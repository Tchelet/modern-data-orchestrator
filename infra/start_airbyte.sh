#!/usr/bin/env bash
set -euo pipefail

if ! command -v abctl >/dev/null 2>&1; then
  cat <<'MSG'
abctl is required to run Airbyte OSS locally.

Install with Homebrew:
  brew tap airbytehq/tap
  brew install abctl

Or follow:
  https://docs.airbyte.com/platform/deploying-airbyte/abctl/
MSG
  exit 1
fi

abctl local install --port 8000
abctl local credentials
