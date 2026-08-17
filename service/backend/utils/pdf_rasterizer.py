"""
Rasterizado de PDF a imágenes por página (RF-02).

Usa PyMuPDF (fitz) en vez de pdf2image: no requiere ningún binario del
sistema (poppler-utils), lo cual encaja con el objetivo de servicios
ligeros y de configuración mínima (RNF-01, RNF-03).

Cada imagen resultante se envía tal cual a YoloClient para la
detección adelantada (eager, Secc. 5.1.2) de todas las páginas del
documento en el momento de la carga (CU-01).
"""

from typing import List

import pymupdf as fitz


class PdfRasterizer:
    def __init__(self, dpi: int = 200):
        # 200 dpi es un buen equilibrio entre nitidez para YOLO/pix2tex
        # y tamaño de imagen razonable; el PDF interno usa 72pt/pulgada.
        self.zoom = dpi / 72

    def num_paginas(self, pdf_path: str) -> int:
        with fitz.open(pdf_path) as doc:
            return doc.page_count

    def rasterizar(self, pdf_path: str) -> List[bytes]:
        """
        Devuelve una lista de imágenes PNG (bytes), una por página, en
        el mismo orden que el documento original. El índice de la
        lista (0-indexado) + 1 es lo que DocumentoService usará como
        número de página al guardar las fórmulas detectadas.
        """
        matriz = fitz.Matrix(self.zoom, self.zoom)
        imagenes = []

        with fitz.open(pdf_path) as doc:
            for pagina in doc:
                pixmap = pagina.get_pixmap(matrix=matriz)
                imagenes.append(pixmap.tobytes("png"))

        return imagenes

    def rasterizar_pagina(self, pdf_path: str, numero_pagina: int) -> bytes:
        """
        Rasteriza una única página (1-indexada), en vez de todo el PDF.
        Lo usa FormulaService para recortar una fórmula concreta (CU-03)
        sin tener que re-rasterizar el documento completo cada vez.
        """
        matriz = fitz.Matrix(self.zoom, self.zoom)
        with fitz.open(pdf_path) as doc:
            pagina = doc[numero_pagina - 1]
            pixmap = pagina.get_pixmap(matrix=matriz)
            return pixmap.tobytes("png")