"""
Modelo de dominio: Documento.

Corresponde a una fila de la tabla `documento` (schema.sql, Fase 1).
Es una estructura de datos simple (sin lógica de negocio): la
orquestación vive en DocumentoService (Fase 6), y el acceso a datos
en DocumentoRepository (este mismo paquete).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Documento:
    nombre_archivo: str
    ruta_archivo: str
    num_paginas: int
    id: Optional[int] = None
    fecha_carga: Optional[str] = None
    fecha_ultima_apertura: Optional[str] = None

    @staticmethod
    def from_row(row) -> "Documento":
        """Construye un Documento a partir de una sqlite3.Row (row_factory=sqlite3.Row)."""
        return Documento(
            id=row["id"],
            nombre_archivo=row["nombre_archivo"],
            ruta_archivo=row["ruta_archivo"],
            num_paginas=row["num_paginas"],
            fecha_carga=row["fecha_carga"],
            fecha_ultima_apertura=row["fecha_ultima_apertura"],
        )