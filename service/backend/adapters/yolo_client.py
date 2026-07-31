"""
Adaptador HTTP hacia service/yolo (RF-03).

Aísla al resto del backend del protocolo concreto (HTTP + multipart)
usado para hablar con el servicio de detección, y permite mockear
DocumentoService en tests sin levantar el contenedor de yolo
(justificación OOP, Secc. 5.3).
"""

import os
from dataclasses import dataclass
from typing import List

import httpx


@dataclass
class DetectedBox:
    x: float
    y: float
    ancho: float
    alto: float
    confidence_score: float


class YoloClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def detectar(self, image_bytes: bytes) -> List[DetectedBox]:
        """Envía la imagen de una página y devuelve las cajas detectadas."""
        files = {"file": ("page.png", image_bytes, "image/png")}

        try:
            response = httpx.post(f"{self.base_url}/detect", files=files, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Error llamando a service/yolo: {e}") from e

        data = response.json()
        return [DetectedBox(**box) for box in data["boxes"]]


def load_yolo_client() -> YoloClient:
    base_url = os.environ.get("YOLO_SERVICE_URL", "http://127.0.0.1:8000")
    return YoloClient(base_url=base_url)