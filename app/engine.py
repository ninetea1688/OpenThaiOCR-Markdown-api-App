"""Model wrapper.

Loading and inference follow iApp's official Mac guide
(https://iapp.co.th/en/blog/openthai2p0-ocr-how-to-run): Transformers backend,
float32 on mps/cpu (bfloat16 on cuda), NVIDIA's DocumentParser with the default
box-and-class prompt, mode="single", greedy decoding (temperature 0), and a
leading new line on the prompt so the tokens match a vLLM server.

Heavy imports (torch, transformers, nemotron_parse) happen inside load(), so the
web server starts at once and the tests run without the model.
"""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version
import threading
import time
from typing import Any, Optional

from .config import Settings

log = logging.getLogger("ocr.engine")

# Files in the model repo that local Transformers inference does not need
# (vLLM drafter, benchmark references, images).
IGNORE_PATTERNS = ["dflash2/*", "reference/*", "assets/*"]


class PageError(Exception):
    """One page could not be read; the request continues with the next page."""


class OCREngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.state = "not_loaded"  # not_loaded | loading | ready | error
        self.error: Optional[str] = None
        self.device: Optional[str] = None
        self.load_seconds: Optional[float] = None
        try:
            self.runtime_version: Optional[str] = version("nemotron-parse")
        except PackageNotFoundError:
            self.runtime_version = None
        self._parser = None
        self._generation_error = Exception
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()  # one page at a time
        self._ready = threading.Event()

    # ---------- loading ----------
    def start_background_load(self) -> None:
        threading.Thread(target=self._safe_load, name="model-loader", daemon=True).start()

    def _safe_load(self) -> None:
        try:
            self.load()
        except Exception:  # state and error are recorded in load()
            pass

    def load(self) -> None:
        with self._load_lock:
            if self.state == "ready":
                return
            self._ready.clear()
            self.state, self.error = "loading", None
            started = time.perf_counter()
            try:
                self._load()
            except Exception as exc:
                self.state, self.error = "error", f"{type(exc).__name__}: {exc}"
                self._ready.set()  # Wake requests waiting on a failed background load.
                log.exception("Model load failed")
                raise
            self.load_seconds = round(time.perf_counter() - started, 1)
            self.state = "ready"
            self._ready.set()
            log.info("Model ready on %s in %.1f s", self.device, self.load_seconds)

    def _pick_device(self, torch) -> str:
        wanted = self.settings.device.lower()
        if wanted != "auto":
            return wanted
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load(self) -> None:
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModel, AutoProcessor
        from nemotron_parse.inference import (
            DocumentParser,
            GenerationError,
            GenerationSettings,
            TransformersBackend,
        )

        s = self.settings
        model_dir = snapshot_download(
            s.model_id,
            revision=s.model_revision,
            ignore_patterns=IGNORE_PATTERNS,
            local_files_only=s.local_files_only,
        )
        device = self._pick_device(torch)
        dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
        log.info("Loading %s@%s from %s on %s (%s)", s.model_id, s.model_revision, model_dir, device, dtype)

        model = AutoModel.from_pretrained(model_dir, trust_remote_code=True, dtype=dtype).to(device).eval()
        processor = AutoProcessor.from_pretrained(model_dir, trust_remote_code=True)

        class Backend(TransformersBackend):
            # A vLLM server reads the prompt after a new line; send the same tokens here.
            def __call__(self, image, *, prompt, **kwargs):
                return super().__call__(image, prompt="\n" + prompt, **kwargs)

        self._parser = DocumentParser(
            backend=Backend(model, processor),
            # OpenThai 2.1 defaults: skip blank pages and use the new postprocessing.
            # Keep dewarping off, as upstream recommends for this model.
            skip_blank=True,
            dewarp=False,
            # Greedy decoding; with sampling a Mac GPU garbled pages in iApp's test.
            fullpage=GenerationSettings(temperature=0, max_tokens=s.max_new_tokens),
        )
        self._generation_error = GenerationError
        self.device = device

    def wait_ready(self, timeout: Optional[float] = None) -> None:
        """Block until the model is loaded (loading it now if nobody has started)."""
        if self.state == "ready":
            return
        if self.state in ("not_loaded", "error"):
            self.load()
            return
        if not self._ready.wait(timeout):
            raise TimeoutError("Model is still loading")
        if self.state != "ready":
            raise RuntimeError(self.error or "Model failed to load")

    # ---------- inference ----------
    def parse_page(self, image, *, on_started=None) -> dict[str, Any]:
        """Read one PIL image. Raises PageError if the page cannot be read."""
        self.wait_ready()
        with self._infer_lock:
            if on_started:
                on_started()
            try:
                return self._parser.parse(image.convert("RGB"), mode="single")
            except self._generation_error as exc:
                raise PageError(f"GenerationError: {exc}") from exc
            except Exception as exc:
                log.exception("Page failed")
                raise PageError(f"{type(exc).__name__}: {exc}") from exc
            finally:
                self._free_cache()

    def _free_cache(self) -> None:
        try:
            import torch

            if self.device == "mps":
                torch.mps.empty_cache()
            elif self.device and self.device.startswith("cuda"):
                torch.cuda.empty_cache()
        except Exception:
            pass
