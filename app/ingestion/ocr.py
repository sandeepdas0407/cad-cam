import io

import pytesseract
from PIL import Image


class TesseractNotFoundError(RuntimeError):
    pass


def configure_tesseract(tesseract_cmd: str | None) -> None:
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def ocr_pixmap(pix, lang: str = "eng") -> str:
    """OCR a PyMuPDF Pixmap and return recognized text."""
    img_bytes = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_bytes))
    try:
        return pytesseract.image_to_string(image, lang=lang)
    except pytesseract.TesseractNotFoundError as e:
        raise TesseractNotFoundError(
            "Tesseract OCR engine not found. Install it (e.g. "
            "https://github.com/UB-Mannheim/tesseract/wiki) and set "
            "ocr.tesseract_cmd in config.yaml to its executable path."
        ) from e
