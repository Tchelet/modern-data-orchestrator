CREATE SCHEMA IF NOT EXISTS {{ bronze_schema }};

CREATE TABLE IF NOT EXISTS {{ bronze_schema }}.weather_observations_raw (
    source_file VARCHAR,
    airbyte_raw_id VARCHAR,
    airbyte_extracted_at_ts TIMESTAMP,
    loaded_at_ts TIMESTAMP NOT NULL,
    observation_ts TIMESTAMP,
    latitude DOUBLE,
    longitude DOUBLE,
    timezone VARCHAR,
    temperature_2m DOUBLE,
    relative_humidity_2m DOUBLE,
    wind_speed_10m DOUBLE,
    raw_payload_json JSON
);
