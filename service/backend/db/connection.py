"""
Gestión de la conexión a la base de datos SQLite embebida.

Se usa directamente el módulo sqlite3 de la biblioteca estándar (sin ORM),
en línea con la decisión de minimizar dependencias (RNF-01, RNF-03) descrita
en la Secc. 5.3 de la memoria.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./data/db/math2pix.sqlite")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Aplica schema.sql. Es idempotente gracias a los IF NOT EXISTS."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())


def get_connection() -> sqlite3.Connection:
    """
    Abre una conexión a la base de datos, creando el fichero y las tablas
    si todavía no existen (p. ej. primer arranque sobre un volumen vacío).
    """
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row              

    _ensure_schema(conn)
    return conn


@contextmanager
def db_session():
    """
    Context manager para usar en los repositorios:

        with db_session() as conn:
            conn.execute("INSERT INTO documento (...) VALUES (...)")

    Hace commit si todo va bien y rollback si se lanza una excepción,
    cerrando siempre la conexión al salir.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()