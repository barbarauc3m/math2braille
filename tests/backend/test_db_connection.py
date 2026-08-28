import sqlite3

import pytest


def test_get_connection_creates_file_and_schema(fresh_db):
    from db import connection

    conn = connection.get_connection()
    try:
        tablas = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"documento", "formula"}.issubset(tablas)
    finally:
        conn.close()


def test_get_connection_creates_parent_dirs(tmp_path, monkeypatch):
    from db import connection

    nested_path = tmp_path / "nested" / "dir" / "db.sqlite"
    monkeypatch.setattr(connection, "DATABASE_PATH", str(nested_path))

    conn = connection.get_connection()
    conn.close()

    assert nested_path.exists()


def test_get_connection_is_idempotent(fresh_db):
    from db import connection

    conn1 = connection.get_connection()
    conn1.close()
    # Segunda apertura no debe fallar aunque las tablas ya existan (IF NOT EXISTS).
    conn2 = connection.get_connection()
    conn2.close()


def test_db_session_commits_on_success(fresh_db):
    from db import connection

    with connection.db_session() as conn:
        conn.execute(
            "INSERT INTO documento (nombre_archivo, ruta_archivo, num_paginas) VALUES (?, ?, ?)",
            ("a.pdf", "/tmp/a.pdf", 1),
        )

    with connection.db_session() as conn:
        row = conn.execute("SELECT * FROM documento").fetchone()
        assert row["nombre_archivo"] == "a.pdf"


def test_db_session_rolls_back_on_error(fresh_db):
    from db import connection

    with pytest.raises(sqlite3.IntegrityError):
        with connection.db_session() as conn:
            conn.execute(
                "INSERT INTO documento (nombre_archivo, ruta_archivo, num_paginas) VALUES (?, ?, ?)",
                ("a.pdf", "/tmp/a.pdf", 1),
            )
            # documento_id inexistente -> viola la FK, fuerza rollback.
            conn.execute(
                "INSERT INTO formula (documento_id, pagina, x, y, ancho, alto, confidence_score) "
                "VALUES (999, 1, 0, 0, 1, 1, 0.9)"
            )

    with connection.db_session() as conn:
        rows = conn.execute("SELECT * FROM documento").fetchall()
        assert rows == []
