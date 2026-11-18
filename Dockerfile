# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm AS runtime
ARG MODEL_ID=iapp/OpenThai2.1-OCR-Markdown-20261118
ARG MODEL_REVISION=c974dc7d18a4511a21988f4a1d12fad07ac16625
# CPU wheels keep Linux CPU images smaller. GPU override selects the CUDA index.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/ocr/.cache/huggingface \
    OCR_HOST=0.0.0.0 OCR_PORT=8090 OCR_FRONTEND_DIR=/srv/frontend/dist \
    OCR_MODEL_ID=${MODEL_ID} OCR_MODEL_REVISION=${MODEL_REVISION}
WORKDIR /srv
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=3 -o Acquire::https::Timeout=30 update \
    && apt-get -o Acquire::Retries=3 -o Acquire::https::Timeout=30 install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir 'torch>=2.11.0,<2.14' 'torchvision>=0.26.0,<0.29' --index-url ${TORCH_INDEX_URL}
COPY docker/install_runtime.py /tmp/install_runtime.py
RUN python /tmp/install_runtime.py && rm /tmp/install_runtime.py
RUN useradd --create-home --uid 10001 ocr \
    && mkdir -p /home/ocr/.cache/huggingface && chown -R ocr:ocr /home/ocr
COPY app/ ./app/
COPY LICENSE THIRD_PARTY_NOTICES.md ./
COPY --from=frontend /web/dist/ ./frontend/dist/
USER ocr
EXPOSE 8090
# Liveness: loading and lazy loading are valid states; model failures are unhealthy.
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8090/health',timeout=5)); raise SystemExit(r['model_state']=='error')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "1"]
