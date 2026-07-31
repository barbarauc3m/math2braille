"""
Repositorio de acceso a datos para Documento.

Aísla toda la SQL relacionada con `documento` del resto del backend,
permitiendo mockear este repositorio en los tests de DocumentoService
sin depender de una base de datos real (justificación OOP, Secc. 5.3).
"""

from typing import List, Optional

from db.connection import db_session
from models.documento import Documento


class DocumentoRepository:

    def crear(self, documento: Documento) -> Documento:
        """Inserta un documento nuevo (CU-01, tras el rasterizado inicial)."""
        with db_session() as conn:
            cursor = conn.execute(
                """
                INSERT INTO documento (nombre_archivo, ruta_archivo, num_paginas)
                VALUES (?, ?, ?)
                """,
                (documento.nombre_archivo, documento.ruta_archivo, documento.num_paginas),
            )
            documento.id = cursor.lastrowid

            # Releemos la fila para recuperar los valores por defecto que
            # asigna SQLite (fecha_carga, fecha_ultima_apertura).
            row = conn.execute(
                "SELECT * FROM documento WHERE id = ?", (documento.id,)
            ).fetchone()
            return Documento.from_row(row)

    def obtener_por_id(self, documento_id: int) -> Optional[Documento]:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM documento WHERE id = ?", (documento_id,)
            ).fetchone()
            return Documento.from_row(row) if row else None

    def listar_historial(self) -> List[Documento]:
        """Historial de documentos (RF-14), más reciente primero."""
        with db_session() as conn:
            rows = conn.execute(
                "SELECT * FROM documento ORDER BY fecha_ultima_apertura DESC"
            ).fetchall()
            return [Documento.from_row(row) for row in rows]

    def actualizar_fecha_apertura(self, documento_id: int) -> None:
        """
        Marca el documento como reabierto ahora mismo (RF-15). No vuelve
        a ejecutar YOLO: DocumentoService reutiliza las fórmulas ya
        guardadas en `formula` para este documento_id.
        """
        with db_session() as conn:
            conn.execute(
                "UPDATE documento SET fecha_ultima_apertura = CURRENT_TIMESTAMP WHERE id = ?",
                (documento_id,),
            )

    def eliminar(self, documento_id: int) -> None:
        """
        Borrado permanente (RF-16). El ON DELETE CASCADE de schema.sql
        se encarga de eliminar también las fórmulas asociadas: no hace
        falta borrarlas aquí explícitamente.
        """
        with db_session() as conn:
            conn.execute("DELETE FROM documento WHERE id = ?", (documento_id,))