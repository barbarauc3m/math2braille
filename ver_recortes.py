"""
Script auxiliar (fuera del repositorio) para depurar la calidad del OCR.

Reproduce EXACTAMENTE la misma lógica de recorte que usa
FormulaService._recortar_formula (mismo margen, misma fuente de la
imagen de página), pero en vez de mandarlo a service/ocr, lo guarda
en disco. Así puedes ver con tus propios ojos qué le está llegando
realmente a pix2tex antes de culpar al modelo.

Uso:
    python inspeccionar_recortes.py --db data/db/math2pix.sqlite \
        --documento-id 3 --pdf ruta/al/mismo.pdf

Requiere: pip install pymupdf pillow
(no necesitas los venvs de yolo/ocr para esto, es independiente)
"""

import argparse
import os
import sqlite3

import pymupdf as fitz
from PIL import Image
import io


def rasterizar_pagina(pdf_path: str, numero_pagina: int, dpi: int) -> bytes:
    zoom = dpi / 72
    matriz = fitz.Matrix(zoom, zoom)
    with fitz.open(pdf_path) as doc:
        pagina = doc[numero_pagina - 1]
        pixmap = pagina.get_pixmap(matrix=matriz)
        return pixmap.tobytes("png")


def recortar(pagina_bytes: bytes, x: float, y: float, ancho: float, alto: float, margen: int) -> Image.Image:
    imagen = Image.open(io.BytesIO(pagina_bytes)).convert("RGB")
    x1 = max(x - margen, 0)
    y1 = max(y - margen, 0)
    x2 = min(x + ancho + margen, imagen.width)
    y2 = min(y + alto + margen, imagen.height)
    return imagen.crop((x1, y1, x2, y2))


def main():
    parser = argparse.ArgumentParser(description="Guarda en disco los recortes exactos que recibiría service/ocr")
    parser.add_argument("--db", required=True, help="Ruta a la base de datos sqlite")
    parser.add_argument("--documento-id", type=int, required=True)
    parser.add_argument("--pdf", required=True, help="Ruta al PDF original (el mismo que se subió)")
    parser.add_argument("--dpi", type=int, default=200, help="DPI usado al rasterizar (debe coincidir con PdfRasterizer)")
    parser.add_argument("--margen", type=int, default=10, help="BBOX_MARGIN_PX usado en el backend")
    args = parser.parse_args()

    os.makedirs("results/recortes", exist_ok=True)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    formulas = conn.execute(
        "SELECT id, pagina, x, y, ancho, alto, confidence_score, mathml FROM formula WHERE documento_id = ? ORDER BY pagina, id",
        (args.documento_id,),
    ).fetchall()

    if not formulas:
        print(f"No hay fórmulas para el documento {args.documento_id}")
        return

    print(f"{len(formulas)} fórmulas encontradas. Guardando recortes en results/recortes/ ...")

    paginas_cache = {}
    for f in formulas:
        if f["pagina"] not in paginas_cache:
            paginas_cache[f["pagina"]] = rasterizar_pagina(args.pdf, f["pagina"], args.dpi)

        recorte = recortar(paginas_cache[f["pagina"]], f["x"], f["y"], f["ancho"], f["alto"], args.margen)

        procesada = "SI" if f["mathml"] else "NO"
        nombre = f"id{f['id']:04d}_pag{f['pagina']}_conf{f['confidence_score']:.2f}_procesada{procesada}.png"
        recorte.save(os.path.join("results/recortes", nombre))

    print("Listo. Revisa results/recortes/ — el nombre de cada fichero incluye el id, la página, "
          "la confianza de detección y si ya tiene mathml guardado.")


if __name__ == "__main__":
    main()