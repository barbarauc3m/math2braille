"""
Excepciones de la capa de negocio.

Los controllers capturas las excepciones para traducirlas a respuestas
HTTP con mensajes accesibles y detallados (RF-20): cada tipo de error necesita un
código de estado y un mensaje no genérico (no un simple "ha ocurrido un error").
"""


class DocumentoNoEncontradoError(Exception):
    pass


class FormulaNoEncontradaError(Exception):
    pass


class ProcesamientoFormulaError(Exception):
    """Envuelve fallos de OCR o de conversión LaTeX->MathML (RF-05, RF-06)."""
    pass