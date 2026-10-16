from datetime import datetime, timezone

from include.scripts.motherduck_runner import MotherDuckRunner


def test_hourly_open_meteo_payload_explodes_to_rows():
    runner = MotherDuckRunner.__new__(MotherDuckRunner)
    payload = {
        "_airbyte_raw_id": "raw-1",
        "_airbyte_extracted_at": "2026-04-25T10:00:00Z",
        "_airbyte_data": {
            "latitude": 32.0853,
            "longitude": 34.7818,
            "timezone": "UTC",
            "hourly": {
                "time": ["2026-04-25T00:00:00Z", "2026-04-25T01:00:00Z"],
                "temperature_2m": [19.4, 18.9],
                "relative_humidity_2m": [63, 67],
                "wind_speed_10m": [8.1, 7.8],
            },
        },
    }

    rows = list(
        runner._payload_to_rows(
            source_file="weather/sample.jsonl",
            payload=payload,
            loaded_at_ts=datetime(2026, 4, 25, tzinfo=timezone.utc),
        )
    )

    assert len(rows) == 2
    assert rows[0]["observation_ts"] == datetime(2026, 4, 25, 0, 0, tzinfo=timezone.utc)
    assert rows[0]["temperature_2m"] == 19.4
    assert rows[1]["relative_humidity_2m"] == 67.0


def test_flat_payload_maps_to_single_row():
    runner = MotherDuckRunner.__new__(MotherDuckRunner)
    payload = {
        "time": "2026-04-25T00:00:00Z",
        "latitude": "32.0853",
        "longitude": "34.7818",
        "timezone": "UTC",
        "temperature_2m": "19.4",
        "relative_humidity_2m": "63",
        "wind_speed_10m": "8.1",
    }

    rows = list(
        runner._payload_to_rows(
            source_file="weather/flat.jsonl",
            payload=payload,
            loaded_at_ts=datetime(2026, 4, 25, tzinfo=timezone.utc),
        )
    )

    assert len(rows) == 1
    assert rows[0]["latitude"] == 32.0853
    assert rows[0]["wind_speed_10m"] == 8.1
