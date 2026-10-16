from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task

from include.scripts.airbyte_client import AirbyteClient
from include.scripts.config import ProjectConfig
from include.scripts.motherduck_runner import MotherDuckRunner


@dag(
    dag_id="modern_data_orchestrator",
    description="Trigger Airbyte, land files in MinIO, and build MotherDuck medallion tables.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "owner": "portfolio",
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["portfolio", "airbyte", "minio", "motherduck", "medallion"],
)
def modern_data_orchestrator() -> None:
    @task
    def validate_runtime_config() -> dict[str, str]:
        config = ProjectConfig.from_env()
        if not config.airbyte_connection_id:
            raise RuntimeError("Set AIRBYTE_CONNECTION_ID in .env before running the DAG.")
        if not config.motherduck_token:
            raise RuntimeError("Set MOTHERDUCK_TOKEN in .env before running the DAG.")
        return {
            "project_env": config.project_env,
            "landing_bucket": config.minio_bucket,
            "landing_prefix": config.minio_airbyte_prefix,
            "motherduck_database": config.motherduck_database,
        }

    @task
    def trigger_airbyte_sync() -> int:
        config = ProjectConfig.from_env()
        client = AirbyteClient(
            base_url=config.airbyte_api_base_url,
            api_mode=config.airbyte_api_mode,
            auth=config.airbyte_auth,
        )
        return client.trigger_sync(config.airbyte_connection_id)

    @task
    def wait_for_airbyte_sync(job_id: int) -> str:
        config = ProjectConfig.from_env()
        client = AirbyteClient(
            base_url=config.airbyte_api_base_url,
            api_mode=config.airbyte_api_mode,
            auth=config.airbyte_auth,
        )
        return client.wait_for_job(
            job_id=job_id,
            poll_seconds=config.airbyte_poll_seconds,
            timeout_seconds=config.airbyte_timeout_seconds,
        )

    @task
    def prepare_bronze_schema() -> list[str]:
        runner = MotherDuckRunner()
        return [str(path) for path in runner.execute_layer("bronze")]

    @task
    def load_bronze_from_minio() -> int:
        runner = MotherDuckRunner()
        return runner.load_airbyte_jsonl_to_bronze()

    @task
    def build_silver() -> list[str]:
        runner = MotherDuckRunner()
        return [str(path) for path in runner.execute_layer("silver")]

    @task
    def build_gold() -> list[str]:
        runner = MotherDuckRunner()
        return [str(path) for path in runner.execute_layer("gold")]

    runtime_config = validate_runtime_config()
    airbyte_job_id = trigger_airbyte_sync()
    airbyte_status = wait_for_airbyte_sync(airbyte_job_id)
    bronze_sql = prepare_bronze_schema()
    bronze_rows = load_bronze_from_minio()
    silver_sql = build_silver()
    gold_sql = build_gold()

    runtime_config >> airbyte_job_id
    airbyte_status >> bronze_sql >> bronze_rows >> silver_sql >> gold_sql


modern_data_orchestrator()
