"""Settings, read from environment variables (prefix OCR_) or a local .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OCR_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    host: str = "127.0.0.1"
    port: int = 8090
    # Built React assets. Optional when running the API alone.
    frontend_dir: str = "frontend/dist"

    model_id: str = "iapp/OpenThai2.1-OCR-Markdown-20261118"
    # OpenThai 2.1 weights + v2.2.0 runtime (nemotron-parse 3.5.0.post8).
    # Pinned Hugging Face commit, so an upstream change cannot silently alter results.
    # Change the model snapshot and installed runtime together; rebuild Docker after upgrades.
    model_revision: str = "c974dc7d18a4511a21988f4a1d12fad07ac16625"
    # auto = cuda if available, else mps (Apple silicon), else cpu
    device: str = "auto"
    # Load the model in the background as soon as the server starts.
    # If false, the model loads on the first OCR request.
    preload: bool = True
    # Only use files already in the Hugging Face cache (no network).
    local_files_only: bool = False

    max_file_mb: int = 50
    max_pages: int = 20
    pdf_dpi: int = 200  # the official guide renders PDF pages at 200 dpi
    max_new_tokens: int = 8744  # upstream default token limit per page

    # Browsers on these origins may call the API (regex). Local tool: localhost only.
    cors_origin_regex: str = r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?"


@lru_cache
def get_settings() -> Settings:
    return Settings()
