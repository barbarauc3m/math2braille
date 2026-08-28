from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from dependencies import get_formula_service
from models.formula import Formula
from services.exceptions import FormulaNoEncontradaError, ProcesamientoFormulaError
from utils.xhtml_validator import XhtmlValidationError


@pytest.fixture
def client_and_mock():
    import main

    formula_service = MagicMock()
    main.app.dependency_overrides[get_formula_service] = lambda: formula_service

    yield TestClient(main.app), formula_service

    main.app.dependency_overrides.clear()


def _formula(**overrides):
    base = dict(id=1, documento_id=1, pagina=1, x=0, y=0, ancho=1, alto=1, confidence_score=0.9)
    base.update(overrides)
    return Formula(**base)


def test_consultar_formula_200(client_and_mock):
    client, formula_service = client_and_mock
    formula_service.consultar_formula.return_value = _formula(mathml="<math/>")

    response = client.get("/formulas/1")

    assert response.status_code == 200
    assert response.json()["mathml"] == "<math/>"


def test_consultar_formula_404(client_and_mock):
    client, formula_service = client_and_mock
    formula_service.consultar_formula.side_effect = FormulaNoEncontradaError("no existe")

    response = client.get("/formulas/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "no existe"


def test_consultar_formula_502_en_fallo_de_procesamiento(client_and_mock):
    client, formula_service = client_and_mock
    formula_service.consultar_formula.side_effect = ProcesamientoFormulaError("fallo ocr")

    response = client.get("/formulas/1")

    assert response.status_code == 502
    assert response.json()["detail"] == "fallo ocr"


def test_editar_formula_200(client_and_mock):
    client, formula_service = client_and_mock
    formula_service.editar_formula.return_value = _formula(mathml="<math><mi>x</mi></math>")

    response = client.put("/formulas/1", json={"mathml": "<math><mi>x</mi></math>"})

    assert response.status_code == 200
    assert response.json()["mathml"] == "<math><mi>x</mi></math>"
    formula_service.editar_formula.assert_called_once_with(1, "<math><mi>x</mi></math>")


def test_editar_formula_404(client_and_mock):
    client, formula_service = client_and_mock
    formula_service.editar_formula.side_effect = FormulaNoEncontradaError("no existe")

    response = client.put("/formulas/999", json={"mathml": "<math/>"})

    assert response.status_code == 404


def test_editar_formula_400_si_invalida(client_and_mock):
    client, formula_service = client_and_mock
    formula_service.editar_formula.side_effect = XhtmlValidationError("mal formado")

    response = client.put("/formulas/1", json={"mathml": "<div>no es math</div>"})

    assert response.status_code == 400
    assert response.json()["detail"] == "mal formado"
