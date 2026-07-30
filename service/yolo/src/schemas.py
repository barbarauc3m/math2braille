"""
DTOs de service/yolo.

BoundingBox es la estructura transitoria que YoloClient recibe en el
backend y que DocumentoService traduce en filas de `formula` (con el
campo mathml aún vacío) a través de FormulaRepository.guardar_lote()
(Secc. 5.4.2 de la memoria). No es una entidad persistente por sí misma.

Nótese que no incluye class_id: el dataset de entrenamiento distingue
5 categorías (Definite Integral, Differentiation, Indefinite Integral,
Limits, Trigonometry), pero para esta herramienta todas representan
por igual una región de "fórmula matemática" — la clase se descarta
tras usarse internamente en detector.py para escoger la confianza.
"""

from typing import List

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float = Field(..., description="Esquina superior izquierda, coord. X (px)")
    y: float = Field(..., description="Esquina superior izquierda, coord. Y (px)")
    ancho: float = Field(..., description="Ancho del recuadro (px)")
    alto: float = Field(..., description="Alto del recuadro (px)")
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class DetectionResponse(BaseModel):
    boxes: List[BoundingBox]