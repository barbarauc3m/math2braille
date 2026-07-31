"""
Conversión de LaTeX a MathML (RF-06).

El LaTeX que devuelve pix2tex es un formato transitorio: nunca se
persiste en SQLite. Este conversor produce el MathML que sí se guarda
en formula.mathml (FormulaRepository.actualizar_mathml), y que es lo
que consume el frontend dentro del elemento <math> del panel lateral
(RF-09).
"""

import latex2mathml.converter


class MathmlConversionError(Exception):
    pass


class MathmlConverter:
    def convertir(self, latex: str) -> str:
        try:
            return latex2mathml.converter.convert(latex)
        except Exception as e:
            # latex2mathml no define una jerarquía de excepciones propia
            # y estable entre versiones; se homogeneiza aquí para que el
            # resto del backend solo tenga que capturar un único tipo.
            raise MathmlConversionError(f"No se pudo convertir a MathML: {e}") from e