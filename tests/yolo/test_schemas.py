import pytest
from pydantic import ValidationError


def test_bounding_box_valida():
    from src.schemas import BoundingBox

    caja = BoundingBox(x=1.0, y=2.0, ancho=3.0, alto=4.0, confidence_score=0.5)
    assert caja.confidence_score == 0.5


@pytest.mark.parametrize("valor", [-0.1, 1.1])
def test_bounding_box_confidence_fuera_de_rango(valor):
    from src.schemas import BoundingBox

    with pytest.raises(ValidationError):
        BoundingBox(x=0, y=0, ancho=1, alto=1, confidence_score=valor)


def test_detection_response_lista_vacia():
    from src.schemas import DetectionResponse

    respuesta = DetectionResponse(boxes=[])
    assert respuesta.boxes == []


def test_detection_response_con_cajas():
    from src.schemas import BoundingBox, DetectionResponse

    caja = BoundingBox(x=1.0, y=2.0, ancho=3.0, alto=4.0, confidence_score=0.9)
    respuesta = DetectionResponse(boxes=[caja])
    assert len(respuesta.boxes) == 1
