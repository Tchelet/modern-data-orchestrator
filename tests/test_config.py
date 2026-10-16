from include.scripts.config import ProjectConfig


def test_config_defaults_are_local(monkeypatch):
    monkeypatch.delenv("PROJECT_ENV", raising=False)
    monkeypatch.delenv("MINIO_AIRBYTE_PREFIX", raising=False)

    config = ProjectConfig.from_env()

    assert config.project_env == "local"
    assert config.minio_bucket == "landing-zone"
    assert config.minio_airbyte_prefix == "local/weather_observations"


def test_config_accepts_explicit_airbyte_prefix(monkeypatch):
    monkeypatch.setenv("MINIO_AIRBYTE_PREFIX", "weather_observations")

    config = ProjectConfig.from_env()

    assert config.minio_airbyte_prefix == "weather_observations"
