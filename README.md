# math2braille
Herramienta de accesiblidad a expresiones matemáticas en documentos PDF

### LEVANTAR SERVICIOS

**SERVICE/YOLO**
```bash
cd service/yolo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt # solo la primera vez
MODEL_PATH=./model/weights.onnx uvicorn app:app --port 8000 --reload
```
Comprobación
```bash
curl http://127.0.0.1:8000/health
```


**SERVICE/OCR**
```bash
cd service/ocr
python3 -m venv venv && source venv/bin/activate
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
uvicorn app:app --port 8001 --reload
```
Comprobación
```bash
curl http://127.0.0.1:8001/health
```

**SERVICE/BACKEND**
```bash
cd service/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
YOLO_SERVICE_URL=http://127.0.0.1:8000 \
OCR_SERVICE_URL=http://127.0.0.1:8001 \
DATABASE_PATH=./data/db/math2pix.sqlite \
UPLOADS_PATH=./data/uploads \
uvicorn main:app --port 8002 --reload
```


### LEVANTAR SERVICIOS

Swagger: 
> http://127.0.0.1:8002/docs#/

Subir un documento y ver el progreso en vivo (-N desactiva el buffering de curl, para ver las líneas según llegan):
```bash
curl -N -X POST http://127.0.0.1:8002/documentos \
  -F "file=@ruta/a/apuntes.pdf"
```

Historial
```bash
curl http://127.0.0.1:8002/documentos
```

Fórmulas del documento
```bash
curl http://127.0.0.1:8002/documentos/1/formulas
```

Consultar una fórmula (dispara OCR la primera vez)
```bash
curl http://127.0.0.1:8002/formulas/1
```

Editar una fórmula 
```bash
# Fórmula válida
curl -X PUT http://127.0.0.1:8002/formulas/1 \
  -H "Content-Type: application/json" \
  -d '{"mathml": "<math><mi>x</mi><mo>+</mo><mn>1</mn></math>"}'
```
```bash
# inválida — debe responder 400
curl -i -X PUT http://127.0.0.1:8002/formulas/1 \
  -H "Content-Type: application/json" \
  -d '{"mathml": "<div>no es math</div>"}'
```

Reabrir y eliminar documento
```bash
curl http://127.0.0.1:8002/documentos/1        # actualiza fecha_ultima_apertura
curl -i -X DELETE http://127.0.0.1:8002/documentos/1   # debe responder 204
curl http://127.0.0.1:8002/documentos/1/formulas        # debe devolver {"formulas": []}
```

Limpiar los ficheros
```bash
rm -rf data/db/math2pix_test.sqlite data/uploads_test
```