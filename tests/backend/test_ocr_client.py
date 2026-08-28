import httpx
import pytest

from adapters.ocr_client import OcrClient, load_ocr_client


class _FakeResponse:
    def __init__(self, json_data):
        self._json = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def test_reconocer_devuelve_latex(monkeypatch):
    client = OcrClient(base_url="http://ocr")

    def _fake_post(url, files, timeout):
        assert url == "http://ocr/ocr"
        return _FakeResponse({"latex": "x^2"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    assert client.reconocer(b"imagen") == "x^2"


def test_reconocer_error_http_se_traduce_en_runtime_error(monkeypatch):
    client = OcrClient(base_url="http://ocr")

    def _fake_post(url, files, timeout):
        raise httpx.ConnectTimeout("timeout", request=None)

    monkeypatch.setattr(httpx, "post", _fake_post)

    with pytest.raises(RuntimeError, match="Error llamando a service/ocr"):
        client.reconocer(b"imagen")


def test_load_ocr_client_usa_env(monkeypatch):
    monkeypatch.setenv("OCR_SERVICE_URL", "http://custom-ocr:9001")
    client = load_ocr_client()
    assert client.base_url == "http://custom-ocr:9001"


def test_load_ocr_client_usa_default(monkeypatch):
    monkeypatch.delenv("OCR_SERVICE_URL", raising=False)
    client = load_ocr_client()
    assert client.base_url == "http://127.0.0.1:8001"
