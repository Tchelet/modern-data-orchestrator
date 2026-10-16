from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int_env(name: str, default: int) -> int:
    raw_value = _env(name)
    if not raw_value:
        return default
    return int(raw_value)


@dataclass(frozen=True)
class ProjectConfig:
    project_env: str
    airbyte_api_base_url: str
    airbyte_api_mode: str
    airbyte_username: str
    airbyte_password: str
    airbyte_connection_id: str
    airbyte_poll_seconds: int
    airbyte_timeout_seconds: int
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_region: str
    minio_bucket: str
    minio_airbyte_prefix: str
    motherduck_token: str
    motherduck_database: str
    bronze_schema: str
    silver_schema: str
    gold_schema: str

    @classmethod
    def from_env(cls) -> "ProjectConfig":
        project_env = _env("PROJECT_ENV", "local")
        return cls(
            project_env=project_env,
            airbyte_api_base_url=_env(
                "AIRBYTE_API_BASE_URL",
                "http://host.docker.internal:8000/api/public/v1",
            ),
            airbyte_api_mode=_env("AIRBYTE_API_MODE", "public"),
            airbyte_username=_env("AIRBYTE_USERNAME"),
            airbyte_password=_env("AIRBYTE_PASSWORD"),
            airbyte_connection_id=_env("AIRBYTE_CONNECTION_ID"),
            airbyte_poll_seconds=_int_env("AIRBYTE_POLL_SECONDS", 15),
            airbyte_timeout_seconds=_int_env("AIRBYTE_TIMEOUT_SECONDS", 1800),
            minio_endpoint=_env("MINIO_ENDPOINT", "http://host.docker.internal:9000"),
            minio_access_key=_env("MINIO_ACCESS_KEY", "minioadmin"),
            minio_secret_key=_env("MINIO_SECRET_KEY", "minioadmin"),
            minio_region=_env("MINIO_REGION", "us-east-1"),
            minio_bucket=_env("MINIO_BUCKET", "landing-zone"),
            minio_airbyte_prefix=_env(
                "MINIO_AIRBYTE_PREFIX",
                f"{project_env}/weather_observations",
            ).strip("/"),
            motherduck_token=_env("MOTHERDUCK_TOKEN"),
            motherduck_database=_env("MOTHERDUCK_DATABASE", "my_db"),
            bronze_schema=_env("MOTHERDUCK_SCHEMA_BRONZE", "bronze"),
            silver_schema=_env("MOTHERDUCK_SCHEMA_SILVER", "silver"),
            gold_schema=_env("MOTHERDUCK_SCHEMA_GOLD", "gold"),
        )

    @property
    def motherduck_connection_string(self) -> str:
        if not self.motherduck_token:
            raise RuntimeError("MOTHERDUCK_TOKEN is required to connect to MotherDuck.")
        return (
            f"md:{self.motherduck_database}"
            f"?motherduck_token={self.motherduck_token}"
        )

    @property
    def airbyte_auth(self) -> tuple[str, str] | None:
        if self.airbyte_username and self.airbyte_password:
            return (self.airbyte_username, self.airbyte_password)
        return None

    @property
    def sql_context(self) -> dict[str, str]:
        return {
            "project_env": self.project_env,
            "bronze_schema": self.bronze_schema,
            "silver_schema": self.silver_schema,
            "gold_schema": self.gold_schema,
        }
