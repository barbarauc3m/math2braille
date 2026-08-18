"""
Configuración centralizada leída de variables de entorno (ver .env.example).
Las que usan directamente adapters/ y services/ (YOLO_SERVICE_URL,
OCR_SERVICE_URL, DATABASE_PATH, UPLOADS_PATH, BBOX_MARGIN_PX) se leen
en sus propios load_*() — aquí solo lo que necesita la capa de API.
"""

import os

# Orígenes desde los que el frontend puede llamar a esta API. Con
# backend y frontend expuestos solo en 127.0.0.1 (docker-compose.yml),
# el riesgo de un origen no confiable es bajo, pero se restringe
# igualmente en vez de usar "*".
FRONTEND_ORIGINS = os.environ.get(
    "FRONTEND_ORIGIN", "http://127.0.0.1,http://localhost"
).split(",")