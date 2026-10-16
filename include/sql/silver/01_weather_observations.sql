CREATE SCHEMA IF NOT EXISTS {{ silver_schema }};

CREATE OR REPLACE TABLE {{ silver_schema }}.weather_observations AS
WITH typed_observations AS (
    SELECT
        source_file,
        airbyte_raw_id,
        airbyte_extracted_at_ts,
        loaded_at_ts,
        observation_ts,
        latitude,
        longitude,
        timezone,
        temperature_2m,
        relative_humidity_2m,
        wind_speed_10m,
        raw_payload_json
    FROM {{ bronze_schema }}.weather_observations_raw
    WHERE observation_ts IS NOT NULL
),

deduplicated_observations AS (
    SELECT
        source_file,
        airbyte_raw_id,
        airbyte_extracted_at_ts,
        loaded_at_ts,
        observation_ts,
        latitude,
        longitude,
        timezone,
        temperature_2m,
        relative_humidity_2m,
        wind_speed_10m,
        raw_payload_json,
        ROW_NUMBER() OVER (
            PARTITION BY observation_ts, latitude, longitude
            ORDER BY loaded_at_ts DESC, source_file DESC
        ) AS row_num
    FROM typed_observations
)

SELECT
    source_file,
    airbyte_raw_id,
    airbyte_extracted_at_ts,
    loaded_at_ts,
    observation_ts,
    latitude,
    longitude,
    timezone,
    temperature_2m,
    relative_humidity_2m,
    wind_speed_10m,
    raw_payload_json
FROM deduplicated_observations
WHERE row_num = 1;
