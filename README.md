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
```
