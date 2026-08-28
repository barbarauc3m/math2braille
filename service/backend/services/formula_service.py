"""
FormulaService — orquesta la consulta y edición de fórmulas.

Consulta la caché de mathml y permite la edición manual antes de guardar.
"""

import io
import os
from typing import Callable, List, Optional

from PIL import Image

from adapters.ocr_client import OcrClient
from models.formula import Formula
from repositories.documento_repository import DocumentoRepository
from repositories.formula_repository import FormulaRepository
from services.exceptions import DocumentoNoEncontradoError, FormulaNoEncontradaError, ProcesamientoFormulaError
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

    def _procesar_formula(self, formula: Formula, pagina_bytes: Optional[bytes] = None) -> Formula:
        """
        Ejecuta OCR + conversión a MathML + validación sobre UNA fórmula
        concreta y persiste el resultado. No comprueba `ya_procesada`:
        esa decisión es responsabilidad de quien invoca —
        consultar_formula y procesar_formulas_pagina la comprueban por
        razones distintas (caché de una sola fórmula vs. saltarse las
        ya traducidas de un lote).

        `pagina_bytes` permite reutilizar una única rasterización de la
        página entre varias llamadas: procesar_formulas_pagina rasteriza
        la página UNA vez para todas sus fórmulas pendientes, en vez de
        una vez por fórmula (que es justo el coste que se quiere evitar
        al procesar en bloque). Si no se pasa (caso de consultar_formula
        sobre una única fórmula), se rasteriza aquí igual que antes.
        """
        if pagina_bytes is None:
            documento = self.documento_repository.obtener_por_id(formula.documento_id)
            if documento is None:
                raise FormulaNoEncontradaError(
                    f"La fórmula {formula.id} referencia un documento inexistente"
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

    def consultar_formula(self, formula_id: int) -> Formula:
        """
        Si la fórmula ya tiene mathml en caché, se devuelve
        directamente sin tocar OCR (evita recalcular en cada apertura
        del documento). Si no, se recorta la región, se manda a
        service/ocr, se convierte a MathML y se valida antes de
        persistir.
        """
        formula = self.formula_repository.obtener_por_id(formula_id)
        if formula is None:
            raise FormulaNoEncontradaError(f"No existe la fórmula {formula_id}")

        if formula.ya_procesada:
            return formula

        return self._procesar_formula(formula)

    def editar_formula(self, formula_id: int, mathml_editado: str) -> Formula:
        """
        Valida el MathML editado manualmente por el
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


    def obtener_formulas_documento(self, documento_id: int) -> List["Formula"]:
        return self.formula_repository.obtener_por_documento(documento_id)

    def procesar_formulas_pagina(
        self,
        documento_id: int,
        numero_pagina: int,
        on_progreso: Optional[Callable[[int, int, Formula], None]] = None,
        on_error_formula: Optional[Callable[[int, str], None]] = None,
    ) -> List[Formula]:
        """
        "Procesar todas" (ajuste opcional del visor): procesa en bloque
        todas las fórmulas todavía sin mathml de una página, en vez de
        esperar a que el usuario las seleccione una a una.

        Un fallo de OCR/conversión en una fórmula concreta NO interrumpe
        el resto del lote: se reporta vía on_error_formula (si se pasa)
        y se sigue con la siguiente — igual que un formulario con varios
        campos, un error aislado no debería tirar todo lo demás.
        Devuelve solo las fórmulas procesadas con éxito en esta llamada;
        las que ya estaban en caché no se incluyen porque no ha habido
        ningún procesamiento nuevo que reportar.
        """
        documento = self.documento_repository.obtener_por_id(documento_id)
        if documento is None:
            raise DocumentoNoEncontradoError(f"No existe el documento {documento_id}")

        formulas_pagina = [
            f for f in self.formula_repository.obtener_por_documento(documento_id)
            if f.pagina == numero_pagina
        ]
        pendientes = [f for f in formulas_pagina if not f.ya_procesada]

        if not pendientes:
            return []

        # Una única rasterización para todas las fórmulas pendientes de
        # la página (ver docstring de _procesar_formula).
        pagina_bytes = self.pdf_rasterizer.rasterizar_pagina(documento.ruta_archivo, numero_pagina)

        procesadas: List[Formula] = []
        total = len(pendientes)
        for indice, formula in enumerate(pendientes, start=1):
            try:
                formula_actualizada = self._procesar_formula(formula, pagina_bytes=pagina_bytes)
            except ProcesamientoFormulaError as e:
                if on_error_formula:
                    on_error_formula(formula.id, str(e))
                continue

            procesadas.append(formula_actualizada)
            if on_progreso:
                on_progreso(indice, total, formula_actualizada)

        return procesadas

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