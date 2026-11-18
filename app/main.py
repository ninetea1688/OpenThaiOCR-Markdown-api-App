"""FastAPI app. Run: uvicorn app.main:app --host 127.0.0.1 --port 8090"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from . import __version__
from .config import Settings, get_settings
from .engine import OCREngine, PageError
from .pages import SUPPORTED_TYPES, UnsupportedFile, open_document
from .schemas import Block, Health, Info, OCRResponse, PageResult, RequestProgress
from .requests import RequestStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ocr.api")


def create_app(settings: Optional[Settings] = None, engine: Optional[OCREngine] = None) -> FastAPI:
    settings = settings or get_settings()
    engine = engine or OCREngine(settings)

    server_id = uuid4().hex
    requests = RequestStore(server_id)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.preload and engine.state == "not_loaded":
            engine.start_background_load()
        async def cleanup():
            while True:
                await asyncio.sleep(30)
                requests.prune()
        task = asyncio.create_task(cleanup())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="OCR Markdown API",
        version=__version__,
        description=(
            "## Thai document OCR — OpenThai 2.1\n\n"
            f"**Configured model:** `{settings.model_id}`  \n"
            f"**Pinned revision:** `{settings.model_revision}`\n\n"
            "The default snapshot includes the v2.2.0 runtime and OpenThai 2.1 weights. "
            "Processing runs on this server through PyTorch/Transformers.\n\n"
            "### Output conventions\n"
            "- Tables are HTML with merged cells preserved; unit row/column spans are omitted.\n"
            "- Formulas use `$$...$$` LaTeX delimiters (the GUI displays the source).\n"
            "- Page headers/footers remain in `blocks` and are omitted from combined Markdown.\n"
            "- Blank pages return empty Markdown; Thai sara am is normalized in rendered output.\n"
            "- Optional dewarping is disabled. Raw block `text` and `include_raw` output "
            "remain model predictions and may differ from rendered `content`.\n\n"
            "Requests wait until the selected pages finish; additional requests queue. "
            "A failed page is reported in `pages[].error` while later pages continue. "
            "Check `/health` for model readiness and the installed `runtime_version`.\n\n"
            "Provide a unique `request_id` UUID to track real queue/page progress via "
            "`GET /v1/ocr/requests/{request_id}` and recover a completed response after a "
            "connection loss. Tracked results are kept in RAM for up to 15 minutes "
            "(16 requests maximum), removed on restart and never written to disk. "
            "`/v1/info.server_id` identifies each server instance.\n\n"
            "### Acknowledgements and licences\n"
            "Thank you to **iApp Technology / OpenThai** for the Thai adaptation and "
            "to **NVIDIA** for the base model, "
            "[Nemotron 3.5 Parse](https://huggingface.co/nvidia/Nemotron-3.5-Parse), "
            "and its parsing runtime. Model/runtime: **OpenMDW-1.1**; "
            "this API wrapper: **MIT**.\n\n"
            f"[Model card and reference](https://huggingface.co/{settings.model_id}/"
            f"blob/{settings.model_revision}/README.md)"
        ),
        license_info={"name": "MIT (API wrapper only)"},
        openapi_tags=[
            {"name": "System", "description": "Server status, model identity and runtime version."},
            {"name": "OCR", "description": "PDF/image to Markdown and page blocks."},
        ],
        lifespan=lifespan,
    )
    app.state.settings, app.state.engine = settings, engine
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.cors_origin_regex,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    def health_dict() -> dict:
        return dict(
            status="ok",
            model_state=engine.state,
            model_loaded=engine.state == "ready",
            model_error=engine.error,
            device=engine.device,
            model=settings.model_id,
            revision=settings.model_revision,
            version=__version__,
            runtime_version=getattr(engine, "runtime_version", None),
        )

    @app.get("/health", response_model=Health, tags=["System"], summary="ตรวจสถานะเซิร์ฟเวอร์และโมเดล")
    async def health():
        return health_dict()

    @app.get("/v1/info", response_model=Info, tags=["System"], summary="ข้อมูลโมเดล Runtime และขีดจำกัด")
    async def info():
        return Info(
            **health_dict(),
            server_id=server_id,
            supported_types=SUPPORTED_TYPES,
            max_file_mb=settings.max_file_mb,
            max_pages=settings.max_pages,
            pdf_dpi=settings.pdf_dpi,
            max_new_tokens=settings.max_new_tokens,
            concurrency="one page at a time; extra requests wait in line",
            load_seconds=engine.load_seconds,
        )

    @app.get("/v1/ocr/requests/{request_id}", response_model=RequestProgress, tags=["OCR"],
             summary="ติดตามคำขอและกู้ผลเมื่อการเชื่อมต่อขาด", responses={404: {"description": "ไม่พบคำขอ หมดอายุ หรือเซิร์ฟเวอร์เริ่มใหม่"}})
    async def request_status(request_id: UUID):
        progress = requests.get(str(request_id))
        if progress is None:
            raise HTTPException(404, "Request not found or expired")
        from fastapi.responses import JSONResponse
        return JSONResponse(progress.model_dump(mode="json", by_alias=True), headers={"Cache-Control": "no-store"})

    @app.post(
        "/v1/ocr", response_model=OCRResponse, response_model_by_alias=True,
        tags=["OCR"], summary="อ่าน PDF หรือรูปภาพเป็น Markdown",
        description="Upload one document. Page numbers are 1-based. max_pages is capped by "
        "the server limit. Blank pages count as processed pages with empty Markdown. "
        "The response arrives after processing completes; use a long client timeout.",
        responses={
            409: {"description": "request_id ซ้ำ"},
            429: {"description": "คำขอที่ติดตามเต็ม กรุณารอแล้วลองใหม่"},
            400: {"description": "หน้าเริ่มต้นเกินจำนวนหน้าในเอกสาร"},
            413: {"description": "ขนาดไฟล์เกินขีดจำกัด"},
            415: {"description": "ไฟล์ไม่รองรับ เสียหาย หรือ PDF ติดรหัสผ่าน"},
            503: {"description": "โหลดโมเดลไม่สำเร็จ"},
        },
    )
    async def ocr(
        request: Request,
        file: UploadFile = File(..., description="PDF, JPEG, PNG, WebP, TIFF or BMP"),
        start_page: int = Form(1, ge=1, description="First page to read (1-based)"),
        max_pages: Optional[int] = Form(None, ge=1, description="Pages to read from start_page"),
        include_raw: bool = Form(False, description="Also return the raw model output per page"),
        request_id: Optional[UUID] = Form(None, description="Optional unique UUID for progress tracking and temporary result recovery. Results expire after up to 15 minutes; max 16 tracked requests."),
    ):
        tracked = str(request_id) if request_id else None
        if tracked:
            try:
                requests.begin(tracked)
            except ValueError as exc:
                raise HTTPException(409, str(exc))
            except OverflowError as exc:
                raise HTTPException(429, str(exc))
        log.info("OCR request %s accepted", tracked or "untracked")
        try:
            result = await process_document(request, file, start_page, max_pages, include_raw, tracked)
            requests.finish(tracked, result=result)
            return result
        except HTTPException as exc:
            requests.finish(tracked, error=str(exc.detail))
            raise
        except Exception:
            requests.finish(tracked, error="OCR request failed; check server logs")
            raise

    async def process_document(request, file, start_page, max_pages, include_raw, tracked):
        started = time.perf_counter()
        limit = settings.max_file_mb * 1024 * 1024
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"File is larger than {settings.max_file_mb} MB")
        try:
            doc = await run_in_threadpool(open_document, data, settings.pdf_dpi)
        except UnsupportedFile as exc:
            raise HTTPException(415, str(exc))
        if start_page > doc.total_pages:
            raise HTTPException(400, f"start_page {start_page} is beyond the last page ({doc.total_pages})")
        count = min(max_pages or settings.max_pages, settings.max_pages)

        requests.update(tracked, selected_pages=min(count, doc.total_pages - start_page + 1))
        if engine.state != "ready":
            requests.update(tracked, phase="loading")
            try:
                await run_in_threadpool(engine.wait_ready)
            except Exception as exc:
                raise HTTPException(503, f"Model is not available: {engine.error or exc}")

        pages: list[PageResult] = []
        iterator = doc.iter_pages(start_page, count)
        while True:
            item = await run_in_threadpool(next, iterator, None)
            if item is None:
                break
            number, image = item
            t0 = time.perf_counter()
            result = PageResult(page=number, width=image.width, height=image.height)
            try:
                requests.update(tracked, phase="queued", current_page=number)
                if tracked:
                    parsed = await run_in_threadpool(
                        engine.parse_page, image,
                        on_started=lambda: requests.update(tracked, phase="processing"),
                    )
                else:
                    parsed = await run_in_threadpool(engine.parse_page, image)
                result.markdown = parsed.get("markdown", "")
                result.blocks = [
                    Block(
                        **{"class": b.get("class", "")},
                        box=b.get("bbox", []),
                        box_pixels=b.get("bbox_pixels"),
                        content=b.get("content", ""),
                        text=b.get("text", ""),
                    )
                    for b in parsed.get("blocks", [])
                ]
                result.warnings = parsed.get("warnings", [])
                if include_raw:
                    result.raw = parsed.get("raw_out")
            except PageError as exc:
                result.error = str(exc)
                log.warning("Page %d of %s failed: %s", number, file.filename, exc)
            result.elapsed_ms = int((time.perf_counter() - t0) * 1000)
            log.info("%s page %d: %.1f s", file.filename, number, result.elapsed_ms / 1000)
            pages.append(result)
            requests.update(tracked, completed_pages=len(pages))
            if await request.is_disconnected():
                log.info("Client disconnected; stopping after page %d", number)
                break

        combined = "\n\n".join(
            p.markdown if p.error is None else f"<!-- page {p.page} could not be read: {p.error} -->"
            for p in pages
        )
        return OCRResponse(
            model=settings.model_id,
            revision=settings.model_revision,
            runtime_version=getattr(engine, "runtime_version", None),
            device=engine.device,
            filename=file.filename,
            file_type=doc.file_type,
            total_pages=doc.total_pages,
            page_count=len(pages),
            pages=pages,
            markdown=combined,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    # Mount last so API routes and their error responses remain independent of the UI.
    frontend = Path(settings.frontend_dir)
    if (frontend / "index.html").is_file():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")

    return app


app = create_app()
