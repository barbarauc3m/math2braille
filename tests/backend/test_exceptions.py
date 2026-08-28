import pytest

from services.exceptions import (
    DocumentoNoEncontradoError,
    FormulaNoEncontradaError,
    ProcesamientoFormulaError,
)


@pytest.mark.parametrize(
    "excepcion",
    [DocumentoNoEncontradoError, FormulaNoEncontradaError, ProcesamientoFormulaError],
)
def test_exceptions_son_excepciones_con_mensaje(excepcion):
    with pytest.raises(excepcion, match="detalle"):
        raise excepcion("detalle")
