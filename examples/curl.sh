#!/usr/bin/env bash
# Usage: examples/curl.sh document.pdf [start_page] [max_pages]
set -euo pipefail
API="${OCR_API:-http://127.0.0.1:8090}"
FILE="${1:?give a PDF or image}"
curl -sS --fail-with-body --max-time 3600 -X POST "$API/v1/ocr" \
  -F "file=@${FILE}" -F "start_page=${2:-1}" -F "max_pages=${3:-5}" \
  -o "${FILE}.ocr.json"
echo "saved ${FILE}.ocr.json"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['markdown'])" "${FILE}.ocr.json"
