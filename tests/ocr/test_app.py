import io

from fastapi.testclient import TestClient
from PIL import Image

from tests.ocr.conftest import FakeLatexOCR


def _png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (350, 100), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_health():
    import app

    client = TestClient(app.app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ocr_imagen_vacia_400():
    import app

    client = TestClient(app.app)
    response = client.post("/ocr", files={"file": ("f.png", b"", "image/png")})

    assert response.status_code == 400


def test_ocr_exitoso_200():
    import app

    client = TestClient(app.app)
    response = client.post("/ocr", files={"file": ("f.png", _png_bytes(), "image/png")})

    assert response.status_code == 200
    assert response.json() == {"latex": "x^{2}"}


def test_ocr_error_interno_500(monkeypatch):
    import app

    def _boom(image_bytes):
        raise RuntimeError("modelo roto")

    monkeypatch.setattr(app.recognizer, "recognize", _boom)

    client = TestClient(app.app)
    response = client.post("/ocr", files={"file": ("f.png", _png_bytes(), "image/png")})

    assert response.status_code == 500
    assert "modelo roto" in response.json()["detail"]
