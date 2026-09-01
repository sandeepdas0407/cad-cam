from pathlib import Path

import pytest

from app.ingestion.pdf_parser import classify_page, parse_pdf
from tests.conftest import FIXTURES, tesseract_available


def test_classify_page():
    assert classify_page("short", has_images=False, min_text_chars=20) == "image_only"
    assert classify_page("a" * 50, has_images=False, min_text_chars=20) == "text_only"
    assert classify_page("a" * 50, has_images=True, min_text_chars=20) == "mixed"


def test_text_pdf_extracts_real_text(ocr_cfg):
    doc = parse_pdf(str(FIXTURES / "sample_text.pdf"), ocr_cfg)
    assert len(doc.pages) == 1
    page = doc.pages[0]
    assert page.source == "text_layer"
    assert "MOTOR MOUNT" in page.text
    assert "Torque" in page.text


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract not installed")
def test_scanned_pdf_is_ocrd(ocr_cfg):
    doc = parse_pdf(str(FIXTURES / "sample_scanned.pdf"), ocr_cfg)
    assert len(doc.pages) == 1
    page = doc.pages[0]
    assert page.source == "ocr"
    assert "KEYWAY" in page.text.upper()


@pytest.mark.skipif(not tesseract_available(), reason="Tesseract not installed")
def test_mixed_pdf_keeps_both_text_and_ocr(ocr_cfg):
    doc = parse_pdf(str(FIXTURES / "sample_mixed.pdf"), ocr_cfg)
    assert len(doc.pages) == 1
    page = doc.pages[0]
    assert page.source == "mixed"
    assert "Drawing No" in page.text  # from the real text layer
    assert "BEND RADIUS" in page.text.upper()  # from OCR of the embedded image
