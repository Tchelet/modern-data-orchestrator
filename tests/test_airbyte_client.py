from include.scripts.airbyte_client import AirbyteClient


def test_extracts_job_id_from_public_response():
    response = {"jobId": 123}

    assert AirbyteClient._extract_job_id(response) == 123


def test_extracts_job_id_from_legacy_response():
    response = {"job": {"id": 456}}

    assert AirbyteClient._extract_job_id(response) == 456


def test_extracts_status_from_nested_job_response():
    response = {"job": {"status": "succeeded"}}

    assert AirbyteClient._extract_status(response) == "succeeded"
