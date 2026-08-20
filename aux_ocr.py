from pix2tex.cli import LatexOCR
from PIL import Image

model = LatexOCR()
img = Image.open("results/recortes/id1420_pg5_conf0.69.procesadaNO.png")
print(model(img))


import base64
import requests

with open("results/recortes/id1420_pg5_conf0.69.procesadaNO.png", "rb") as img_file:
    b64_string = base64.b64encode(img_file.read()).decode("utf-8")

response = requests.post(
    "https://lukas-blecher-latex-ocr.hf.space/api/predict",
    json={"data": [f"data:image/png;base64,{b64_string}"]},
)

latex_code = response.json()["data"][0]
print(latex_code)