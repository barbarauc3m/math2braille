import sys
import types

import pytest

from tests.conftest import OCR_DIR, YOLO_DIR


def _purge_modules():
    for name in list(sys.modules):
        if (
            name == "src"
            or name.startswith("src.")
            or name == "app"
            or name == "pix2tex"
            or name.startswith("pix2tex.")
        ):
            del sys.modules[name]


class FakeLatexOCR:
    """Sustituto ligero de pix2tex.cli.LatexOCR (evita depender de torch en los tests)."""

    instances = []

    def __init__(self, *args, **kwargs):
        self.calls = []
        FakeLatexOCR.instances.append(self)

    def __call__(self, image):
        self.calls.append(image)
        return "x^{2}"


def _activate():
    _purge_modules()
    # service/ocr/src es un namespace package (sin __init__.py): si el
    # directorio de yolo (cuyo "src" sí tiene __init__.py) conviviera en
    # sys.path, "import src" resolvería siempre al de yolo. Se retira
    # explícitamente para que cada suite de tests importe solo su "src".
    while YOLO_DIR in sys.path:
        sys.path.remove(YOLO_DIR)
    if sys.path[0] != OCR_DIR:
        while OCR_DIR in sys.path:
            sys.path.remove(OCR_DIR)
        sys.path.insert(0, OCR_DIR)

    FakeLatexOCR.instances = []
    fake_pix2tex = types.ModuleType("pix2tex")
    fake_pix2tex_cli = types.ModuleType("pix2tex.cli")
    fake_pix2tex_cli.LatexOCR = FakeLatexOCR
    fake_pix2tex.cli = fake_pix2tex_cli
    sys.modules["pix2tex"] = fake_pix2tex
    sys.modules["pix2tex.cli"] = fake_pix2tex_cli


# Se activa ya durante la recolección (import de este conftest), porque los
# tests importan `src`/`app` en la cabecera del módulo, antes de que se
# ejecute ningún fixture.
_activate()


@pytest.fixture(autouse=True, scope="module")
def ocr_env():
    _activate()
    yield
    _purge_modules()
