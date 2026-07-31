"""
Validación sintáctica de fragmentos XHTML+MathML (RF-11, RNF-06).

Se invoca en dos momentos: tras MathmlConverter (para no persistir un
MathML corrupto en formula.mathml), y de nuevo cuando el usuario edita
manualmente una fórmula desde el panel lateral, antes de guardar
(RF-12) — en ese segundo caso, un fallo de validación es lo que
dispara la notificación accesible de error (RF-20, aria-live="assertive").
"""

from lxml import etree


class XhtmlValidationError(Exception):
    pass


class XhtmlValidator:
    def validar_fragmento_mathml(self, mathml_fragment: str) -> None:
        """
        No devuelve nada: si el fragmento es válido, simplemente no
        lanza excepción. Comprueba dos cosas:
          1. Que sea XML bien formado.
          2. Que el elemento raíz sea <math> (espacio de nombres MathML).
        """
        try:
            root = etree.fromstring(mathml_fragment.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            raise XhtmlValidationError(f"XML mal formado: {e}") from e

        tag_local = etree.QName(root).localname
        if tag_local != "math":
            raise XhtmlValidationError(
                f"Se esperaba un elemento raíz <math>, se encontró <{tag_local}>"
            )