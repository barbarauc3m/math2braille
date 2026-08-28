import os
import sys

import pytest

from tests.conftest import BACKEND_DIR

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_PATH", os.path.join(BACKEND_DIR, "_unused_default.sqlite"))
os.environ.setdefault("UPLOADS_PATH", os.path.join(BACKEND_DIR, "_unused_uploads"))


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Aisla cada test que toque la BD real en un fichero sqlite propio."""
    from db import connection

    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(connection, "DATABASE_PATH", str(db_path))
    return str(db_path)


@pytest.fixture
def documento_repository(fresh_db):
    from repositories.documento_repository import DocumentoRepository

    return DocumentoRepository()


@pytest.fixture
def formula_repository(fresh_db):
    from repositories.formula_repository import FormulaRepository

    return FormulaRepository()


@pytest.fixture
def simple_pdf_bytes(tmp_path):
    """Genera un PDF real (2 páginas, con texto) usando PyMuPDF."""
    import pymupdf as fitz

    doc = fitz.open()
    pagina1 = doc.new_page()
    pagina1.insert_text((72, 72), "Hola mundo")
    pagina2 = doc.new_page()
    pagina2.insert_text((72, 72), "Segunda pagina")
    data = doc.tobytes()
    doc.close()
    return data
