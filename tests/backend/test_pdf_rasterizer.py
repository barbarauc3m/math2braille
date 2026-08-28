import pymupdf as fitz

from utils.pdf_rasterizer import PdfRasterizer, _corregir_acentos


def _crear_pdf(tmp_path, textos):
    doc = fitz.open()
    for texto in textos:
        pagina = doc.new_page()
        pagina.insert_text((72, 100), texto)
    ruta = tmp_path / "doc.pdf"
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


def test_num_paginas(tmp_path):
    ruta = _crear_pdf(tmp_path, ["Pagina 1", "Pagina 2", "Pagina 3"])
    rasterizer = PdfRasterizer()
    assert rasterizer.num_paginas(ruta) == 3


def test_rasterizar_devuelve_una_imagen_png_por_pagina(tmp_path):
    ruta = _crear_pdf(tmp_path, ["Pagina 1", "Pagina 2"])
    rasterizer = PdfRasterizer()
    imagenes = rasterizer.rasterizar(ruta)
    assert len(imagenes) == 2
    for imagen in imagenes:
        assert imagen[:8] == b"\x89PNG\r\n\x1a\n"


def test_rasterizar_pagina_individual(tmp_path):
    ruta = _crear_pdf(tmp_path, ["Pagina 1", "Pagina 2"])
    rasterizer = PdfRasterizer()
    imagen = rasterizer.rasterizar_pagina(ruta, 2)
    assert imagen[:8] == b"\x89PNG\r\n\x1a\n"


def test_zoom_calculado_desde_dpi():
    rasterizer = PdfRasterizer(dpi=72)
    assert rasterizer.zoom == 1.0
    rasterizer_200 = PdfRasterizer(dpi=200)
    assert abs(rasterizer_200.zoom - 200 / 72) < 1e-9


def test_extraer_bloques_texto_sin_cajas_a_ignorar(tmp_path):
    ruta = _crear_pdf(tmp_path, ["Hola mundo"])
    rasterizer = PdfRasterizer()
    bloques = rasterizer.extraer_bloques_texto(ruta, 1)
    assert len(bloques) == 1
    assert "Hola mundo" in bloques[0]["texto"]
    assert set(bloques[0].keys()) == {"texto", "x", "y", "x1", "y1"}


def test_extraer_bloques_texto_redacta_cajas_a_ignorar(tmp_path):
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_text((72, 100), "Formula")
    pagina.insert_text((72, 300), "Texto normal")
    ruta = tmp_path / "doc.pdf"
    doc.save(str(ruta))
    doc.close()

    rasterizer = PdfRasterizer()
    # bbox amplio alrededor de "Formula" (72,100) en puntos PDF.
    caja = (60.0, 80.0, 200.0, 120.0)
    bloques = rasterizer.extraer_bloques_texto(str(ruta), 1, cajas_a_ignorar=[caja])

    textos = [b["texto"] for b in bloques]
    assert not any("Formula" in t for t in textos)
    assert any("Texto normal" in t for t in textos)


def test_corregir_acentos_invertidos():
    assert _corregir_acentos("nu´ador") == "nuádor"
    assert _corregir_acentos("Espan~na") == "Espanña"
    assert _corregir_acentos("¨uber") == "über"


def test_corregir_acentos_nfc_normalization():
    # 'a' + combining acute accent (U+0301) -> 'á' precompuesto tras NFC.
    texto = "á"
    assert _corregir_acentos(texto) == "á"


def test_corregir_acentos_elimina_simbolo_suelto():
    assert _corregir_acentos("100´") == "100"
