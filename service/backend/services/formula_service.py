"""
FormulaService — orquesta la consulta y edición de fórmulas.

Consulta la caché de mathml y permite la edición manual antes de guardar.
"""

import io
import os
from typing import List

from PIL import Image

from adapters.ocr_client import OcrClient
from models.formula import Formula
from repositories.documento_repository import DocumentoRepository
from repositories.formula_repository import FormulaRepository
from services.exceptions import FormulaNoEncontradaError, ProcesamientoFormulaError
from utils.mathml_converter import MathmlConversionError, MathmlConverter
from utils.pdf_rasterizer import PdfRasterizer
from utils.xhtml_validator import XhtmlValidationError, XhtmlValidator


class FormulaService:
    def __init__(
        self,
        formula_repository: FormulaRepository,
        documento_repository: DocumentoRepository,
        pdf_rasterizer: PdfRasterizer,
        ocr_client: OcrClient,
        mathml_converter: MathmlConverter,
        xhtml_validator: XhtmlValidator,
        bbox_margin_px: int = 10,
    ):
        self.formula_repository = formula_repository
        self.documento_repository = documento_repository
        self.pdf_rasterizer = pdf_rasterizer
        self.ocr_client = ocr_client
        self.mathml_converter = mathml_converter
        self.xhtml_validator = xhtml_validator
        self.bbox_margin_px = bbox_margin_px

    def _recortar_formula(self, pagina_bytes: bytes, formula: Formula) -> bytes:
        """
        Recorta la región de la fórmula sobre la imagen de la página,
        con un margen de seguridad (BBOX_MARGIN_PX) alrededor del
        bounding box, para no cortar de más justo en el borde detectado
        por YOLO y perjudicar el reconocimiento de pix2tex.
        """
        imagen = Image.open(io.BytesIO(pagina_bytes)).convert("RGB")

        x1 = max(formula.x - self.bbox_margin_px, 0)
        y1 = max(formula.y - self.bbox_margin_px, 0)
        x2 = min(formula.x + formula.ancho + self.bbox_margin_px, imagen.width)
        y2 = min(formula.y + formula.alto + self.bbox_margin_px, imagen.height)

        recorte = imagen.crop((x1, y1, x2, y2))
        buffer = io.BytesIO()
        recorte.save(buffer, format="PNG")
        return buffer.getvalue()

    def consultar_formula(self, formula_id: int) -> Formula:
        """
        CU-03: si la fórmula ya tiene mathml en caché, se devuelve
        directamente sin tocar OCR (evita recalcular en cada apertura
        del documento). Si no, se recorta la región, se manda a
        service/ocr, se convierte a MathML y se valida antes de
        persistir (RF-05, RF-06, RF-11).
        """
        formula = self.formula_repository.obtener_por_id(formula_id)
        if formula is None:
            raise FormulaNoEncontradaError(f"No existe la fórmula {formula_id}")

        if formula.ya_procesada:
            return formula

        documento = self.documento_repository.obtener_por_id(formula.documento_id)
        if documento is None:
            raise FormulaNoEncontradaError(
                f"La fórmula {formula_id} referencia un documento inexistente"
            )

        pagina_bytes = self.pdf_rasterizer.rasterizar_pagina(documento.ruta_archivo, formula.pagina)
        recorte_bytes = self._recortar_formula(pagina_bytes, formula)

        try:
            latex = self.ocr_client.reconocer(recorte_bytes)
            mathml = self.mathml_converter.convertir(latex)
            self.xhtml_validator.validar_fragmento_mathml(mathml)
        except MathmlConversionError as e:
            raise ProcesamientoFormulaError(str(e)) from e
        except XhtmlValidationError as e:
            # Un MathML generado automáticamente que no valida indica un
            # problema en el LaTeX reconocido por pix2tex, no un error
            # del usuario: se trata igual que un fallo de procesamiento.
            raise ProcesamientoFormulaError(f"MathML generado inválido: {e}") from e

        return self.formula_repository.actualizar_mathml(formula.id, mathml)

    def editar_formula(self, formula_id: int, mathml_editado: str) -> Formula:
        """
        RF-12 (CU-04): valida el MathML editado manualmente por el
        usuario ANTES de guardarlo. Si no valida, se lanza
        XhtmlValidationError sin tocar la base de datos — el mathml
        anterior se conserva intacto, tal y como exige RF-11.
        """
        formula = self.formula_repository.obtener_por_id(formula_id)
        if formula is None:
            raise FormulaNoEncontradaError(f"No existe la fórmula {formula_id}")

        # Puede lanzar XhtmlValidationError: se deja propagar tal cual
        # hacia el controller, que la traduce en un error accesible
        # (RF-20, aria-live="assertive") sin modificar formula.mathml.
        self.xhtml_validator.validar_fragmento_mathml(mathml_editado)

        return self.formula_repository.actualizar_mathml(formula_id, mathml_editado)


def load_formula_service() -> FormulaService:
    from adapters.ocr_client import load_ocr_client

    return FormulaService(
        formula_repository=FormulaRepository(),
        documento_repository=DocumentoRepository(),
        pdf_rasterizer=PdfRasterizer(),
        ocr_client=load_ocr_client(),
        mathml_converter=MathmlConverter(),
        xhtml_validator=XhtmlValidator(),
        bbox_margin_px=int(os.environ.get("BBOX_MARGIN_PX", "10")),
    )

def obtener_formulas_documento(self, documento_id: int) -> List["Formula"]:
    return self.formula_repository.obtener_por_documento(documento_id)