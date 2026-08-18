"""
Esquemas Pydantic de entrada/salida de la API REST.

Definen el contrato público con el frontend, no la estructura interna de BD.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentoOut(BaseModel):
    id: int
    nombre_archivo: str
    num_paginas: int
    fecha_carga: str
    fecha_ultima_apertura: str


class FormulaOut(BaseModel):
    id: int
    pagina: int
    x: float
    y: float
    ancho: float
    alto: float
    confidence_score: float
    mathml: Optional[str] = None
    fecha_procesado: Optional[str] = None


class HistorialOut(BaseModel):
    documentos: List[DocumentoOut]


class FormulasDocumentoOut(BaseModel):
    formulas: List[FormulaOut]


class FormulaEditarIn(BaseModel):
    mathml: str = Field(..., description="Fragmento XHTML+MathML editado por el usuario (RF-12)")