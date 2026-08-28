import os
import sys

import pytest

from tests.conftest import OCR_DIR, YOLO_DIR

MODEL_PATH = os.path.join(YOLO_DIR, "model", "weights.onnx")


def _purge_modules():
    for name in list(sys.modules):
        if name == "src" or name.startswith("src.") or name == "app" or name == "dibujar_bboxes":
            del sys.modules[name]


def _activate():
    _purge_modules()
    # service/ocr/src es un namespace package (sin __init__.py): si su
    # directorio conviviera en sys.path con el de yolo (que sí tiene
    # __init__.py), "import src" resolvería siempre al de yolo. Se retira
    # explícitamente para que cada suite de tests importe solo su "src".
    while OCR_DIR in sys.path:
        sys.path.remove(OCR_DIR)
    if sys.path[0] != YOLO_DIR:
        while YOLO_DIR in sys.path:
            sys.path.remove(YOLO_DIR)
        sys.path.insert(0, YOLO_DIR)
    os.environ["MODEL_PATH"] = MODEL_PATH
    os.environ["CONFIDENCE_THRESHOLD"] = "0.4"


# Se activa ya durante la recolección (import de este conftest), porque los
# tests importan `src`/`app` en la cabecera del módulo, antes de que se
# ejecute ningún fixture.
_activate()


@pytest.fixture(autouse=True, scope="module")
def yolo_env():
    _activate()
    yield
    _purge_modules()
