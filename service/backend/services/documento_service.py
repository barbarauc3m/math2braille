"""
DocumentoService — orquesta la carga de documentos y el historial.

Punto donde se conectan los repositorios, adaptadores y utilidades.
El propio servicio no trabaja directamente con SQL ni HTTP, sino que coordina las llamadas a estos componentes especializados.
"""

import os
import uuid
from pathlib import Path
from typing import Callable, List, Optional

from adapters.yolo_client import YoloClient
from models.documento import Documento
from models.formula import Formula
from repositories.documento_repository import DocumentoRepository
from repositories.formula_repository import FormulaRepository
from services.exceptions import DocumentoNoEncontradoError
from utils.pdf_rasterizer import PdfRasterizer

# Callback de progreso: recibe (pagina_actual, total_paginas).
ProgresoCallback = Callable[[int, int], None]


class DocumentoService:
    def __init__(
        self,
        documento_repository: DocumentoRepository,
        formula_repository: FormulaRepository,
        pdf_rasterizer: PdfRasterizer,
        yolo_client: YoloClient,
        uploads_path: str,
    ):
        self.documento_repository = documento_repository
        self.formula_repository = formula_repository
        self.pdf_rasterizer = pdf_rasterizer
        self.yolo_client = yolo_client
        self.uploads_path = uploads_path

    def _guardar_pdf(self, pdf_bytes: bytes, nombre_archivo: str) -> str:
        """
        Guarda el PDF subido con un nombre único en disco (evita
        colisiones si dos documentos se llaman igual) y devuelve la ruta absoluta, que es lo que se persiste en documento.ruta_archivo.
        """
        Path(self.uploads_path).mkdir(parents=True, exist_ok=True)
        nombre_unico = f"{uuid.uuid4().hex}_{nombre_archivo}"
        ruta_archivo = os.path.join(self.uploads_path, nombre_unico)

        with open(ruta_archivo, "wb") as f:
            f.write(pdf_bytes)

        return ruta_archivo

    def cargar_documento(
        self,
        pdf_bytes: bytes,
        nombre_archivo: str,
        on_progreso: Optional[ProgresoCallback] = None,
    ) -> Documento:
        """
        Guarda el PDF, lo rasteriza página a página y ejecuta la detección adelantada (eager) de YOLO sobre cada una, guardando todas las fórmulas encontradas todavía sin mathml. 
        """
        ruta_archivo = self._guardar_pdf(pdf_bytes, nombre_archivo)
        num_paginas = self.pdf_rasterizer.num_paginas(ruta_archivo)

        documento = self.documento_repository.crear(
            Documento(nombre_archivo=nombre_archivo, ruta_archivo=ruta_archivo, num_paginas=num_paginas)
        )

        imagenes_por_pagina = self.pdf_rasterizer.rasterizar(ruta_archivo)
        formulas_detectadas: List[Formula] = []

        for indice, imagen_bytes in enumerate(imagenes_por_pagina):
            numero_pagina = indice + 1
            cajas = self.yolo_client.detectar(imagen_bytes)

            for caja in cajas:
                formulas_detectadas.append(Formula(
                    documento_id=documento.id,
                    pagina=numero_pagina,
                    x=caja.x,
                    y=caja.y,
                    ancho=caja.ancho,
                    alto=caja.alto,
                    confidence_score=caja.confidence_score,
                ))

            if on_progreso:
                on_progreso(numero_pagina, num_paginas)

        self.formula_repository.guardar_lote(documento.id, formulas_detectadas)
        return documento

    def listar_historial(self) -> List[Documento]:
        """RF-14."""
        return self.documento_repository.listar_historial()

    def abrir_documento(self, documento_id: int) -> Documento:
        """
        Reabre un documento del historial SIN volver a ejecutar YOLO — las fórmulas ya están en `formula` desde la
        carga original. Solo actualiza fecha_ultima_apertura.
        """
        documento = self.documento_repository.obtener_por_id(documento_id)
        if documento is None:
            raise DocumentoNoEncontradoError(f"No existe el documento {documento_id}")

        self.documento_repository.actualizar_fecha_apertura(documento_id)
        return documento

    def eliminar_documento(self, documento_id: int) -> None:
        """ El ON DELETE CASCADE de schema.sql se encarga de las fórmulas."""
        documento = self.documento_repository.obtener_por_id(documento_id)
        if documento is None:
            raise DocumentoNoEncontradoError(f"No existe el documento {documento_id}")

        self.documento_repository.eliminar(documento_id)

    def obtener_contenido_pagina(self, documento_id: int, numero_pagina: int) -> List[dict]:
        """
        Combina el texto real de la página con las fórmulas detectadas en ella, ordenados por posición vertical (y, luego x) para reconstruir el orden de lectura.
        """
        documento = self.documento_repository.obtener_por_id(documento_id)
        if documento is None:
            raise DocumentoNoEncontradoError(f"No existe el documento {documento_id}")

        bloques_texto = self.pdf_rasterizer.extraer_bloques_texto(documento.ruta_archivo, numero_pagina)
        formulas_pagina = [
            f for f in self.formula_repository.obtener_por_documento(documento_id)
            if f.pagina == numero_pagina
        ]

        # f.x / f.y están en píxeles de la imagen rasterizada a 200 dpi
        # (así los usa FormulaService para recortar), mientras que b["x"] /
        # b["y"] vienen de PyMuPDF en puntos PDF (72 pt/pulgada), sin
        # escalar. Si se comparan tal cual, el y de una fórmula sale ~2.78
        # veces mayor que el de un texto en la misma posición física, y las
        # fórmulas acaban ordenándose casi siempre después de todo el texto
        # de la página. Se dividen aquí por el mismo zoom usado al
        # rasterizar para llevarlas a puntos PDF, solo a efectos de orden;
        # no se modifica lo que hay guardado en la tabla formula.
        zoom = self.pdf_rasterizer.zoom
        elementos = (
            [{"tipo": "texto", "y": b["y"], "x": b["x"], "texto": b["texto"]} for b in bloques_texto]
            + [
                {"tipo": "formula", "y": f.y / zoom, "x": f.x / zoom, "formula": f}
                for f in formulas_pagina
            ]
        )
        elementos.sort(key=lambda e: (e["y"], e["x"]))
        return elementos


def load_documento_service() -> DocumentoService:
    """
    Factory que instancia DocumentoService con sus dependencias reales (BD real, servicios yolo/ocr reales). La usará main.py. Separarla de __init__ es lo que permite en tests construir el servicio con mocks en vez de llamar a esta función.
    """
    from adapters.yolo_client import load_yolo_client

    return DocumentoService(
        documento_repository=DocumentoRepository(),
        formula_repository=FormulaRepository(),
        pdf_rasterizer=PdfRasterizer(),
        yolo_client=load_yolo_client(),
        uploads_path=os.environ.get("UPLOADS_PATH", "./data/uploads"),
    )