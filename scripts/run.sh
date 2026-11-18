#!/usr/bin/env bash
# Start the API. Settings come from .env (see .env.example) or OCR_* variables.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
# Let PyTorch fall back to the CPU for any operation the Mac GPU lacks.
export PYTORCH_ENABLE_MPS_FALLBACK="${PYTORCH_ENABLE_MPS_FALLBACK:-1}"
exec .venv/bin/uvicorn app.main:app --host "${OCR_HOST:-127.0.0.1}" --port "${OCR_PORT:-8090}" --workers 1 "$@"
