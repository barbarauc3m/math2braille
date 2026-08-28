import cv2
import numpy as np
from fastapi.testclient import TestClient


def _png_bytes():
    imagen = np.full((200, 200, 3), 255, dtype=np.uint8)
    ok, buffer = cv2.imencode(".png", imagen)
    assert ok
    return buffer.tobytes()


def test_health():
    import app

    client = TestClient(app.app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_detect_imagen_vacia_400():
    import app

    client = TestClient(app.app)
    response = client.post("/detect", files={"file": ("p.png", b"", "image/png")})

    assert response.status_code == 400


def test_detect_imagen_invalida_400():
    import app

    client = TestClient(app.app)
    response = client.post("/detect", files={"file": ("p.png", b"no es imagen", "image/png")})

    assert response.status_code == 400


def test_detect_imagen_valida_200():
    import app

    client = TestClient(app.app)
    response = client.post("/detect", files={"file": ("p.png", _png_bytes(), "image/png")})

    assert response.status_code == 200
    assert "boxes" in response.json()
