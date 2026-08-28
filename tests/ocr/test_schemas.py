def test_ocr_response():
    from src.schemas import OcrResponse

    respuesta = OcrResponse(latex="x^2")
    assert respuesta.latex == "x^2"
