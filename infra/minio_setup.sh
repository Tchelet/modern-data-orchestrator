#!/usr/bin/env bash
set -euo pipefail

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_BUCKET="${MINIO_BUCKET:-landing-zone}"
PROJECT_ENV="${PROJECT_ENV:-local}"

if ! command -v mc >/dev/null 2>&1; then
  echo "Install the MinIO client first: brew install minio/stable/mc"
  exit 1
fi

mc alias set local "${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"
mc mb --ignore-existing "local/${MINIO_BUCKET}"
echo "ready" | mc pipe "local/${MINIO_BUCKET}/${PROJECT_ENV}/.keep"
mc anonymous set none "local/${MINIO_BUCKET}"

echo "MinIO bucket is ready: s3://${MINIO_BUCKET}/${PROJECT_ENV}/"
