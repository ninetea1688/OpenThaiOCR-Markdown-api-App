# Third-party notices

This repository holds only the API code (MIT, see `LICENSE`). It contains no
model weights and no copy of NVIDIA's code. At install time it downloads and
uses the following, each under its own licence:

## iapp/OpenThai2.1-OCR-Markdown-20261118 (model)

- Source: https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118
  (revision `c974dc7d18a4511a21988f4a1d12fad07ac16625`)
- Authors: iApp Technology Co., Ltd., a Thai fine-tune of NVIDIA Nemotron 3.5 Parse.
- Licence: OpenMDW License Agreement, version 1.1.
  Full text: https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118/blob/c974dc7d18a4511a21988f4a1d12fad07ac16625/LICENSE
- Third-party notices of the model:
  https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118/blob/c974dc7d18a4511a21988f4a1d12fad07ac16625/THIRD_PARTY_NOTICES.md
- Tokenizer (MIT) attribution:
  https://huggingface.co/iapp/OpenThai2.1-OCR-Markdown-20261118/blob/c974dc7d18a4511a21988f4a1d12fad07ac16625/TOKENIZER_ATTRIBUTION.md
- NVIDIA's original model card: `NVIDIA_NEMOTRON_PARSE_README.md` in the same repository.

## NVIDIA Nemotron 3.5 Parse (base model, `nemotron_parse` package, serving code)

- Source: https://huggingface.co/nvidia/Nemotron-3.5-Parse
- Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
- Licence: OpenMDW-1.1 (SPDX: OpenMDW-1.1).
- This snapshot carries OpenThai 2.1 weights and the v2.2.0 release runtime (`nemotron-parse` 3.5.0.post8). Optional dewarping is disabled.
- The `nemotron-parse` Python package is installed from the model repository
  unchanged; its `LICENSE`, `THIRD_PARTY_NOTICES.md` and `TOKENIZER_ATTRIBUTION.md`
  are installed with it (see the package's `.dist-info/licenses` folder in `.venv`).
  Local copies after download:
  `~/.cache/huggingface/hub/models--iapp--OpenThai2.1-OCR-Markdown-20261118/snapshots/<revision>/`

## Notes

- `app/engine.py` follows the loading steps of iApp's public guide
  (https://iapp.co.th/en/blog/openthai2p0-ocr-how-to-run); it calls NVIDIA's
  `DocumentParser` and `TransformersBackend` through their public interface and
  does not copy NVIDIA code.
- If you redistribute the model weights (for example in a Docker image), include
  the model's `LICENSE`, `THIRD_PARTY_NOTICES.md` and `TOKENIZER_ATTRIBUTION.md` unchanged.
- Python libraries (FastAPI, Uvicorn, pypdfium2, Pillow, PyTorch, Transformers and
  others) are installed from PyPI under their own licences.

## Browser interface

- React / React DOM, Vite and the Markdown rendering packages retain their own
  open-source licences. Package versions are recorded in `frontend/package-lock.json`.
- Noto Sans Thai is bundled locally through `@fontsource/noto-sans-thai` under the
  SIL Open Font License 1.1. It is not fetched from Google Fonts at runtime.
- Phosphor icons are distributed under MIT.
- The frontend build collects production dependency licence texts into
  `frontend/dist/third-party-licenses.txt`, served at `/third-party-licenses.txt`.
