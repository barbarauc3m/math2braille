import os
from unittest.mock import MagicMock

import pytest

from adapters.yolo_client import DetectedBox
from models.documento import Documento
from models.formula import Formula
from services.documento_service import DocumentoService
from services.exceptions import DocumentoNoEncontradoError


def _service(tmp_path, **overrides):
    kwargs = dict(
        documento_repository=MagicMock(),
        formula_repository=MagicMock(),
        pdf_rasterizer=MagicMock(),
        yolo_client=MagicMock(),
        uploads_path=str(tmp_path / "uploads"),
    )
    kwargs.update(overrides)
    return DocumentoService(**kwargs)


def test_guardar_pdf_escribe_fichero_con_nombre_unico(tmp_path):
    service = _service(tmp_path)
    ruta = service._guardar_pdf(b"contenido", "apuntes.pdf")

    assert os.path.exists(ruta)
    assert ruta.endswith("_apuntes.pdf")
    with open(ruta, "rb") as f:
        assert f.read() == b"contenido"


def test_cargar_documento_flujo_completo(tmp_path):
    documento_repository = MagicMock()
    formula_repository = MagicMock()
    pdf_rasterizer = MagicMock()
    yolo_client = MagicMock()

    documento_creado = Documento(
        id=1, nombre_archivo="apuntes.pdf", ruta_archivo="/x", num_paginas=2
    )
    documento_repository.crear.return_value = documento_creado
    pdf_rasterizer.num_paginas.return_value = 2
    pdf_rasterizer.rasterizar.return_value = [b"pagina1", b"pagina2"]
    yolo_client.detectar.side_effect = [
        [DetectedBox(x=1, y=2, ancho=3, alto=4, confidence_score=0.9)],
        [],
    ]

    service = _service(
        tmp_path,
        documento_repository=documento_repository,
        formula_repository=formula_repository,
        pdf_rasterizer=pdf_rasterizer,
        yolo_client=yolo_client,
    )

    progresos = []
    documento = service.cargar_documento(
        b"pdfbytes", "apuntes.pdf", on_progreso=lambda p, t: progresos.append((p, t))
    )

    assert documento is documento_creado
    assert progresos == [(1, 2), (2, 2)]

    formulas_guardadas = formula_repository.guardar_lote.call_args[0][1]
    assert len(formulas_guardadas) == 1
    assert formulas_guardadas[0].pagina == 1
    assert formulas_guardadas[0].documento_id == 1


def test_cargar_documento_sin_callback_de_progreso(tmp_path):
    documento_repository = MagicMock()
    pdf_rasterizer = MagicMock()
    yolo_client = MagicMock()

    documento_repository.crear.return_value = Documento(
        id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1
    )
    pdf_rasterizer.num_paginas.return_value = 1
    pdf_rasterizer.rasterizar.return_value = [b"pagina1"]
    yolo_client.detectar.return_value = []

    service = _service(
        tmp_path,
        documento_repository=documento_repository,
        pdf_rasterizer=pdf_rasterizer,
        yolo_client=yolo_client,
    )

    documento = service.cargar_documento(b"pdfbytes", "a.pdf")
    assert documento.id == 1


def test_listar_historial_delega_en_repositorio(tmp_path):
    documento_repository = MagicMock()
    documento_repository.listar_historial.return_value = ["doc1", "doc2"]
    service = _service(tmp_path, documento_repository=documento_repository)

    assert service.listar_historial() == ["doc1", "doc2"]


def test_abrir_documento_existente(tmp_path):
    documento_repository = MagicMock()
    documento = Documento(id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1)
    documento_repository.obtener_por_id.return_value = documento
    service = _service(tmp_path, documento_repository=documento_repository)

    resultado = service.abrir_documento(1)

    assert resultado is documento
    documento_repository.actualizar_fecha_apertura.assert_called_once_with(1)


def test_abrir_documento_inexistente(tmp_path):
    documento_repository = MagicMock()
    documento_repository.obtener_por_id.return_value = None
    service = _service(tmp_path, documento_repository=documento_repository)

    with pytest.raises(DocumentoNoEncontradoError):
        service.abrir_documento(999)


def test_eliminar_documento_existente(tmp_path):
    documento_repository = MagicMock()
    documento_repository.obtener_por_id.return_value = Documento(
        id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1
    )
    service = _service(tmp_path, documento_repository=documento_repository)

    service.eliminar_documento(1)

    documento_repository.eliminar.assert_called_once_with(1)


def test_eliminar_documento_inexistente(tmp_path):
    documento_repository = MagicMock()
    documento_repository.obtener_por_id.return_value = None
    service = _service(tmp_path, documento_repository=documento_repository)

    with pytest.raises(DocumentoNoEncontradoError):
        service.eliminar_documento(999)
    documento_repository.eliminar.assert_not_called()


def test_obtener_contenido_pagina_documento_inexistente(tmp_path):
    documento_repository = MagicMock()
    documento_repository.obtener_por_id.return_value = None
    service = _service(tmp_path, documento_repository=documento_repository)

    with pytest.raises(DocumentoNoEncontradoError):
        service.obtener_contenido_pagina(999, 1)


def test_obtener_contenido_pagina_ordena_texto_y_formulas(tmp_path):
    documento_repository = MagicMock()
    formula_repository = MagicMock()
    pdf_rasterizer = MagicMock()

    documento = Documento(id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1)
    documento_repository.obtener_por_id.return_value = documento
    pdf_rasterizer.zoom = 2.0

    formula_pagina1 = Formula(
        id=10, documento_id=1, pagina=1, x=20, y=20, ancho=10, alto=10, confidence_score=0.9
    )
    formula_pagina2 = Formula(
        id=11, documento_id=1, pagina=2, x=0, y=0, ancho=1, alto=1, confidence_score=0.9
    )
    formula_repository.obtener_por_documento.return_value = [formula_pagina1, formula_pagina2]

    pdf_rasterizer.extraer_bloques_texto.return_value = [
        {"texto": "arriba", "x": 0.0, "y": 0.0},
        {"texto": "abajo", "x": 0.0, "y": 100.0},
    ]

    service = _service(
        tmp_path,
        documento_repository=documento_repository,
        formula_repository=formula_repository,
        pdf_rasterizer=pdf_rasterizer,
    )

    elementos = service.obtener_contenido_pagina(1, 1)

    # Solo debe incluir la fórmula de la página 1, y quedar ordenado por y.
    tipos_y_orden = [(e["tipo"], e["y"]) for e in elementos]
    assert tipos_y_orden == [
        ("texto", 0.0),
        ("formula", 10.0),
        ("texto", 100.0),
    ]

    # Verificamos que se pasan las cajas convertidas a puntos PDF (zoom=2).
    llamada = pdf_rasterizer.extraer_bloques_texto.call_args
    assert llamada.kwargs["cajas_a_ignorar"] == [(10.0, 10.0, 15.0, 15.0)]


def test_load_documento_service(monkeypatch, tmp_path):
    from services.documento_service import load_documento_service

    monkeypatch.setenv("UPLOADS_PATH", str(tmp_path / "uploads"))
    service = load_documento_service()

    assert isinstance(service, DocumentoService)
    assert service.uploads_path == str(tmp_path / "uploads")
