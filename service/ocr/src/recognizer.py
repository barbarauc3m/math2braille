"""
Wrapper sobre pix2tex (LaTeX-OCR).

A diferencia de service/yolo (detección adelantada/eager), este
servicio se invoca bajo demanda (lazy loading, Secc. 5.1.2): solo
cuando el usuario selecciona una fórmula concreta en el visor (CU-03).
El modelo, sin embargo, se carga una única vez al arrancar el
contenedor (ver load_recognizer() en app.py) y se reutiliza en todas
las peticiones — lo que es "lazy" es la llamada por fórmula, no la
carga del modelo en memoria.

El LaTeX que devuelve es un formato transitorio (no se persiste en
SQLite): FormulaService lo pasa inmediatamente a MathmlConverter
(RF-06) para obtener el MathML que sí se guarda en la tabla `formula`.
"""

import io

from PIL import Image
from pix2tex.cli import LatexOCR


class FormulaRecognizer:
    def __init__(self):
        # La descarga de pesos se hizo en tiempo de build (ver
        # Dockerfile); aquí solo se cargan desde la caché local, sin
        # necesidad de red.
        self.model = LatexOCR()

    def recognize(self, image_bytes: bytes) -> str:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return self.model(image)


def load_recognizer() -> FormulaRecognizer:
    return FormulaRecognizer()