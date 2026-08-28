import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from dependencies import get_documento_service, get_formula_service
from models.documento import Documento
from models.formula import Formula
from services.exceptions import DocumentoNoEncontradoError


@pytest.fixture
def client_and_mocks():
    import main

    documento_service = MagicMock()
    formula_service = MagicMock()
    main.app.dependency_overrides[get_documento_service] = lambda: documento_service
    main.app.dependency_overrides[get_formula_service] = lambda: formula_service

    yield TestClient(main.app), documento_service, formula_service

    main.app.dependency_overrides.clear()


def _parse_ndjson(texto):
    return [json.loads(linea) for linea in texto.strip().split("\n") if linea]


def test_subir_documento_pdf_valido(client_and_mocks):
    client, documento_service, _ = client_and_mocks
    documento_creado = Documento(
        id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=2,
        fecha_carga="2024-01-01", fecha_ultima_apertura="2024-01-01",
    )

    def _cargar_documento(pdf_bytes, nombre_archivo, on_progreso=None):
        on_progreso(1, 2)
        on_progreso(2, 2)
        return documento_creado

    documento_service.cargar_documento.side_effect = _cargar_documento

    response = client.post(
        "/documentos", files={"file": ("a.pdf", b"%PDF-1.4 contenido", "application/pdf")}
    )

    assert response.status_code == 200
    eventos = _parse_ndjson(response.text)
    assert eventos[0] == {"tipo": "progreso", "pagina": 1, "total": 2}
    assert eventos[1] == {"tipo": "progreso", "pagina": 2, "total": 2}
    assert eventos[2]["tipo"] == "completado"
    assert eventos[2]["documento"]["id"] == 1


def test_subir_documento_content_type_invalido(client_and_mocks):
    client, _, _ = client_and_mocks
    response = client.post(
        "/documentos", files={"file": ("a.txt", b"hola", "text/plain")}
    )
    assert response.status_code == 400


def test_subir_documento_vacio(client_and_mocks):
    client, _, _ = client_and_mocks
    response = client.post(
        "/documentos", files={"file": ("a.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400


def test_subir_documento_error_en_servicio(client_and_mocks):
    client, documento_service, _ = client_and_mocks
    documento_service.cargar_documento.side_effect = RuntimeError("fallo yolo")

    response = client.post(
        "/documentos", files={"file": ("a.pdf", b"contenido", "application/pdf")}
    )

    eventos = _parse_ndjson(response.text)
    assert eventos[-1] == {"tipo": "error", "detalle": "fallo yolo"}


def test_listar_historial(client_and_mocks):
    client, documento_service, _ = client_and_mocks
    documento_service.listar_historial.return_value = [
        Documento(
            id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1,
            fecha_carga="2024-01-01", fecha_ultima_apertura="2024-01-01",
        )
    ]

    response = client.get("/documentos")

    assert response.status_code == 200
    assert response.json() == {
        "documentos": [
            {
                "id": 1, "nombre_archivo": "a.pdf", "num_paginas": 1,
                "fecha_carga": "2024-01-01", "fecha_ultima_apertura": "2024-01-01",
            }
        ]
    }


def test_abrir_documento_200(client_and_mocks):
    client, documento_service, _ = client_and_mocks
    documento_service.abrir_documento.return_value = Documento(
        id=1, nombre_archivo="a.pdf", ruta_archivo="/x", num_paginas=1,
        fecha_carga="2024-01-01", fecha_ultima_apertura="2024-01-01",
    )

    response = client.get("/documentos/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_abrir_documento_404(client_and_mocks):
    client, documento_service, _ = client_and_mocks
    documento_service.abrir_documento.side_effect = DocumentoNoEncontradoError("no existe")

    response = client.get("/documentos/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "no existe"


def test_obtener_formulas(client_and_mocks):
    client, _, formula_service = client_and_mocks
    formula_service.obtener_formulas_documento.return_value = [
        Formula(id=1, documento_id=1, pagina=1, x=0, y=0, ancho=1, alto=1, confidence_score=0.9)
    ]

    response = client.get("/documentos/1/formulas")

    assert response.status_code == 200
    assert response.json()["formulas"][0]["id"] == 1


def test_eliminar_documento_204(client_and_mocks):
    client, documento_service, _ = client_and_mocks

    response = client.delete("/documentos/1")

    assert response.status_code == 204
    documento_service.eliminar_documento.assert_called_once_with(1)


def test_eliminar_documento_404(client_and_mocks):
    client, documento_service, _ = client_and_mocks
    documento_service.eliminar_documento.side_effect = DocumentoNoEncontradoError("no existe")

    response = client.delete("/documentos/999")

    assert response.status_code == 404


def test_obtener_contenido_pagina_200(client_and_mocks):
    client, documento_service, _ = client_and_mocks
    documento_service.obtener_contenido_pagina.return_value = [
        {"tipo": "texto", "texto": "hola", "x": 0.0, "y": 0.0},
        {
            "tipo": "formula",
            "x": 0.0, "y": 0.0,
            "formula": Formula(
                id=1, documento_id=1, pagina=1, x=0, y=0, ancho=1, alto=1, confidence_score=0.9
            ),
        },
    ]

    response = client.get("/documentos/1/paginas/1/contenido")

    assert response.status_code == 200
    elementos = response.json()["elementos"]
    assert elementos[0] == {"tipo": "texto", "texto": "hola"}
    assert elementos[1]["tipo"] == "formula"
    assert elementos[1]["formula"]["id"] == 1


def test_obtener_contenido_pagina_404(client_and_mocks):
    client, documento_service, _ = client_and_mocks
    documento_service.obtener_contenido_pagina.side_effect = DocumentoNoEncontradoError("no existe")

    response = client.get("/documentos/999/paginas/1/contenido")

    assert response.status_code == 404


def test_procesar_formulas_pagina_streaming(client_and_mocks):
    client, _, formula_service = client_and_mocks

    formula_procesada = Formula(
        id=1, documento_id=1, pagina=1, x=0, y=0, ancho=1, alto=1,
        confidence_score=0.9, mathml="<math/>",
    )

    def _procesar(documento_id, numero_pagina, on_progreso=None, on_error_formula=None):
        on_error_formula(2, "fallo ocr")
        on_progreso(1, 1, formula_procesada)
        return [formula_procesada]

    formula_service.procesar_formulas_pagina.side_effect = _procesar

    response = client.post("/documentos/1/paginas/1/procesar")

    eventos = _parse_ndjson(response.text)
    assert eventos[0] == {"tipo": "error_formula", "formula_id": 2, "detalle": "fallo ocr"}
    assert eventos[1]["tipo"] == "progreso"
    assert eventos[1]["formula"]["id"] == 1
    assert eventos[2] == {"tipo": "completado"}


def test_procesar_formulas_pagina_documento_inexistente(client_and_mocks):
    client, _, formula_service = client_and_mocks
    formula_service.procesar_formulas_pagina.side_effect = DocumentoNoEncontradoError("no existe")

    response = client.post("/documentos/999/paginas/1/procesar")

    eventos = _parse_ndjson(response.text)
    assert eventos[-1] == {"tipo": "error", "detalle": "no existe"}
