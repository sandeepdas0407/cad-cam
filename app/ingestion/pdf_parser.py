import fitz  # PyMuPDF

from app.ingestion.ocr import ocr_pixmap
from app.models import ParsedDocument, ParsedPage


def classify_page(text: str, has_images: bool, min_text_chars: int) -> str:
    stripped = text.strip()
    if len(stripped) < min_text_chars:
        return "image_only"
    if has_images:
        return "mixed"
    return "text_only"


def parse_pdf(path: str, ocr_cfg: dict) -> ParsedDocument:
    doc = ParsedDocument(path=path, doc_type="pdf")
    min_text_chars = ocr_cfg.get("min_text_chars_threshold", 20)
    dpi = ocr_cfg.get("dpi", 300)
    lang = ocr_cfg.get("lang", "eng")

    with fitz.open(path) as pdf:
        for i, page in enumerate(pdf, start=1):
            text = page.get_text("text") or ""
            has_images = len(page.get_images()) > 0
            page_class = classify_page(text, has_images, min_text_chars)

            if page_class == "text_only":
                doc.pages.append(
                    ParsedPage(page_number=i, text=text, source="text_layer")
                )
                continue

            pix = page.get_pixmap(dpi=dpi)
            ocr_text = ocr_pixmap(pix, lang=lang)

            if page_class == "image_only":
                combined = ocr_text
                source = "ocr"
            else:  # mixed
                combined = f"{text}\n{ocr_text}"
                source = "mixed"

            doc.pages.append(
                ParsedPage(page_number=i, text=combined, source=source)
            )

    return doc
