"""
service/yolo — servicio de detección de regiones matemáticas (RF-03).

Se invoca una única vez por documento durante la detección adelantada
(eager loading, Secc. 5.1.2): DocumentoService rasteriza cada página y
llama a este servicio a través de YoloClient, antes de mostrar el visor.
"""

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.detector import load_detector
from src.schemas import BoundingBox, DetectionResponse

app = FastAPI(title="math2pix - service/yolo")
detector = load_detector()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/detect", response_model=DetectionResponse)
async def detect(file: UploadFile = File(...)):
    """
    Recibe la imagen rasterizada de una página (RF-02) y devuelve los
    bounding boxes detectados (RF-03). No recibe ni asigna número de
    página ni documento_id: esa asociación la hace DocumentoService al
    recorrer las páginas, manteniendo este servicio agnóstico del resto
    del dominio (ver Secc. 5.4.1, capa de adaptadores).
    """
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Fichero de imagen vacío")

    try:
        raw_boxes = detector.detect(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    boxes = [
        BoundingBox(x=b.x, y=b.y, ancho=b.ancho, alto=b.alto, confidence_score=b.confidence_score)
        for b in raw_boxes
    ]
    return DetectionResponse(boxes=boxes)