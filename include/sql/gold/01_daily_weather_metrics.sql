CREATE SCHEMA IF NOT EXISTS {{ gold_schema }};

CREATE OR REPLACE TABLE {{ gold_schema }}.daily_weather_metrics AS
SELECT
    CAST(observation_ts AS DATE) AS observation_date,
    latitude,
    longitude,
    timezone,
    COUNT(*) AS observation_count,
    MIN(temperature_2m) AS min_temperature_2m,
    AVG(temperature_2m) AS avg_temperature_2m,
    MAX(temperature_2m) AS max_temperature_2m,
    AVG(relative_humidity_2m) AS avg_relative_humidity_2m,
    AVG(wind_speed_10m) AS avg_wind_speed_10m,
    MIN(loaded_at_ts) AS first_loaded_at_ts,
    MAX(loaded_at_ts) AS last_loaded_at_ts
FROM {{ silver_schema }}.weather_observations
GROUP BY
    observation_date,
    latitude,
    longitude,
    timezone;
