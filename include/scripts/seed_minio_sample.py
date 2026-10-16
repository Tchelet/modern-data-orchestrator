from __future__ import annotations

from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from include.scripts.config import ProjectConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_FILE = PROJECT_ROOT / "include" / "sample_data" / "weather_observations.jsonl"


def seed_sample_file() -> str:
    config = ProjectConfig.from_env()
    object_key = f"{config.minio_airbyte_prefix}/sample/weather_observations.jsonl"
    client = boto3.client(
        "s3",
        endpoint_url=config.minio_endpoint.replace("host.docker.internal", "localhost"),
        aws_access_key_id=config.minio_access_key,
        aws_secret_access_key=config.minio_secret_key,
        region_name=config.minio_region,
    )
    try:
        client.create_bucket(Bucket=config.minio_bucket)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise
    client.upload_file(str(SAMPLE_FILE), config.minio_bucket, object_key)
    return f"s3://{config.minio_bucket}/{object_key}"


if __name__ == "__main__":
    print(seed_sample_file())
