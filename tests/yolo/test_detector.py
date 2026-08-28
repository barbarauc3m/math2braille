import cv2
import numpy as np
import pytest

from tests.conftest import ROOT_DIR
from tests.yolo.conftest import MODEL_PATH

MUESTRA_PDF = ROOT_DIR + "/derivadasyprimitivas.pdf"


def _png_bytes_from_array(array):
    ok, buffer = cv2.imencode(".png", array)
    assert ok
    return buffer.tobytes()


@pytest.fixture(scope="module")
def detector():
    from src.detector import YoloDetector

    return YoloDetector(model_path=MODEL_PATH, confidence_threshold=0.4)


@pytest.fixture(scope="module")
def pagina_con_formulas_bytes():
    import pymupdf as fitz

    doc = fitz.open(MUESTRA_PDF)
    # La página 4 (índice 3) contiene numerosas fórmulas detectables por el
    # modelo, a diferencia de la portada: ejercita la rama de NMS con cajas
    # candidatas reales, no solo el camino de "sin detecciones".
    pagina = doc[3]
    pixmap = pagina.get_pixmap(matrix=fitz.Matrix(200 / 72, 200 / 72))
    data = pixmap.tobytes("png")
    doc.close()
    return data


def test_detector_carga_modelo_y_expone_input_name(detector):
    assert detector.input_name


def test_detect_sobre_imagen_en_blanco_no_detecta_nada(detector):
    imagen = np.full((640, 480, 3), 255, dtype=np.uint8)
    resultado = detector.detect(_png_bytes_from_array(imagen))
    assert resultado == []


def test_detect_sobre_bytes_invalidos_lanza_value_error(detector):
    with pytest.raises(ValueError, match="No se ha podido decodificar"):
        detector.detect(b"esto no es una imagen")


def test_detect_sobre_pagina_real_devuelve_cajas_validas(detector, pagina_con_formulas_bytes):
    from src.detector import RawBox

    cajas = detector.detect(pagina_con_formulas_bytes)

    assert isinstance(cajas, list)
    assert len(cajas) > 0
    for caja in cajas:
        assert isinstance(caja, RawBox)
        assert caja.x >= 0.0
        assert caja.y >= 0.0
        assert caja.ancho > 0.0
        assert caja.alto > 0.0
        assert 0.0 <= caja.confidence_score <= 1.0


def test_letterbox_devuelve_imagen_cuadrada(detector):
    imagen = np.zeros((100, 300, 3), dtype=np.uint8)
    padded, scale, pad_x, pad_y = detector._letterbox(imagen)

    assert padded.shape == (detector.img_size, detector.img_size, 3)
    assert scale == pytest.approx(detector.img_size / 300)
    assert pad_x >= 0
    assert pad_y >= 0


def test_preprocess_forma_tensor(detector):
    imagen = np.zeros((100, 300, 3), dtype=np.uint8)
    tensor, scale, pad_x, pad_y = detector._preprocess(imagen)

    assert tensor.shape == (1, 3, detector.img_size, detector.img_size)
    assert tensor.dtype == np.float32


def test_load_detector_usa_variables_de_entorno(monkeypatch):
    from src.detector import load_detector

    monkeypatch.setenv("MODEL_PATH", MODEL_PATH)
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.7")

    detector_cargado = load_detector()

    assert detector_cargado.confidence_threshold == 0.7
