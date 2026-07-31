"""
Adaptador HTTP hacia service/ocr (RF-05).

Se invoca bajo demanda desde FormulaService, una vez por cada fórmula
que el usuario selecciona en el visor y que todavía no tiene mathml
en caché (CU-03).
"""

import os

import httpx


class OcrClient:
    def __init__(self, base_url: str, timeout: float = 60.0):
        # Timeout más alto que YoloClient: pix2tex sobre CPU puede
        # tardar más que una detección YOLO.
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def reconocer(self, image_bytes: bytes) -> str:
        """Envía el recorte de una fórmula y devuelve el LaTeX reconocido."""
        files = {"file": ("formula.png", image_bytes, "image/png")}

        try:
            response = httpx.post(f"{self.base_url}/ocr", files=files, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Error llamando a service/ocr: {e}") from e

        return response.json()["latex"]


def load_ocr_client() -> OcrClient:
    base_url = os.environ.get("OCR_SERVICE_URL", "http://127.0.0.1:8001")
    return OcrClient(base_url=base_url)