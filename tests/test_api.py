"""API tests with a fake engine, so they run without the model or a GPU."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.engine import PageError
from app.main import create_app
from app.pages import open_document


class FakeEngine:
    def __init__(self, fail_pages=()):
        self.state, self.error, self.device, self.load_seconds = "ready", None, "cpu", 0.0
        self.calls = 0
        self.fail_pages = set(fail_pages)

    def start_background_load(self):
        pass

    def wait_ready(self, timeout=None):
        pass

    def parse_page(self, image):
        self.calls += 1
        if self.calls in self.fail_pages:
            raise PageError("GenerationError: cut off at the token limit")
        return {
            "markdown": f"# หน้า {self.calls}",
            "blocks": [{"class": "Title", "bbox": [0, 0, 1, 1], "bbox_pixels": [0, 0, 10, 10],
                        "text": f"# หน้า {self.calls}", "content": f"หน้า {self.calls}"}],
            "warnings": [],
            "raw_out": "raw",
        }


def png_bytes(color="white", fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", (60, 80), color).save(buf, fmt)
    return buf.getvalue()


def pdf_bytes(pages=3):
    buf = io.BytesIO()
    imgs = [Image.new("RGB", (60, 80), "white") for _ in range(pages)]
    imgs[0].save(buf, "PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def client(engine=None, **kw):
    settings = Settings(_env_file=None, preload=False, **kw)
    return TestClient(create_app(settings, engine or FakeEngine()))


def test_health_and_info():
    c = client()
    assert c.get("/health").json()["model_loaded"] is True
    info = c.get("/v1/info").json()
    assert "pdf" in info["supported_types"] and info["max_pages"] == 20


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP", "TIFF", "BMP"])
def test_image_formats(fmt):
    r = client().post("/v1/ocr", files={"file": (f"a.{fmt.lower()}", png_bytes(fmt=fmt))})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["page_count"] == 1 and body["pages"][0]["blocks"][0]["class"] == "Title"


def test_pdf_split_and_range():
    r = client().post("/v1/ocr", files={"file": ("a.pdf", pdf_bytes(5))},
                      data={"start_page": "2", "max_pages": "2"})
    body = r.json()
    assert body["total_pages"] == 5 and [p["page"] for p in body["pages"]] == [2, 3]
    assert body["markdown"] == "# หน้า 1\n\n# หน้า 2"


def test_server_page_cap():
    body = client(max_pages=2).post("/v1/ocr", files={"file": ("a.pdf", pdf_bytes(4))},
                                    data={"max_pages": "10"}).json()
    assert body["page_count"] == 2


def test_failed_page_does_not_fail_document():
    body = client(FakeEngine(fail_pages={2})).post(
        "/v1/ocr", files={"file": ("a.pdf", pdf_bytes(3))}).json()
    assert [p["error"] is None for p in body["pages"]] == [True, False, True]
    assert "could not be read" in body["markdown"]


def test_rejects_bad_input():
    c = client(max_file_mb=1)
    assert c.post("/v1/ocr", files={"file": ("a.txt", b"hello")}).status_code == 415
    assert c.post("/v1/ocr", files={"file": ("a.pdf", b"")}).status_code == 415
    assert c.post("/v1/ocr", files={"file": ("big.png", b"0" * (1024 * 1024 + 1))}).status_code == 413
    assert c.post("/v1/ocr", files={"file": ("a.pdf", pdf_bytes(2))},
                  data={"start_page": "3"}).status_code == 400
    gif = io.BytesIO(); Image.new("RGB", (5, 5)).save(gif, "GIF")
    assert c.post("/v1/ocr", files={"file": ("a.gif", gif.getvalue())}).status_code == 415


def test_open_document_counts_pdf_pages():
    assert open_document(pdf_bytes(4)).total_pages == 4


def test_serves_frontend_without_swallowing_api_routes(tmp_path):
    (tmp_path / 'index.html').write_text('<html>OCR Workspace</html>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets' / 'app.js').write_text('console.log("ui")')
    c = client(frontend_dir=str(tmp_path))
    assert 'OCR Workspace' in c.get('/').text
    assert c.get('/assets/app.js').status_code == 200
    assert c.get('/health').json()['model_state'] == 'ready'
    assert c.get('/v1/missing').status_code == 404
    assert c.post('/v1/ocr', files={'file': ('x.png', png_bytes())}).status_code == 200


def test_api_works_without_frontend(tmp_path):
    c = client(frontend_dir=str(tmp_path / 'missing'))
    assert c.get('/').status_code == 404
    assert c.get('/health').status_code == 200


def test_openapi_documents_upgraded_model_and_runtime():
    c = client()
    spec = c.get('/openapi.json').json()
    assert spec['info']['version'] == '0.2.0'
    description = spec['info']['description']
    assert 'iapp/OpenThai2.1-OCR-Markdown-20261118' in description
    assert 'c974dc7d18a4511a21988f4a1d12fad07ac16625' in description
    assert 'NVIDIA' in description and 'OpenMDW-1.1' in description
    assert 'v2.2.0' in description
    assert 'runtime_version' in spec['components']['schemas']['Health']['properties']
    assert 'runtime_version' in spec['components']['schemas']['OCRResponse']['properties']
    assert '503' in spec['paths']['/v1/ocr']['post']['responses']


def test_model_identity_matches_health_info_and_result():
    engine = FakeEngine()
    engine.runtime_version = '3.5.0.post8'
    c = client(engine)
    result = c.post('/v1/ocr', files={'file': ('scan.png', png_bytes())}).json()
    for body in [c.get('/health').json(), c.get('/v1/info').json(), result]:
        assert body['model'] == 'iapp/OpenThai2.1-OCR-Markdown-20261118'
        assert body['revision'] == 'c974dc7d18a4511a21988f4a1d12fad07ac16625'
        assert body['runtime_version'] == '3.5.0.post8'
