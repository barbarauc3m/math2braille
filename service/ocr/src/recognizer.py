"""
Wrapper sobre pix2tex (LaTeX-OCR).

A diferencia de service/yolo (detección adelantada/eager), este
servicio se invoca bajo demanda (solo cuando el usuario selecciona una fórmula concreta en el visor).

El LaTeX que devuelve es un formato transitorio (no se persiste en SQLite): FormulaService lo pasa inmediatamente a MathmlConverter para obtener el MathML que sí se guarda en la tabla `formula`.

De forma previa al reconocimiento, se realiza un reescalado de la imagen para reducir su dimensión a un ancho de 300px, pues se comprobó de forma empírica que pix2tex realiza mejores predicciones con imágenes más pequeñas. El reescalado se hace manteniendo el aspect ratio y sin recortar la imagen, para no perder información de la fórmula.
"""

import io
import os

from PIL import Image
from pix2tex.cli import LatexOCR

OCR_TARGET_WIDTH_PX = int(os.environ.get("OCR_TARGET_WIDTH_PX", "300"))


class FormulaRecognizer:
    def __init__(self, target_width_px: int = OCR_TARGET_WIDTH_PX):
        # La descarga de pesos ya ocurrió en tiempo de build (ver Dockerfile); aquí solo se cargan desde la caché local, sin necesidad de red.
        self.model = LatexOCR()
        self.target_width_px = target_width_px

    def _reescalar(self, image: Image.Image) -> Image.Image:
        """
        Reescala manteniendo la proporción, tanto si el recorte es más grande como más pequeño que el ancho objetivo
        """
        if image.width == self.target_width_px:
            return image

        ratio = self.target_width_px / image.width
        alto_objetivo = max(int(image.height * ratio), 1)
        return image.resize((self.target_width_px, alto_objetivo))

    def recognize(self, image_bytes: bytes) -> str:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image = self._reescalar(image)
        return self.model(image)


def load_recognizer() -> FormulaRecognizer:
    return FormulaRecognizer()