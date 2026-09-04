# math2braille

`math2braille` es un editor accesible que tome documentos PDF con fórmulas matemáticas (por ejemplo, apuntes o ejercicios escaneados/exportados) y las convierte a **MathML**, un formato que los lectores de pantalla y las líneas braille saben interpretar y transcribir a braille matemático de forma nativa. El usuario navega el documento página a página en un visor web accesible, con las fórmulas detectadas automáticamente y editables a mano si el reconocimiento falla.


## Cómo lanzar

1. Tener Docker y Docker Compose instalados
2. Clonar el repositorio
3. Abrir la terminal
4. Lanzar run.sh 
```bash
./run.sh    
```
La primera vez tardará un poco en construir las imágenes (especialmente `ocr`, ya que debe instalar PyTorch).

5. Abrir el navegador en http://127.0.0.1
6. Usar el editor!



> Nota: El servicio `ocr` tiene un límite de memoria de 2GB configurado en `docker-compose.yml`; si la máquina del usuario tiene poca RAM libre el reconocimiento puede ir lento o fallar.


## Documentación auxiliar. Cómo funciona

1. **Detección (`service/yolo`)** — Al subir un PDF, cada página se
rasteriza y se pasa por un modelo YOLO (ONNX) el cual busca página por página recuadros donde haya fórmulas matemáticas. Las coordenadas de estos recuadros se guardan en base de datos y se ocultan antes de pasarlas a PyMuPDF, encargado de realizar un OCR sobre el texto plano del documento. 
2. **Reconocimiento (`service/ocr`)** — Cuando el usuario selecciona una fórmula concreta, la región correspondiente se envía a un modelo OCR matemático (`pix2tex`) que devuelve el LaTeX reconocido.
3. **Conversión y validación (`service/backend`)** — El LaTeX se convierte a MathML (`latex2mathml`) y el resultado se cachea en SQLite: la próxima vez que se abra la misma fórmula no se vuelve a ejecutar el OCR.
4. **Edición manual** — Si el reconocimiento automático falla o es
incorrecto, el MathML se puede editar directamente en el visor; la
edición se valida antes de persistirse, así que un fragmento sintácticamente inválido nunca sobrescribe el resultado anterior.
5. **Frontend accesible (`service/frontend`)** — Página de inicio (subir PDF nuevo o reabrir uno del historial) y visor de documento, ambos pensados para navegación con lector de pantalla.

## Documentación auxiliar. Arquitectura

```
                         ┌──────────────┐
   navegador  ──80──────▶│   frontend   │  (nginx, sirve el visor y hace
                         │   (nginx)    │   de proxy a /documentos, /formulas)
                         └──────┬───────┘
                                │ 8000
                         ┌──────▼───────┐
                         │   backend    │  orquestador, único servicio con
                         │  (FastAPI)   │  API pensada para el frontend
                         └───┬──────┬───┘
                    interno  │      │  interno
                     ┌───────▼┐   ┌─▼────────┐
                     │  yolo  │   │   ocr    │
                     │(FastAPI│   │(FastAPI +│
                     │+ ONNX) │   │ pix2tex) │
                     └────────┘   └──────────┘
```

- **backend**: orquesta la subida de documentos, la detección adelantada de
  fórmulas por página, la caché en SQLite y la API que consume el
  frontend. Es el único servicio expuesto a 127.0.0.1 junto al frontend;
  `yolo` y `ocr` son internos a la red Docker.
- **yolo**: detecta las regiones de fórmulas de una imagen de página.
- **ocr**: reconoce el LaTeX de una imagen recortada de fórmula (`pix2tex`).
- **frontend**: interfaz web (HTML/CSS/JS vanilla, sin build step) servida
  por nginx, que también actúa de proxy inverso hacia el backend.



## Documentación auxiliar. Configuración

Las variables de entorno relevantes están documentadas en `.env.example`:

| Variable            | Descripción                                                    |
|---------------------|------------------------------------------------------------------|
| `BACKEND_PORT`      | Puerto expuesto del backend en localhost (por defecto `8000`)   |
| `FRONTEND_PORT`      | Puerto expuesto del frontend en localhost (por defecto `80`)    |
| `DATABASE_PATH`      | Ruta al SQLite dentro del contenedor del backend                |
| `UPLOADS_PATH`       | Ruta donde se guardan los PDF subidos                            |
| `YOLO_SERVICE_URL`   | URL interna del servicio de detección                            |
| `OCR_SERVICE_URL`    | URL interna del servicio de reconocimiento                       |
| `BBOX_MARGIN_PX`     | Margen (px) alrededor del bounding box al recortar antes del OCR |

## Documentación auxiliar. Tests
Existen 3 suites de tests (una por cada servicio con lógica, es decir, service/backend, service/yolo y service/ocr).

Para correr una suite de tests, se debe tener activar el entorno virtual del servicio a testear y lanzar los tests con pytest.

Ejemplo para service/backend:

```bash
source service/backend/venv/bin/activate  # Activar entorno virtual de service/backend
pip install pytest pytest-cov httpx
pytest tests/backend/   
```

## Documentación auxiliar. Licencia

Este proyecto está bajo la Licencia **GNU Affero General Public License v3.0** (AGPL-3.0). 
Consulta el archivo [LICENSE](LICENSE) para ver los términos completos.
