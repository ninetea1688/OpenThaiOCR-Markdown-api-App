#!/usr/bin/env bash
# Install the API on a Mac with Apple silicon (also works on Linux).
# Follows iApp's guide: download the model repo, then install its own
# package (nemotron-parse, which brings PyTorch and Transformers).
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  [ -d .venv ] || uv venv --python 3.13 .venv
  PIP=(uv pip install --python .venv/bin/python)
else
  [ -d .venv ] || python3 -m venv .venv
  PIP=(.venv/bin/python -m pip install)
fi

"${PIP[@]}" "huggingface-hub>=1.24.0,<2" "pydantic-settings>=2.4"
# Use the same .env / environment precedence and defaults as the running API.
MODEL_ID=$(.venv/bin/python -c 'from app.config import get_settings; print(get_settings().model_id)')
REVISION=$(.venv/bin/python -c 'from app.config import get_settings; print(get_settings().model_revision)')

echo "== Downloading $MODEL_ID@$REVISION into the Hugging Face cache (about 2.6 GB)"
SNAP=$(.venv/bin/hf download "$MODEL_ID" --revision "$REVISION" \
  --exclude "dflash2/*" --exclude "reference/*" --exclude "assets/*" --quiet)
echo "   $SNAP"

# The cache holds symlinks; copy the package files out before building it.
SRC=$(mktemp -d)
for f in pyproject.toml LICENSE THIRD_PARTY_NOTICES.md TOKENIZER_ATTRIBUTION.md README.md postprocessing.py latex2html.py; do
  cp -L "$SNAP/$f" "$SRC/"
done
cp -RL "$SNAP/nemotron_parse" "$SNAP/vllm_tied_patch" "$SRC/"

echo "== Installing nemotron-parse and the API dependencies"
"${PIP[@]}" "$SRC" -r requirements.txt
rm -rf "$SRC"
echo "== Done. Start with: scripts/run.sh"
