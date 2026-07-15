#!/usr/bin/env bash

set -Eeuo pipefail

cd "$(dirname "$0")/.."

source .venv/bin/activate

exec uvicorn \
    services.core.app.main:app \
    --reload \
    --host 127.0.0.1 \
    --port 8080
