# Airbyte Setup

This project keeps Airbyte configuration manual for the first version. The goal
is to learn the moving parts before automating connector creation.

## Verify MinIO is ready (before wiring Airbyte)

From the project root, with the same compose file you used to start MinIO:

```bash
docker compose -f infra/docker-compose.yaml ps
```

Expect **`minio`** in state **`running (healthy)`**. The **`minio-init`** service exits after creating the bucket; that is normal.

Check the API port from your machine:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:9000/minio/health/live
```

Expect **`200`**. Open the console at `http://localhost:9001` (default keys `minioadmin` / `minioadmin` unless you overrode them) and confirm bucket **`landing-zone`** exists.

Optional, if you have the MinIO client (`brew install minio/stable/mc`):

```bash
mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
mc ls local/landing-zone
```

You should see at least a **`local/`** placeholder object from compose init (path depends on `PROJECT_ENV`, default `local`).

## Start Airbyte

```bash
bash infra/start_airbyte.sh
```

Open `http://localhost:8000` and sign in with the credentials printed by:

```bash
abctl local credentials
```

Copy that same username and password into `.env` as `AIRBYTE_USERNAME` and `AIRBYTE_PASSWORD`. The Airflow DAG uses those values to call the Airbyte API. `infra/start_airbyte.sh` prints them once when Airbyte finishes installing.

## Destination: MinIO S3-Compatible Storage

Create an S3 destination with these values:

| Field | Value |
| --- | --- |
| Bucket | `landing-zone` |
| Bucket path / prefix | `weather_observations` |
| Endpoint | `http://host.docker.internal:9000` from Airbyte, or `http://minio:9000` if running in the same compose network |
| Region | `us-east-1` |
| Access key id | `minioadmin` |
| Secret access key | `minioadmin` |
| Path-style access | enabled |
| Output format | JSONL |
| **S3 Path Format** (optional) | **Leave empty** unless you know the connector’s supported placeholders. |

**What `PART_ID` was supposed to mean:** in older examples it stood for “which
file chunk within a sync” (so large syncs do not overwrite one object). **Current
Airbyte S3 does not treat `${PART_ID}` or `${NAMESPACE}` as variables**—if you put
that string in **S3 Path Format**, unsupported tokens are written **literally**
into MinIO keys (the ugly `..._part_${PART_ID}.jsonl...` filenames). **Clear that
field** (or use only documented **`{part_number}`**-style placeholders in a
custom pattern—see link below). **File name pattern** can also stay empty for
defaults.

**Prefix must match Airflow:** The DAG loads objects under the S3 prefix in
`MINIO_AIRBYTE_PREFIX` in `.env` (see `.env.example`). If you use
`weather_observations` there, set the Airbyte destination **bucket path / prefix**
to exactly that (no leading slash). If you omit `MINIO_AIRBYTE_PREFIX` in `.env`,
the code defaults to `local/weather_observations`; in that case set the Airbyte
prefix to **`local/weather_observations`** so landed files match what
`MotherDuckRunner` lists.

If the connector asks for an **S3 path** or **file name pattern**, prefer
**leaving it empty** so Airbyte uses its **default** object layout (documented
for the S3 destination).

If you set a custom **file name pattern**, Airbyte’s S3 connector only expands
**curly-brace** placeholders such as `{timestamp}`, `{part_number}`,
`{sync_id}`, `{format_extension}` (see
[Airbyte S3 destination](https://docs.airbyte.com/integrations/destinations/s3)).
Placeholders that are **not** supported are written **literally** to the object
key (for example a file named `..._part_${PART_ID}.jsonl` in MinIO). Do **not**
use `${...}` / `${PART_ID}` style from older examples.

## Source: Public Weather API

Use this URL (copy as a single line). No API key.

```text
https://api.open-meteo.com/v1/forecast?latitude=32.0853&longitude=34.7818&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=UTC&past_days=1&forecast_days=1
```

Recommended **stream name** (in Builder or in the source UI):

```text
weather_observations
```

### Option A: Catalog source (only if it exists in your build)

Airbyte’s old **HTTP Request** source is **archived** and often **not** listed in
new OSS catalogs. It is normal for searches like `HTTP` or `REST` to return nothing
useful.

Searching the **Marketplace** for `api` only surfaces **named** third-party APIs
(Coin API, News API, and so on), not “call my own URL.”

If you **do** see a clearly generic HTTP/REST/URL connector under **Airbyte
Connectors**, use it with **GET**, the URL above, and **no authentication**.
Otherwise go straight to Option B.

### Option B: Connector Builder (“How do you want to start building?”)

1. Choose **Start from scratch** (or **Fork a connector** and pick an official
   HTTP-style connector to edit, if you prefer a template).
2. Set the **connector name** (for example `Open-Meteo weather`).
3. Under **Streams**, add a stream named **`weather_observations`**.
4. Configure the HTTP request for that stream:
   - **Method:** `GET`
   - **URL:** paste the Open-Meteo URL above (full string)
   - **Authentication:** none
5. **Record selection (Open-Meteo):** the API returns **one JSON object** (the
   forecast document), not a top-level array. You want **exactly one record per
   request**, and that record should be the **whole response** (it must still
   contain `latitude`, `longitude`, `timezone`, and the nested **`hourly`** object
   with array fields—do **not** point the extractor only at `hourly`, or you drop
   coordinates the loader uses).
   - With **Dpath Extractor**, leave **Field Path empty** (root / whole body), or
     use whatever the Builder documents as “root” if empty is invalid.
   - Click **Test** → **Records**; you should see **1** record shaped like the raw
     API JSON in the preview. If you see **0** records, the path is too deep; clear
     it. If you see **many** records, you over-split; use the root document only.
6. **Test** the stream, then **Publish** (or **Add to workspace**) so the connector
   appears in the catalog.
7. Go to **Sources → New source**, pick your published connector, and finish the
   source definition (same URL and stream if prompted again).

This endpoint requires no API key. The MotherDuck loader supports either a
single JSON record containing an `hourly` object with arrays, or already flattened
JSONL records with `time`, `temperature_2m`, `relative_humidity_2m`, and
`wind_speed_10m` fields.

## Airflow Connection ID

After creating the Airbyte connection, copy its connection id into `.env`:

```bash
AIRBYTE_USERNAME=<username from abctl local credentials>
AIRBYTE_PASSWORD=<password from abctl local credentials>
AIRBYTE_CONNECTION_ID=<your-airbyte-connection-id>
```

Airflow loads `.env` at container start. Restart it before the first DAG run, and again after any later edit:

```bash
astro dev restart
```

The DAG triggers the connection through:

```bash
AIRBYTE_API_BASE_URL=http://host.docker.internal:8000/api/public/v1
AIRBYTE_API_MODE=public
```

If your local Airbyte build only exposes the legacy API, change these values:

```bash
AIRBYTE_API_BASE_URL=http://host.docker.internal:8000/api/v1
AIRBYTE_API_MODE=legacy
```

## Fallback For First Green Run

If the HTTP connector path blocks progress, use the sample file seed to validate
MinIO and MotherDuck while the Airbyte connection is fixed:

```bash
python -m include.scripts.seed_minio_sample
```

The seed only lands sample JSONL in MinIO. The DAG still needs a real Airbyte
connection id before `trigger_airbyte_sync` can succeed.
