#!/usr/bin/env bash
set -euo pipefail

if ! command -v abctl >/dev/null 2>&1; then
  echo "abctl is not installed; nothing to stop."
  exit 0
fi

abctl local uninstall
