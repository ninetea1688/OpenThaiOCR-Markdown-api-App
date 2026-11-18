"""Call the OCR Markdown API from another Python project (needs: pip install httpx).

    python examples/client.py document.pdf
"""

import sys
from pathlib import Path

import httpx

API = "http://127.0.0.1:8090"


def ocr_file(path: str, start_page: int = 1, max_pages: int = 5) -> dict:
    p = Path(path)
    with p.open("rb") as f, httpx.Client(timeout=3600) as client:
        r = client.post(
            f"{API}/v1/ocr",
            files={"file": (p.name, f)},
            data={"start_page": start_page, "max_pages": max_pages},
        )
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    result = ocr_file(sys.argv[1])
    for page in result["pages"]:
        status = page["error"] or f"{len(page['blocks'])} blocks"
        print(f"page {page['page']}: {page['elapsed_ms'] / 1000:.1f} s, {status}", file=sys.stderr)
    print(result["markdown"])
