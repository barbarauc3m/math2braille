"""
Inyección de dependencias de FastAPI para los servicios de negocio.

Los servicios se instancian una única vez al arrancar el proceso. Centralizarlo aquí
permite además sobrescribir estas dependencias en tests con
app.dependency_overrides, sin tocar los controllers.
"""

from services.documento_service import DocumentoService, load_documento_service
from services.formula_service import FormulaService, load_formula_service

_documento_service = load_documento_service()
_formula_service = load_formula_service()


def get_documento_service() -> DocumentoService:
    return _documento_service


def get_formula_service() -> FormulaService:
    return _formula_service