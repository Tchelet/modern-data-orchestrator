# Local Infrastructure

This folder owns the local services used by this project.

## MinIO

Start MinIO with Docker Compose:

```bash
docker compose -f infra/docker-compose.yaml up -d
```

Default endpoints:
- S3 API: `http://localhost:9000`
- Console: `http://localhost:9001`
- Username: `minioadmin`
- Password: `minioadmin`

The compose init container creates the `landing-zone` bucket and a `local/.keep`
object so the environment prefix is visible.

## Airbyte OSS

Airbyte's current OSS local deployment path is `abctl`, which runs Airbyte in a
local Docker-backed kind cluster. Start it with:

```bash
bash infra/start_airbyte.sh
```

After the script finishes, Airbyte is available at `http://localhost:8000`.
The script prints a username and password. Use that pair to sign in, and copy it
into `.env` as `AIRBYTE_USERNAME` and `AIRBYTE_PASSWORD`. Run
`abctl local credentials` again if you need the generated login.

## Why Airbyte Is Not In Compose

Older Airbyte OSS tutorials used Docker Compose directly. Airbyte now documents
`abctl` as the supported local path. Keeping MinIO in Compose and Airbyte in
`abctl` gives the same local learning surface without pinning this portfolio
project to deprecated Airbyte deployment internals.
