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
        
    def extraer_bloques_texto(
        self,
        pdf_path: str,
        numero_pagina: int,
        cajas_a_ignorar: "list[tuple[float, float, float, float]] | None" = None,
        factor_encogimiento: float = 1,
    ) -> list[dict]:
        """
        Extrae los bloques de texto ya embebidos en el PDF, sin necesidad de OCR general: PyMuPDF los lee directamente porque el PDF los contiene como texto real, no como píxeles. Solo es fiable para PDFs exportados de documentos digitales (Word, Power Point, etc)

        `cajas_a_ignorar` son rectángulos (x0, y0, x1, y1) en puntos PDF —
        normalmente las cajas de fórmula ya detectadas por YOLO— cuyo
        contenido se **redacta** (se borra del propio content stream de la
        página, no solo visualmente) antes de llamar a get_text(). Esto
        evita que una fórmula, al ser texto real embebido en el PDF, se
        lea dos veces: una aquí como texto plano y otra ya traducida por
        service/ocr. Filtrar a posteriori por solapamiento de bbox no es
        fiable porque PyMuPDF puede trocear una misma fórmula en varios
        bloques pequeños (p.ej. los límites de una integral quedan en un
        bloque aparte, por encima/debajo del cuerpo) o fundirla con texto
        vecino en un bloque más grande; redactar antes de extraer elimina
        el problema de raíz en vez de intentar adivinarlo después.

        `factor_encogimiento` reduce cada caja hacia su centro antes de
        redactar (0.8 = se conserva el 80% del ancho y el alto). Las cajas
        de YOLO suelen venir más holgadas que el contenido real de la
        fórmula, y `apply_redactions()` borra carácter a carácter, no
        bloque a bloque: si la caja se pasa de la fórmula e invade el
        bloque de texto vecino (p.ej. la descripción "a) Derivada de..."
        justo encima), ese bloque queda truncado a medias, con un bbox que
        ya no refleja su posición real de lectura — lo que además
        descoloca el orden en obtener_contenido_pagina. Es preferible
        encoger de más y dejar algún glifo suelto de la propia fórmula
        (irrelevante, porque esa región ya se sustituye por su traducción
        MathML) que invadir texto ajeno.

        Como el documento se abre y se descarta dentro de este método sin
        llamar a doc.save(), la redacción es puramente en memoria: el PDF
        original en disco no se modifica.
        """
        with fitz.open(pdf_path) as doc:
            pagina = doc[numero_pagina - 1]

            if cajas_a_ignorar:
                for x0, y0, x1, y1 in cajas_a_ignorar:
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    semiancho = (x1 - x0) / 2 * factor_encogimiento
                    semialto = (y1 - y0) / 2 * factor_encogimiento
                    rect = fitz.Rect(
                        cx - semiancho, cy - semialto,
                        cx + semiancho, cy + semialto,
                    )
                    pagina.add_redact_annot(rect)
                pagina.apply_redactions()

            bloques_raw = pagina.get_text("blocks")

        bloques = []
        for x0, y0, x1, y1, texto, _bloque_no, tipo_bloque in bloques_raw:
            texto_limpio = _corregir_acentos(texto.strip())
            if tipo_bloque == 0 and texto_limpio:  # tipo 0 = bloque de texto (no imagen)
                bloques.append({"texto": texto_limpio, "x": x0, "y": y0, "x1": x1, "y1": y1})

        return bloques