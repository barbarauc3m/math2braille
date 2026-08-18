from utils.pdf_rasterizer import PdfRasterizer

rasterizer = PdfRasterizer(dpi=200)
print("Páginas:", rasterizer.num_paginas("ejercicios-resueltos.pdf"))

imagenes = rasterizer.rasterizar("ejercicios-resueltos.pdf")
with open("pagina_1.png", "wb") as f:
    f.write(imagenes[0])