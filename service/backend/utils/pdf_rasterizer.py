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
import re
import unicodedata
import pymupdf as fitz


# Algunas fuentes LaTeX generan el acento como un glifo independiente colocado ANTES de la vocal, en vez de como carácter Unicode precompuesto.
# PyMuPDF extrae los glifos en ese mismo orden erróneo.
# Se corrige recomponiendo cada par acento+vocal detectado por vocal actencuada.

_MAPA_ACENTOS_INVERTIDOS = {
    "´a": "á", "´e": "é", "´i": "í", "´o": "ó", "´u": "ú",
    "´A": "Á", "´E": "É", "´I": "Í", "´O": "Ó", "´U": "Ú",
    "¨u": "ü", "¨U": "Ü",
    "~n": "ñ", "~N": "Ñ",
}


def _corregir_acentos(texto: str) -> str:
    for patron, combinado in _MAPA_ACENTOS_INVERTIDOS.items():
        texto = texto.replace(patron, combinado)

    # Por si en algún PDF el acento sí llega como marca Unicode combinante pero en el orden correcto, esto la recompone en un solo carácter precompuesto (NFC).
    texto = unicodedata.normalize("NFC", texto)

    # Cualquier símbolo de acento que sobreviva sin una vocal detrásim se elimina ina como último recurso, en vez de dejarlo suelto en medio de una palabra.
    texto = re.sub(r"[´¨~](?![aeiouAEIOU])", "", texto)

    return texto

class PdfRasterizer:
    def __init__(self, dpi: int = 200):
        # 200 dpi es un buen equilibrio entre nitidez para YOLO/pix2tex y tamaño de imagen razonable; el PDF interno usa 72pt/pulgada.
        self.zoom = dpi / 72

    def num_paginas(self, pdf_path: str) -> int:
        with fitz.open(pdf_path) as doc:
            return doc.page_count

    def rasterizar(self, pdf_path: str) -> List[bytes]:
        """
        Devuelve una lista de imágenes PNG (bytes), una por página, en el mismo orden que el documento original. El índice de la lista (0-indexado) + 1 es lo que DocumentoService usará como número de página al guardar las fórmulas detectadas.
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
        Lo usa FormulaService para recortar una fórmula concreta sin tener que re-rasterizar el documento completo cada vez.
        """
        matriz = fitz.Matrix(self.zoom, self.zoom)
        with fitz.open(pdf_path) as doc:
            pagina = doc[numero_pagina - 1]
            pixmap = pagina.get_pixmap(matrix=matriz)
            return pixmap.tobytes("png")
        
    def extraer_bloques_texto(self, pdf_path: str, numero_pagina: int) -> list[dict]:
        """
        Extrae los bloques de texto ya embebidos en el PDF, sin necesidad de OCR general: PyMuPDF los lee directamente porque el PDF los contiene como texto real, no como píxeles. Solo es fiable para PDFs exportados de documentos digitales (Word, Power Point, etc)
        """
        with fitz.open(pdf_path) as doc:
            pagina = doc[numero_pagina - 1]
            bloques_raw = pagina.get_text("blocks")

        bloques = []
        for x0, y0, x1, y1, texto, _bloque_no, tipo_bloque in bloques_raw:
            texto_limpio = _corregir_acentos(texto.strip())
            if tipo_bloque == 0 and texto_limpio:  # tipo 0 = bloque de texto (no imagen)
                bloques.append({"texto": texto_limpio, "x": x0, "y": y0})

        return bloques