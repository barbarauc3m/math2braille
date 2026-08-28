import httpx
import pytest

from adapters.yolo_client import DetectedBox, YoloClient, load_yolo_client


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json


def test_detectar_devuelve_cajas(monkeypatch):
    client = YoloClient(base_url="http://yolo/")

    def _fake_post(url, files, timeout):
        assert url == "http://yolo/detect"
        return _FakeResponse({"boxes": [
            {"x": 1.0, "y": 2.0, "ancho": 3.0, "alto": 4.0, "confidence_score": 0.9}
        ]})

    monkeypatch.setattr(httpx, "post", _fake_post)

    cajas = client.detectar(b"imagen")
    assert cajas == [DetectedBox(x=1.0, y=2.0, ancho=3.0, alto=4.0, confidence_score=0.9)]


def test_detectar_error_http_se_traduce_en_runtime_error(monkeypatch):
    client = YoloClient(base_url="http://yolo")

    def _fake_post(url, files, timeout):
        raise httpx.ConnectError("no se pudo conectar", request=None)

    monkeypatch.setattr(httpx, "post", _fake_post)

    with pytest.raises(RuntimeError, match="Error llamando a service/yolo"):
        client.detectar(b"imagen")


def test_base_url_se_normaliza_sin_barra_final():
    client = YoloClient(base_url="http://yolo/")
    assert client.base_url == "http://yolo"


def test_load_yolo_client_usa_env(monkeypatch):
    monkeypatch.setenv("YOLO_SERVICE_URL", "http://custom-yolo:9000")
    client = load_yolo_client()
    assert client.base_url == "http://custom-yolo:9000"


def test_load_yolo_client_usa_default(monkeypatch):
    monkeypatch.delenv("YOLO_SERVICE_URL", raising=False)
    client = load_yolo_client()
    assert client.base_url == "http://127.0.0.1:8000"
