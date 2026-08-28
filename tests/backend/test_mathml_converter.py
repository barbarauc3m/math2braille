import pytest

from utils.mathml_converter import MathmlConversionError, MathmlConverter


def test_convertir_latex_valido():
    converter = MathmlConverter()
    mathml = converter.convertir("x+1")
    assert "<math" in mathml


def test_convertir_error_se_homogeneiza(monkeypatch):
    import latex2mathml.converter as real_converter

    def _boom(_latex):
        raise ValueError("latex invalido")

    monkeypatch.setattr(real_converter, "convert", _boom)

    converter = MathmlConverter()
    with pytest.raises(MathmlConversionError, match="No se pudo convertir a MathML"):
        converter.convertir("\\bad{")
