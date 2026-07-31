"""
Modelo de dominio: Formula.

Corresponde a una fila de la tabla `formula` (schema.sql, Fase 1).
`mathml` y `fecha_procesado` son nullable: una fórmula recién
detectada por YOLO (RF-03) existe en base de datos sin mathml todavía;
se rellena solo cuando el usuario la selecciona y pasa por OCR +
MathmlConverter (RF-05, RF-06). Esa nulidad es precisamente lo que
permite el cacheo de CU-03 (si mathml ya existe, no se vuelve a
invocar service/ocr).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Formula:
    documento_id: int
    pagina: int
    x: float
    y: float
    ancho: float
    alto: float
    confidence_score: float
    id: Optional[int] = None
    mathml: Optional[str] = None
    fecha_procesado: Optional[str] = None

    @property
    def ya_procesada(self) -> bool:
        """True si ya tiene mathml calculado (evita repetir OCR, CU-03)."""
        return self.mathml is not None

    @staticmethod
    def from_row(row) -> "Formula":
        return Formula(
            id=row["id"],
            documento_id=row["documento_id"],
            pagina=row["pagina"],
            x=row["x"],
            y=row["y"],
            ancho=row["ancho"],
            alto=row["alto"],
            confidence_score=row["confidence_score"],
            mathml=row["mathml"],
            fecha_procesado=row["fecha_procesado"],
        )