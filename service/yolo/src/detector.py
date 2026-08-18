"""
Wrapper de inferencia sobre el modelo YOLO26 exportado a ONNX.

El .onnx exportado usa el formato "raw" (end2end=False): salida
(1, 4+nc, 8400). El dataset de entrenamiento (MathorNotV4, Roboflow)
tiene una única clase ("math"), por lo que nc=1 y la salida es
(1, 5, 8400). El NMS se aplica manualmente con cv2.dnn.NMSBoxes, ya
que no usamos la librería ultralytics en este servicio (RNF-01, RNF-03).
"""

import os
from dataclasses import dataclass
from typing import List

import cv2
import numpy as np
import onnxruntime as ort


@dataclass
class RawBox:
    x: float
    y: float
    ancho: float
    alto: float
    confidence_score: float


class YoloDetector:
    def __init__(
        self,
        model_path: str,
        img_size: int = 640,
        confidence_threshold: float = 0.5,
        nms_iou_threshold: float = 0.45,
    ):
        self.img_size = img_size
        self.confidence_threshold = confidence_threshold
        self.nms_iou_threshold = nms_iou_threshold

        # CPU-only por diseño: el portátil de despliegue no tiene GPU (RNF-05).
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    def _letterbox(self, image: np.ndarray):
        """
        Redimensiona manteniendo el aspect ratio y rellena el sobrante con
        gris (114,114,114) hasta obtener un cuadrado img_size x img_size.
        Devuelve el factor de escala y el padding aplicados, para poder
        deshacer la transformación sobre las cajas detectadas.
        """
        h, w = image.shape[:2]
        scale = min(self.img_size / h, self.img_size / w)
        new_h, new_w = int(round(h * scale)), int(round(w * scale))

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        pad_h, pad_w = self.img_size - new_h, self.img_size - new_w
        top, bottom = pad_h // 2, pad_h - pad_h // 2
        left, right = pad_w // 2, pad_w - pad_w // 2

        padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                     cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return padded, scale, left, top

    def _preprocess(self, image: np.ndarray):
        padded, scale, pad_x, pad_y = self._letterbox(image)
        img = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)           # HWC -> CHW
        img = np.expand_dims(img, axis=0)      # añadir dimensión de batch
        return np.ascontiguousarray(img), scale, pad_x, pad_y

    def detect(self, image_bytes: bytes) -> List[RawBox]:
        np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("No se ha podido decodificar la imagen recibida")

        input_tensor, scale, pad_x, pad_y = self._preprocess(image)

        outputs = self.session.run(None, {self.input_name: input_tensor})
        # (1, 9, 8400) -> (8400, 9), para iterar por predicción candidata
        predictions = outputs[0][0].transpose(1, 0)

        candidate_boxes = []
        candidate_scores = []

        for pred in predictions:
            box_xywh = pred[:4]
            class_scores = pred[4:]     # 5 valores: una por clase del dataset

            # Solo nos interesa la confianza máxima entre las 5 clases;
            # cuál de ellas gane es irrelevante para esta herramienta.
            class_id = int(np.argmax(class_scores))
            confidence = float(class_scores[class_id])

            if confidence < self.confidence_threshold:
                continue

            cx, cy, w, h = box_xywh
            x1 = cx - w / 2
            y1 = cy - h / 2

            candidate_boxes.append([float(x1), float(y1), float(w), float(h)])
            candidate_scores.append(confidence)

        if not candidate_boxes:
            return []

        # NMS class-agnostic: no separamos por clase antes de filtrar,
        # así que dos predicciones solapadas se fusionan en una aunque el
        # modelo les haya asignado clases distintas (ver docstring del módulo).
        indices = cv2.dnn.NMSBoxes(
            candidate_boxes, candidate_scores,
            score_threshold=self.confidence_threshold,
            nms_threshold=self.nms_iou_threshold,
        )

        boxes: List[RawBox] = []
        for i in np.array(indices).flatten():
            x, y, w, h = candidate_boxes[i]
            confidence = candidate_scores[i]

            # Deshacer el letterbox para volver a coordenadas de la imagen original
            x1 = (x - pad_x) / scale
            y1 = (y - pad_y) / scale
            x2 = (x + w - pad_x) / scale
            y2 = (y + h - pad_y) / scale

            boxes.append(RawBox(
                x=float(max(x1, 0.0)),
                y=float(max(y1, 0.0)),
                ancho=float(x2 - x1),
                alto=float(y2 - y1),
                confidence_score=float(confidence),
            ))

        return boxes


def load_detector() -> YoloDetector:
    model_path = os.environ.get("MODEL_PATH", "/app/model/weights.onnx")
    confidence_threshold = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.5"))
    return YoloDetector(model_path=model_path, confidence_threshold=confidence_threshold)