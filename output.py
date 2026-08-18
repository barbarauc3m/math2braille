# DELETE FILE

import onnxruntime as ort
session = ort.InferenceSession("service/yolo/model/weights.onnx", providers=["CPUExecutionProvider"])
print("input:", session.get_inputs()[0].name, session.get_inputs()[0].shape)
print("output:", session.get_outputs()[0].name, session.get_outputs()[0].shape)