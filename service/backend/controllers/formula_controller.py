"""
Endpoints para obtener y editar una fórmula, respectivamente. 
"""

from fastapi import APIRouter, Depends, HTTPException

from api_schemas import FormulaEditarIn, FormulaOut
from dependencies import get_formula_service
from services.formula_service import FormulaService
from services.exceptions import FormulaNoEncontradaError, ProcesamientoFormulaError
from utils.xhtml_validator import XhtmlValidationError

router = APIRouter(prefix="/formulas", tags=["formulas"])


def _formula_a_schema(formula) -> FormulaOut:
    return FormulaOut(
        id=formula.id, pagina=formula.pagina, x=formula.x, y=formula.y,
        ancho=formula.ancho, alto=formula.alto,
        confidence_score=formula.confidence_score,
        mathml=formula.mathml, fecha_procesado=formula.fecha_procesado,
    )


@router.get("/{formula_id}", response_model=FormulaOut)
def consultar_formula(
    formula_id: int,
    formula_service: FormulaService = Depends(get_formula_service),
):
    """
    RF-05/RF-06/CU-03: si la fórmula ya está en caché, se devuelve al
    momento; si no, dispara OCR + conversión a MathML + validación.
    Puede tardar varios segundos la primera vez (pix2tex sobre CPU).
    """
    try:
        formula = formula_service.consultar_formula(formula_id)
    except FormulaNoEncontradaError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProcesamientoFormulaError as e:
        # Fallo de OCR o de conversión: no es culpa del cliente, sino
        # del servicio externo o del contenido de la fórmula (502).
        raise HTTPException(status_code=502, detail=str(e))

    return _formula_a_schema(formula)


@router.put("/{formula_id}", response_model=FormulaOut)
def editar_formula(
    formula_id: int,
    body: FormulaEditarIn,
    formula_service: FormulaService = Depends(get_formula_service),
):
    """
    RF-12/CU-04: guarda una edición manual del MathML, validándola
    antes de persistir (RF-11). Un fragmento inválido responde 400 sin
    tocar el mathml anterior — el frontend traduce esto en el error
    accesible de RF-20 (aria-live="assertive").
    """
    try:
        formula = formula_service.editar_formula(formula_id, body.mathml)
    except FormulaNoEncontradaError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except XhtmlValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _formula_a_schema(formula)