import io
from unittest.mock import MagicMock

import pytest
from PIL import Image

from models.documento import Documento
from models.formula import Formula
from services.exceptions import DocumentoNoEncontradoError, FormulaNoEncontradaError, ProcesamientoFormulaError
from services.formula_service import FormulaService
from utils.mathml_converter import MathmlConversionError
from utils.xhtml_validator import XhtmlValidationError


def _png_bytes(width=100, height=100):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def _service(**overrides):
    kwargs = dict(
        formula_repository=MagicMock(),
        documento_repository=MagicMock(),
        pdf_rasterizer=MagicMock(),
        ocr_client=MagicMock(),
        mathml_converter=MagicMock(),
        xhtml_validator=MagicMock(),
        bbox_margin_px=10,
    )
    kwargs.update(overrides)
    return FormulaService(**kwargs)


def _formula(**overrides):
    base = dict(
        id=1, documento_id=1, pagina=1, x=20, y=20, ancho=10, alto=10, confidence_score=0.9
    )
    base.update(overrides)
    return Formula(**base)


def test_recortar_formula_respeta_margen_y_limites():
    service = _service()
    pagina_bytes = _png_bytes(width=100, height=100)
    formula = _formula(x=95, y=95, ancho=10, alto=10)  # se sale del borde inferior/derecho

    recorte_bytes = service._recortar_formula(pagina_bytes, formula)
    recorte = Image.open(io.BytesIO(recorte_bytes))

    # x2/y2 deben quedar limitados al tamaño de la imagen (100x100).
    assert recorte.width == 100 - max(95 - 10, 0)
    assert recorte.height == 100 - max(95 - 10, 0)


def test_consultar_formula_devuelve_cache_si_ya_procesada():
    formula_repository = MagicMock()
    formula_cacheada = _formula(mathml="<math/>")
    formula_repository.obtener_por_id.return_value = formula_cacheada

    service = _service(formula_repository=formula_repository)
    resultado = service.consultar_formula(1)

    assert resultado is formula_cacheada
    service.ocr_client.reconocer.assert_not_called()


def test_consultar_formula_inexistente():
    formula_repository = MagicMock()
    formula_repository.obtener_por_id.return_value = None
    service = _service(formula_repository=formula_repository)

    with pytest.raises(FormulaNoEncontradaError):
        service.consultar_formula(999)


def test_consultar_formula_dispara_pipeline_completo():
    formula_repository = MagicMock()
    documento_repository = MagicMock()
    pdf_rasterizer = MagicMock()
    ocr_client = MagicMock()
    mathml_converter = MagicMock()
    xhtml_validator = MagicMock()

    formula_sin_procesar = _formula()
    formula_repository.obtener_por_id.return_value = formula_sin_procesar
    documento_repository.obtener_por_id.return_value = Documento(
        id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1
    )
    pdf_rasterizer.rasterizar_pagina.return_value = _png_bytes()
    ocr_client.reconocer.return_value = "x^2"
    mathml_converter.convertir.return_value = "<math><mn>x^2</mn></math>"
    formula_actualizada = _formula(mathml="<math><mn>x^2</mn></math>")
    formula_repository.actualizar_mathml.return_value = formula_actualizada

    service = _service(
        formula_repository=formula_repository,
        documento_repository=documento_repository,
        pdf_rasterizer=pdf_rasterizer,
        ocr_client=ocr_client,
        mathml_converter=mathml_converter,
        xhtml_validator=xhtml_validator,
    )

    resultado = service.consultar_formula(1)

    assert resultado is formula_actualizada
    ocr_client.reconocer.assert_called_once()
    mathml_converter.convertir.assert_called_once_with("x^2")
    xhtml_validator.validar_fragmento_mathml.assert_called_once_with("<math><mn>x^2</mn></math>")
    formula_repository.actualizar_mathml.assert_called_once_with(1, "<math><mn>x^2</mn></math>")


def test_procesar_formula_documento_inexistente():
    formula_repository = MagicMock()
    documento_repository = MagicMock()
    formula_repository.obtener_por_id.return_value = _formula()
    documento_repository.obtener_por_id.return_value = None

    service = _service(formula_repository=formula_repository, documento_repository=documento_repository)

    with pytest.raises(FormulaNoEncontradaError):
        service.consultar_formula(1)


def test_procesar_formula_error_conversion_mathml():
    formula_repository = MagicMock()
    documento_repository = MagicMock()
    pdf_rasterizer = MagicMock()
    ocr_client = MagicMock()
    mathml_converter = MagicMock()

    formula_repository.obtener_por_id.return_value = _formula()
    documento_repository.obtener_por_id.return_value = Documento(
        id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1
    )
    pdf_rasterizer.rasterizar_pagina.return_value = _png_bytes()
    ocr_client.reconocer.return_value = "\\bad"
    mathml_converter.convertir.side_effect = MathmlConversionError("latex invalido")

    service = _service(
        formula_repository=formula_repository,
        documento_repository=documento_repository,
        pdf_rasterizer=pdf_rasterizer,
        ocr_client=ocr_client,
        mathml_converter=mathml_converter,
    )

    with pytest.raises(ProcesamientoFormulaError):
        service.consultar_formula(1)


def test_procesar_formula_error_validacion_xhtml():
    formula_repository = MagicMock()
    documento_repository = MagicMock()
    pdf_rasterizer = MagicMock()
    ocr_client = MagicMock()
    mathml_converter = MagicMock()
    xhtml_validator = MagicMock()

    formula_repository.obtener_por_id.return_value = _formula()
    documento_repository.obtener_por_id.return_value = Documento(
        id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1
    )
    pdf_rasterizer.rasterizar_pagina.return_value = _png_bytes()
    ocr_client.reconocer.return_value = "x"
    mathml_converter.convertir.return_value = "<div>no es math</div>"
    xhtml_validator.validar_fragmento_mathml.side_effect = XhtmlValidationError("raiz invalida")

    service = _service(
        formula_repository=formula_repository,
        documento_repository=documento_repository,
        pdf_rasterizer=pdf_rasterizer,
        ocr_client=ocr_client,
        mathml_converter=mathml_converter,
        xhtml_validator=xhtml_validator,
    )

    with pytest.raises(ProcesamientoFormulaError, match="MathML generado inválido"):
        service.consultar_formula(1)


def test_editar_formula_valida_y_persiste():
    formula_repository = MagicMock()
    xhtml_validator = MagicMock()
    formula_repository.obtener_por_id.return_value = _formula()
    formula_repository.actualizar_mathml.return_value = _formula(mathml="<math/>")

    service = _service(formula_repository=formula_repository, xhtml_validator=xhtml_validator)

    resultado = service.editar_formula(1, "<math/>")

    xhtml_validator.validar_fragmento_mathml.assert_called_once_with("<math/>")
    formula_repository.actualizar_mathml.assert_called_once_with(1, "<math/>")
    assert resultado.mathml == "<math/>"


def test_editar_formula_inexistente():
    formula_repository = MagicMock()
    formula_repository.obtener_por_id.return_value = None
    service = _service(formula_repository=formula_repository)

    with pytest.raises(FormulaNoEncontradaError):
        service.editar_formula(999, "<math/>")


def test_editar_formula_invalida_no_persiste():
    formula_repository = MagicMock()
    xhtml_validator = MagicMock()
    formula_repository.obtener_por_id.return_value = _formula()
    xhtml_validator.validar_fragmento_mathml.side_effect = XhtmlValidationError("mal formado")

    service = _service(formula_repository=formula_repository, xhtml_validator=xhtml_validator)

    with pytest.raises(XhtmlValidationError):
        service.editar_formula(1, "<div/>")
    formula_repository.actualizar_mathml.assert_not_called()


def test_obtener_formulas_documento():
    formula_repository = MagicMock()
    formula_repository.obtener_por_documento.return_value = ["f1", "f2"]
    service = _service(formula_repository=formula_repository)

    assert service.obtener_formulas_documento(1) == ["f1", "f2"]


def test_procesar_formulas_pagina_documento_inexistente():
    documento_repository = MagicMock()
    documento_repository.obtener_por_id.return_value = None
    service = _service(documento_repository=documento_repository)

    with pytest.raises(DocumentoNoEncontradoError):
        service.procesar_formulas_pagina(999, 1)


def test_procesar_formulas_pagina_sin_pendientes():
    formula_repository = MagicMock()
    documento_repository = MagicMock()
    documento_repository.obtener_por_id.return_value = Documento(
        id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1
    )
    formula_repository.obtener_por_documento.return_value = [_formula(mathml="<math/>")]

    service = _service(formula_repository=formula_repository, documento_repository=documento_repository)

    assert service.procesar_formulas_pagina(1, 1) == []
    service.pdf_rasterizer.rasterizar_pagina.assert_not_called()


def test_procesar_formulas_pagina_una_falla_y_otra_no_interrumpe_lote():
    formula_repository = MagicMock()
    documento_repository = MagicMock()
    pdf_rasterizer = MagicMock()
    ocr_client = MagicMock()
    mathml_converter = MagicMock()
    xhtml_validator = MagicMock()

    documento_repository.obtener_por_id.return_value = Documento(
        id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1
    )
    formula_fallida = _formula(id=1)
    formula_exitosa = _formula(id=2)
    formula_ya_procesada = _formula(id=3, mathml="<math/>")
    formula_repository.obtener_por_documento.return_value = [
        formula_fallida, formula_exitosa, formula_ya_procesada
    ]
    pdf_rasterizer.rasterizar_pagina.return_value = _png_bytes()

    ocr_client.reconocer.side_effect = ["latex1", "latex2"]
    mathml_converter.convertir.side_effect = [MathmlConversionError("boom"), "<math/>"]
    formula_repository.actualizar_mathml.return_value = _formula(id=2, mathml="<math/>")

    service = _service(
        formula_repository=formula_repository,
        documento_repository=documento_repository,
        pdf_rasterizer=pdf_rasterizer,
        ocr_client=ocr_client,
        mathml_converter=mathml_converter,
        xhtml_validator=xhtml_validator,
    )

    progresos = []
    errores = []
    procesadas = service.procesar_formulas_pagina(
        1, 1,
        on_progreso=lambda i, t, f: progresos.append((i, t, f.id)),
        on_error_formula=lambda fid, detalle: errores.append((fid, detalle)),
    )

    assert len(procesadas) == 1
    assert procesadas[0].id == 2
    assert errores == [(1, "boom")]
    assert progresos == [(2, 2, 2)]
    # Solo una rasterización para toda la página, reutilizada entre fórmulas.
    pdf_rasterizer.rasterizar_pagina.assert_called_once()


def test_load_formula_service(monkeypatch):
    from services.formula_service import load_formula_service

    monkeypatch.setenv("BBOX_MARGIN_PX", "25")
    service = load_formula_service()

    assert isinstance(service, FormulaService)
    assert service.bbox_margin_px == 25
