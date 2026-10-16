# Smoke Test Checklist

Use this checklist after the first Airbyte connection is configured.

## 1. Start Services

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yaml up -d
bash infra/start_airbyte.sh
astro dev start
```

## 2. Configure Airbyte

- Create or confirm the Open-Meteo source.
- Create or confirm the MinIO S3 destination.
- Run a manual Airbyte sync once from the UI.
- Confirm objects exist in MinIO under `s3://landing-zone/weather_observations/`.
- Copy the Airbyte UI login from `abctl local credentials` into `AIRBYTE_USERNAME` and `AIRBYTE_PASSWORD` in `.env`.
- Copy the Airbyte connection id into `AIRBYTE_CONNECTION_ID`.
- Run `astro dev restart` so Airflow reloads `.env` before the first trigger.

## 3. Run Airflow

- Open the Airflow UI from Astro.
- Trigger the `modern_data_orchestrator` DAG.
- Confirm each task succeeds:
  - `validate_runtime_config`
  - `trigger_airbyte_sync`
  - `wait_for_airbyte_sync`
  - `prepare_bronze_schema`
  - `load_bronze_from_minio`
  - `build_silver`
  - `build_gold`

## 4. Validate MotherDuck

The tree on the left can show **`my_db` → bronze / silver / gold** while your
notebook is still using a **different current database** (MotherDuck’s default
session is not always `my_db`). Unqualified names like `bronze.weather_observations_raw`
then fail with *schema "bronze" does not exist* even though the objects exist
under `my_db`.

**Fix:** run this once at the top of the cell (or pick **`my_db`** as the active
database in the UI if MotherDuck exposes that control):

```sql
USE my_db;
```

Confirm context:

```sql
SELECT current_database();
SHOW SCHEMAS;
```

Then run the checks (two-part names are enough after `USE my_db`):

```sql
SELECT COUNT(*) AS bronze_rows FROM bronze.weather_observations_raw;
SELECT COUNT(*) AS silver_rows FROM silver.weather_observations;
SELECT COUNT(*) AS gold_rows FROM gold.daily_weather_metrics;
SELECT * FROM gold.daily_weather_metrics ORDER BY observation_date DESC LIMIT 10;
```

**Alternative** without `USE`: fully qualify with three-part names, for example
`my_db.bronze.weather_observations_raw` (see
[MotherDuck: switching database](https://motherduck.com/docs/key-tasks/database-operations/switching-the-current-database/)).

## Troubleshooting

### MotherDuck UI: schemas visible in the tree but `schema "bronze" does not exist`

The explorer lists **`my_db`**, but the notebook’s **current database** may still
be something else. Run **`USE my_db;`** (or qualify tables as `my_db.bronze.…`).
See **§4** above.

### `prepare_bronze_schema` yellow / failed (after Airbyte succeeds)

That task only runs **MotherDuck** DDL (`include/sql/bronze/…`). Open the task →
**Log** and read the traceback (not only the grid color).

Common causes:

1. **`MOTHERDUCK_TOKEN` invalid or expired** — renew the token in the MotherDuck
   UI, update `.env`, then **`astro dev restart`** so workers pick up the change.
2. **Database name mismatch** — `MOTHERDUCK_DATABASE` in `.env` must be the **exact**
   name shown under MotherDuck **Databases** (for example `my_db`). If you only have
   `my_db` but `.env` still says `modern_data_orchestrator`, `prepare_bronze_schema`
   will fail until you align them or create the missing database in the MotherDuck UI.
3. **Stale `.env` in containers** — after editing `.env`, always restart Astro
   dev so scheduler/workers reload variables (`.env` is not baked into the image;
   it is read at runtime).
4. **Network** — the Airflow worker must reach MotherDuck over the internet. A VPN
   or firewall can block that.

## 5. Fallback Seed

If Airbyte setup blocks the first green run, seed MinIO with the sample file:

```bash
python -m include.scripts.seed_minio_sample
```

The seed only lands sample JSONL in MinIO. Airbyte tasks still need a working
`AIRBYTE_CONNECTION_ID` before the full DAG can run.
