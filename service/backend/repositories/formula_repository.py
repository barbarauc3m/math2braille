"""
Repositorio de acceso a datos para Formula.
"""

from typing import List, Optional

from db.connection import db_session
from models.formula import Formula


class FormulaRepository:

    def guardar_lote(self, documento_id: int, formulas: List[Formula]) -> List[Formula]:
        """
        Inserta de una vez todas las fórmulas detectadas por YOLO para un
        documento (CU-01), todavía sin mathml. Se usa executemany en una
        única transacción para no abrir/cerrar conexión por fórmula
        cuando un documento puede tener decenas de ellas.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            for formula in formulas:
                cursor.execute(
                    """
                    INSERT INTO formula (documento_id, pagina, x, y, ancho, alto, confidence_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        documento_id,
                        formula.pagina,
                        formula.x,
                        formula.y,
                        formula.ancho,
                        formula.alto,
                        formula.confidence_score,
                    ),
                )
                formula.id = cursor.lastrowid

            rows = conn.execute(
                "SELECT * FROM formula WHERE documento_id = ? ORDER BY id",
                (documento_id,),
            ).fetchall()
            return [Formula.from_row(row) for row in rows]

    def obtener_por_id(self, formula_id: int) -> Optional[Formula]:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM formula WHERE id = ?", (formula_id,)
            ).fetchone()
            return Formula.from_row(row) if row else None

    def obtener_por_documento(self, documento_id: int) -> List[Formula]:
        """Todas las fórmulas de un documento, para pintar el visor (RF-07)."""
        with db_session() as conn:
            rows = conn.execute(
                "SELECT * FROM formula WHERE documento_id = ? ORDER BY pagina, id",
                (documento_id,),
            ).fetchall()
            return [Formula.from_row(row) for row in rows]

    def actualizar_mathml(self, formula_id: int, mathml: str) -> Optional[Formula]:
        """
        Guarda el mathml calculado (RF-06, tras OCR, o RF-12 tras una
        edición validada). Actualiza también fecha_procesado, que es lo
        que distingue una fórmula "procesada" de una "sin procesar" para
        el aria-label dinámico del frontend (RF-17).
        """
        with db_session() as conn:
            conn.execute(
                """
                UPDATE formula
                SET mathml = ?, fecha_procesado = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (mathml, formula_id),
            )
            row = conn.execute(
                "SELECT * FROM formula WHERE id = ?", (formula_id,)
            ).fetchone()
            return Formula.from_row(row) if row else None