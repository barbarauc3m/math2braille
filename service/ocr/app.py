"""
service/ocr — reconocimiento de fórmulas matemáticas vía pix2tex (RF-05).

Se invoca bajo demanda, una vez por cada fórmula que el usuario
selecciona en el visor (CU-03), nunca de forma adelantada.
"""

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.recognizer import load_recognizer
from src.schemas import OcrResponse

app = FastAPI(title="math2pix - service/ocr")
recognizer = load_recognizer()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ocr", response_model=OcrResponse)
async def ocr(file: UploadFile = File(...)):
    """
    Recibe el recorte de imagen correspondiente a una única fórmula
    (ya recortado por el backend según el bounding box, con el margen
    de seguridad BBOX_MARGIN_PX) y devuelve el LaTeX reconocido.
    """
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Fichero de imagen vacío")

    try:
        latex = recognizer.recognize(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de OCR: {e}")

    return OcrResponse(latex=latex)