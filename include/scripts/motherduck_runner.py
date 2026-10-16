from __future__ import annotations

import gzip
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import boto3
import duckdb

from include.scripts.config import ProjectConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_ROOT = PROJECT_ROOT / "include" / "sql"


class MotherDuckRunner:
    def __init__(self, config: ProjectConfig | None = None) -> None:
        self.config = config or ProjectConfig.from_env()

    def execute_layer(self, layer_name: str) -> list[Path]:
        sql_dir = SQL_ROOT / layer_name
        if not sql_dir.exists():
            raise FileNotFoundError(f"SQL layer directory does not exist: {sql_dir}")

        executed_files: list[Path] = []
        with self._connect() as conn:
            for sql_file in sorted(sql_dir.glob("*.sql")):
                sql = self._render_sql(sql_file.read_text())
                conn.execute(sql)
                executed_files.append(sql_file)
        return executed_files

    def load_airbyte_jsonl_to_bronze(self) -> int:
        rows = list(self._iter_airbyte_rows())
        if not rows:
            return 0

        source_files = sorted({row["source_file"] for row in rows})
        table_name = f"{self.config.bronze_schema}.weather_observations_raw"
        columns = (
            "source_file",
            "airbyte_raw_id",
            "airbyte_extracted_at_ts",
            "loaded_at_ts",
            "observation_ts",
            "latitude",
            "longitude",
            "timezone",
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "raw_payload_json",
        )

        with self._connect() as conn:
            for source_file in source_files:
                conn.execute(
                    f"DELETE FROM {table_name} WHERE source_file = ?",
                    [source_file],
                )

            placeholders = ", ".join(["?"] * len(columns))
            conn.executemany(
                f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
                [[row[column_name] for column_name in columns] for row in rows],
            )

        return len(rows)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self.config.motherduck_connection_string)

    def _render_sql(self, sql: str) -> str:
        rendered_sql = sql
        for key, value in self.config.sql_context.items():
            rendered_sql = rendered_sql.replace(f"{{{{ {key} }}}}", value)
        return rendered_sql

    def _iter_airbyte_rows(self) -> Iterable[dict[str, Any]]:
        client = boto3.client(
            "s3",
            endpoint_url=self.config.minio_endpoint,
            aws_access_key_id=self.config.minio_access_key,
            aws_secret_access_key=self.config.minio_secret_key,
            region_name=self.config.minio_region,
        )
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(
            Bucket=self.config.minio_bucket,
            Prefix=self.config.minio_airbyte_prefix,
        )

        loaded_at_ts = datetime.now(timezone.utc)
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/") or not self._is_jsonl_key(key):
                    continue

                body = client.get_object(Bucket=self.config.minio_bucket, Key=key)["Body"].read()
                yield from self._parse_object_rows(key, body, loaded_at_ts)

    def _parse_object_rows(
        self,
        source_file: str,
        body: bytes,
        loaded_at_ts: datetime,
    ) -> Iterable[dict[str, Any]]:
        if source_file.endswith(".gz"):
            body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()

        for raw_line in body.decode("utf-8").splitlines():
            if not raw_line.strip():
                continue
            payload = json.loads(raw_line)
            yield from self._payload_to_rows(source_file, payload, loaded_at_ts)

    def _payload_to_rows(
        self,
        source_file: str,
        payload: dict[str, Any],
        loaded_at_ts: datetime,
    ) -> Iterable[dict[str, Any]]:
        data = payload.get("_airbyte_data", payload)
        airbyte_raw_id = payload.get("_airbyte_raw_id")
        airbyte_extracted_at_ts = self._parse_ts(payload.get("_airbyte_extracted_at"))

        hourly = data.get("hourly") if isinstance(data, dict) else None
        if isinstance(hourly, dict) and isinstance(hourly.get("time"), list):
            yield from self._explode_hourly_payload(
                source_file,
                payload,
                data,
                hourly,
                airbyte_raw_id,
                airbyte_extracted_at_ts,
                loaded_at_ts,
            )
            return

        yield self._build_row(
            source_file=source_file,
            payload=payload,
            data=data,
            airbyte_raw_id=airbyte_raw_id,
            airbyte_extracted_at_ts=airbyte_extracted_at_ts,
            loaded_at_ts=loaded_at_ts,
            observation_ts=data.get("time") or data.get("timestamp") or data.get("date"),
            temperature_2m=data.get("temperature_2m"),
            relative_humidity_2m=(
                data.get("relative_humidity_2m")
                or data.get("relativehumidity_2m")
            ),
            wind_speed_10m=data.get("wind_speed_10m") or data.get("windspeed_10m"),
        )

    def _explode_hourly_payload(
        self,
        source_file: str,
        payload: dict[str, Any],
        data: dict[str, Any],
        hourly: dict[str, Any],
        airbyte_raw_id: str | None,
        airbyte_extracted_at_ts: datetime | None,
        loaded_at_ts: datetime,
    ) -> Iterable[dict[str, Any]]:
        for idx, observation_ts in enumerate(hourly["time"]):
            yield self._build_row(
                source_file=source_file,
                payload=payload,
                data=data,
                airbyte_raw_id=airbyte_raw_id,
                airbyte_extracted_at_ts=airbyte_extracted_at_ts,
                loaded_at_ts=loaded_at_ts,
                observation_ts=observation_ts,
                temperature_2m=self._list_value(hourly.get("temperature_2m"), idx),
                relative_humidity_2m=self._list_value(
                    hourly.get("relative_humidity_2m") or hourly.get("relativehumidity_2m"),
                    idx,
                ),
                wind_speed_10m=self._list_value(
                    hourly.get("wind_speed_10m") or hourly.get("windspeed_10m"),
                    idx,
                ),
            )

    def _build_row(
        self,
        source_file: str,
        payload: dict[str, Any],
        data: dict[str, Any],
        airbyte_raw_id: str | None,
        airbyte_extracted_at_ts: datetime | None,
        loaded_at_ts: datetime,
        observation_ts: Any,
        temperature_2m: Any,
        relative_humidity_2m: Any,
        wind_speed_10m: Any,
    ) -> dict[str, Any]:
        return {
            "source_file": source_file,
            "airbyte_raw_id": airbyte_raw_id,
            "airbyte_extracted_at_ts": airbyte_extracted_at_ts,
            "loaded_at_ts": loaded_at_ts,
            "observation_ts": self._parse_ts(observation_ts),
            "latitude": self._float_or_none(data.get("latitude")),
            "longitude": self._float_or_none(data.get("longitude")),
            "timezone": data.get("timezone"),
            "temperature_2m": self._float_or_none(temperature_2m),
            "relative_humidity_2m": self._float_or_none(relative_humidity_2m),
            "wind_speed_10m": self._float_or_none(wind_speed_10m),
            "raw_payload_json": json.dumps(payload, sort_keys=True),
        }

    @staticmethod
    def _is_jsonl_key(key: str) -> bool:
        return key.endswith((".jsonl", ".jsonl.gz", ".ndjson", ".ndjson.gz", ".json"))

    @staticmethod
    def _list_value(values: Any, idx: int) -> Any:
        if isinstance(values, list) and idx < len(values):
            return values[idx]
        return None

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value in (None, ""):
            return None
        return float(value)

    @staticmethod
    def _parse_ts(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            if value > 10_000_000_000:
                value = value / 1000
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            normalized_value = value.replace("Z", "+00:00")
            if len(normalized_value) == 10:
                normalized_value = f"{normalized_value}T00:00:00+00:00"
            return datetime.fromisoformat(normalized_value)
        raise TypeError(f"Unsupported timestamp value: {value!r}")
