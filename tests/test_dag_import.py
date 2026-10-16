import pytest


pytest.importorskip("airflow")


def test_dag_imports():
    from dags.modern_data_orchestrator_dag import modern_data_orchestrator

    assert modern_data_orchestrator is not None
