FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# Precarga los pesos de pix2tex en tiempo de build (se descargan de
# GitHub la primera vez que se instancia LatexOCR). Así el contenedor
# final funciona sin acceso a internet, en línea con el despliegue
# totalmente local descrito en la memoria.
RUN python -c "from pix2tex.cli import LatexOCR; LatexOCR()"

COPY app.py .
COPY src/ ./src/

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]