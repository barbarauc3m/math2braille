import sys
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest
import requests


def _png_path(tmp_path, name="p.png"):
    ruta = tmp_path / name
    imagen = np.zeros((50, 50, 3), dtype=np.uint8)
    cv2.imwrite(str(ruta), imagen)
    return str(ruta)


def test_detectar_devuelve_boxes(tmp_path, monkeypatch):
    import dibujar_bboxes

    ruta = _png_path(tmp_path)
    respuesta = MagicMock(status_code=200)
    respuesta.json.return_value = {"boxes": [{"x": 1, "y": 1, "ancho": 2, "alto": 2, "confidence_score": 0.9}]}
    monkeypatch.setattr(requests, "post", lambda url, files: respuesta)

    boxes = dibujar_bboxes.detectar(ruta, "http://x/detect")

    assert boxes == [{"x": 1, "y": 1, "ancho": 2, "alto": 2, "confidence_score": 0.9}]


def test_detectar_error_http_termina_programa(tmp_path, monkeypatch):
    import dibujar_bboxes

    ruta = _png_path(tmp_path)
    respuesta = MagicMock(status_code=500, text="boom")
    monkeypatch.setattr(requests, "post", lambda url, files: respuesta)

    with pytest.raises(SystemExit):
        dibujar_bboxes.detectar(ruta, "http://x/detect")


def test_dibujar_boxes_filtra_por_confianza_y_guarda(tmp_path):
    import dibujar_bboxes

    ruta = _png_path(tmp_path, "in.png")
    salida = tmp_path / "out.png"
    boxes = [
        {"x": 1, "y": 1, "ancho": 5, "alto": 5, "confidence_score": 0.9},
        {"x": 2, "y": 2, "ancho": 5, "alto": 5, "confidence_score": 0.1},
    ]

    dibujar_bboxes.dibujar_boxes(ruta, boxes, str(salida), confidence_threshold=0.5)

    assert salida.exists()


def test_dibujar_boxes_imagen_inexistente_termina_programa(tmp_path):
    import dibujar_bboxes

    with pytest.raises(SystemExit):
        dibujar_bboxes.dibujar_boxes(str(tmp_path / "no_existe.png"), [], str(tmp_path / "out.png"), 0.0)


def test_main_flujo_completo(tmp_path, monkeypatch):
    import dibujar_bboxes

    ruta = _png_path(tmp_path, "pagina.png")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["dibujar_bboxes.py", str(ruta), "--confidence", "0.0"]
    )

    respuesta = MagicMock(status_code=200)
    respuesta.json.return_value = {"boxes": []}
    monkeypatch.setattr(requests, "post", lambda url, files: respuesta)

    dibujar_bboxes.main()

    assert (tmp_path / "results" / "pagina_bboxes.png").exists()


def test_main_imagen_inexistente_termina_programa(tmp_path, monkeypatch):
    import dibujar_bboxes

    monkeypatch.setattr(sys, "argv", ["dibujar_bboxes.py", str(tmp_path / "no_existe.png")])

    with pytest.raises(SystemExit):
        dibujar_bboxes.main()
