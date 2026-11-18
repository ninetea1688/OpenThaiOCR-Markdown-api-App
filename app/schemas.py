"""Response models (shown in the OpenAPI docs at /docs)."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Block(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    class_: str = Field(alias="class", description="Block class, e.g. Text, Title, Table, Picture")
    box: list[float] = Field(description="Box normalized to the model's content frame [x1, y1, x2, y2]")
    box_pixels: Optional[list[float]] = Field(None, description="Box in pixels of the page image")
    content: str = Field(description="Rendered content (Markdown; tables as HTML)")
    text: str = Field(description="Raw block text as predicted by the model")


class PageResult(BaseModel):
    page: int = Field(description="1-based page number in the original file")
    width: Optional[int] = None
    height: Optional[int] = None
    markdown: str = ""
    blocks: list[Block] = []
    warnings: list[Any] = []
    error: Optional[str] = None
    raw: Optional[str] = Field(None, description="Cleaned raw model output (only with include_raw=true)")
    elapsed_ms: int = 0


class OCRResponse(BaseModel):
    model: str = Field(description="Hugging Face model repository ID")
    revision: str = Field(description="Configured pinned Hugging Face revision, separate from API version")
    runtime_version: Optional[str] = Field(None, description="Installed nemotron-parse package version")
    device: Optional[str]
    filename: Optional[str]
    file_type: str
    total_pages: int = Field(description="Pages in the uploaded file")
    page_count: int = Field(description="Pages processed in this request")
    pages: list[PageResult]
    markdown: str = Field(description="Rendered Markdown of all pages in order. OpenThai 2.1 uses HTML tables, "
                         "$$ LaTeX, normalized sara am and omits page headers/footers. Blank pages are empty.")
    elapsed_ms: int


class Health(BaseModel):
    status: str
    model_state: str = Field(description="not_loaded | loading | ready | error")
    model_loaded: bool
    model_error: Optional[str]
    device: Optional[str]
    model: str
    revision: str
    version: str = Field(description="API application version; not the OCR model version")
    runtime_version: Optional[str] = Field(None, description="Installed nemotron-parse package version, or null if absent")


class RequestProgress(BaseModel):
    request_id: str
    server_id: str
    phase: Literal["validating", "loading", "queued", "processing", "completed", "error"]
    current_page: Optional[int] = None
    completed_pages: int = 0
    selected_pages: int = 0
    elapsed_ms: int = 0
    error: Optional[str] = None
    result: Optional[OCRResponse] = Field(None, description="Finished result, cached in memory for up to 15 minutes (16 requests maximum)")


class Info(Health):
    server_id: str = Field(description="Changes on server restart; pending requests from older instances cannot resume")
    supported_types: list[str]
    max_file_mb: int
    max_pages: int
    pdf_dpi: int
    max_new_tokens: int
    concurrency: str
    load_seconds: Optional[float]
