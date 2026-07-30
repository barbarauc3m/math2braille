"""DTO de service/ocr."""

from pydantic import BaseModel


class OcrResponse(BaseModel):
    latex: str