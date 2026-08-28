import pytest

from utils.xhtml_validator import XhtmlValidationError, XhtmlValidator


def test_fragmento_valido_no_lanza():
    validator = XhtmlValidator()
    validator.validar_fragmento_mathml("<math><mi>x</mi></math>")


def test_xml_mal_formado():
    validator = XhtmlValidator()
    with pytest.raises(XhtmlValidationError, match="XML mal formado"):
        validator.validar_fragmento_mathml("<math><mi>x</mi>")


def test_raiz_distinta_de_math():
    validator = XhtmlValidator()
    with pytest.raises(XhtmlValidationError, match="se encontró <div>"):
        validator.validar_fragmento_mathml("<div>no es math</div>")


def test_raiz_math_con_namespace():
    validator = XhtmlValidator()
    validator.validar_fragmento_mathml(
        '<math xmlns="http://www.w3.org/1998/Math/MathML"><mi>x</mi></math>'
    )
