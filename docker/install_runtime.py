"""Install the model's Python package without baking weights into the image."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from huggingface_hub import snapshot_download

with tempfile.TemporaryDirectory() as cache, tempfile.TemporaryDirectory() as package:
    snapshot = Path(snapshot_download(
        os.environ['OCR_MODEL_ID'],
        revision=os.environ['OCR_MODEL_REVISION'],
        cache_dir=cache,
        allow_patterns=[
            'pyproject.toml', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
            'TOKENIZER_ATTRIBUTION.md', 'README.md', 'postprocessing.py',
            'latex2html.py', 'nemotron_parse/*', 'vllm_tied_patch/*',
        ],
    ))
    for entry in snapshot.iterdir():
        destination = Path(package) / entry.name
        if entry.is_dir():
            shutil.copytree(entry, destination)
        else:
            shutil.copyfile(entry, destination)
    subprocess.run(['python', '-m', 'pip', 'install', '--no-cache-dir', package], check=True)
