import sqlite3


def _sqlite_type(value):
    if isinstance(value, bool):
        return "INTEGER"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, float):
        return "REAL"
    return "TEXT"


def _row(mapping):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    columnas = ", ".join(mapping.keys())
    placeholders = ", ".join("?" for _ in mapping)
    definicion = ", ".join(f"{k} {_sqlite_type(v)}" for k, v in mapping.items())
    conn.execute(f"CREATE TABLE t ({definicion})")
    conn.execute(f"INSERT INTO t ({columnas}) VALUES ({placeholders})", list(mapping.values()))
    return conn.execute("SELECT * FROM t").fetchone()


def test_documento_from_row():
    from models.documento import Documento

    row = _row(
        {
            "id": 1,
            "nombre_archivo": "a.pdf",
            "ruta_archivo": "/tmp/a.pdf",
            "num_paginas": 3,
            "fecha_carga": "2024-01-01",
            "fecha_ultima_apertura": "2024-01-02",
        }
    )
    documento = Documento.from_row(row)
    assert documento.id == 1
    assert documento.nombre_archivo == "a.pdf"
    assert documento.ruta_archivo == "/tmp/a.pdf"
    assert documento.num_paginas == 3
    assert documento.fecha_carga == "2024-01-01"
    assert documento.fecha_ultima_apertura == "2024-01-02"


def test_documento_defaults():
    from models.documento import Documento

    documento = Documento(nombre_archivo="a.pdf", ruta_archivo="/tmp/a.pdf", num_paginas=1)
    assert documento.id is None
    assert documento.fecha_carga is None
    assert documento.fecha_ultima_apertura is None


def test_formula_from_row():
    from models.formula import Formula

    row = _row(
        {
            "id": 5,
            "documento_id": 1,
            "pagina": 2,
            "x": 1.0,
            "y": 2.0,
            "ancho": 3.0,
            "alto": 4.0,
            "confidence_score": 0.9,
            "mathml": "<math/>",
            "fecha_procesado": "2024-01-01",
        }
    )
    formula = Formula.from_row(row)
    assert formula.id == 5
    assert formula.documento_id == 1
    assert formula.mathml == "<math/>"
    assert formula.ya_procesada is True


def test_formula_ya_procesada_false_when_no_mathml():
    from models.formula import Formula

    formula = Formula(
        documento_id=1, pagina=1, x=0, y=0, ancho=1, alto=1, confidence_score=0.5
    )
    assert formula.ya_procesada is False
