"""
Punto de entrada de service/backend.

Orquestador central: es el único servicio con endpoints pensados para
consumo directo del frontend (yolo y ocr son internos, ver
docker-compose.yml). Se expone solo en 127.0.0.1 (RNF de seguridad
por aislamiento de red).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import FRONTEND_ORIGINS
from controllers import documento_controller, formula_controller

app = FastAPI(title="math2braille - service/backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(documento_controller.router)
app.include_router(formula_controller.router)


@app.get("/health")
def health():
    return {"status": "ok"}