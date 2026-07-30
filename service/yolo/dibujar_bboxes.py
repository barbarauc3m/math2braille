"""
Script auxiliar (fuera del repositorio math2pix) para verificar
visualmente que service/yolo detecta bien las fórmulas.

Llama al endpoint /detect con una imagen, dibuja los bounding boxes
devueltos en rojo sobre la imagen original, y guarda el resultado en
./results/<nombre_imagen>_bboxes.png

Uso:
    python dibujar_bboxes.py ruta/a/pagina_prueba.png
    python dibujar_bboxes.py ruta/a/pagina_prueba.png --url http://127.0.0.1:8000/detect
    python dibujar_bboxes.py ruta/a/pagina_prueba.png --confidence 0.4

Requiere: pip install requests opencv-python
(usa opencv "normal", no headless, porque aquí sí queremos guardar
imágenes con dibujos — no es el mismo entorno que el contenedor Docker)
"""

import argparse
import os
import sys

import cv2
import requests


def detectar(image_path: str, url: str) -> list[dict]:
    with open(image_path, "rb") as f:
        response = requests.post(url, files={"file": f})

    if response.status_code != 200:
        print(f"Error del servicio ({response.status_code}): {response.text}")
        sys.exit(1)

    return response.json()["boxes"]


def dibujar_boxes(image_path: str, boxes: list[dict], output_path: str, confidence_threshold: float):
    image = cv2.imread(image_path)
    if image is None:
        print(f"No se ha podido leer la imagen: {image_path}")
        sys.exit(1)

    dibujadas = 0
    for box in boxes:
        if box["confidence_score"] < confidence_threshold:
            continue

        x, y = int(box["x"]), int(box["y"])
        w, h = int(box["ancho"]), int(box["alto"])

        # Rectángulo rojo (BGR: 0, 0, 255), grosor 2px
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # Etiqueta con el score encima del recuadro
        label = f"{box['confidence_score']:.2f}"
        cv2.putText(image, label, (x, max(y - 6, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        dibujadas += 1

    cv2.imwrite(output_path, image)
    print(f"{dibujadas}/{len(boxes)} cajas dibujadas (umbral >= {confidence_threshold}).")
    print(f"Guardado en: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Visualiza los bounding boxes de service/yolo")
    parser.add_argument("image_path", help="Ruta a la imagen de la página a analizar")
    parser.add_argument("--url", default="http://127.0.0.1:8000/detect",
                         help="URL del endpoint /detect (por defecto: http://127.0.0.1:8000/detect)")
    parser.add_argument("--confidence", type=float, default=0.0,
                         help="Umbral mínimo de confianza para dibujar una caja (por defecto: 0.0, dibuja todas)")
    args = parser.parse_args()

    if not os.path.isfile(args.image_path):
        print(f"No existe el fichero: {args.image_path}")
        sys.exit(1)

    os.makedirs("results", exist_ok=True)

    nombre_base = os.path.splitext(os.path.basename(args.image_path))[0]
    output_path = os.path.join("results", f"{nombre_base}_bboxes.png")

    boxes = detectar(args.image_path, args.url)
    print(f"Detectadas {len(boxes)} cajas en total.")

    dibujar_boxes(args.image_path, boxes, output_path, args.confidence)


if __name__ == "__main__":
    main()