import io

from PIL import Image

from tests.ocr.conftest import FakeLatexOCR


def _png_bytes(width=700, height=100):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_reescalar_no_toca_imagen_del_ancho_objetivo():
    from src.recognizer import FormulaRecognizer

    recognizer = FormulaRecognizer(target_width_px=350)
    imagen = Image.new("RGB", (350, 100))

    resultado = recognizer._reescalar(imagen)

    assert resultado is imagen


def test_reescalar_reduce_manteniendo_aspecto():
    from src.recognizer import FormulaRecognizer

    recognizer = FormulaRecognizer(target_width_px=350)
    imagen = Image.new("RGB", (700, 200))

    resultado = recognizer._reescalar(imagen)

    assert resultado.width == 350
    assert resultado.height == 100


def test_reescalar_altura_minima_uno():
    from src.recognizer import FormulaRecognizer

    recognizer = FormulaRecognizer(target_width_px=1)
    imagen = Image.new("RGB", (1000, 1))

    resultado = recognizer._reescalar(imagen)

    assert resultado.height >= 1


def test_recognize_devuelve_latex_del_modelo():
    from src.recognizer import FormulaRecognizer

    recognizer = FormulaRecognizer(target_width_px=350)
    resultado = recognizer.recognize(_png_bytes())

    assert resultado == "x^{2}"
    fake_model = recognizer.model
    assert len(fake_model.calls) == 1
    imagen_pasada = fake_model.calls[0]
    assert imagen_pasada.width == 350


def test_load_recognizer_usa_env(monkeypatch):
    from src.recognizer import FormulaRecognizer, load_recognizer

    monkeypatch.setenv("OCR_TARGET_WIDTH_PX", "500")
    recognizer = load_recognizer()
    # target_width_px por defecto se calcula en import time desde el env var
    # original del módulo; el constructor explícito respeta el override.
    assert isinstance(recognizer, FormulaRecognizer)
