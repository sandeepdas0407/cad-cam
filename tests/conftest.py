import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

TESSERACT_CMD = "C:/Program Files/Tesseract-OCR/tesseract.exe"


@pytest.fixture(scope="session")
def ocr_cfg():
    return {
        "tesseract_cmd": TESSERACT_CMD,
        "dpi": 300,
        "lang": "eng",
        "min_text_chars_threshold": 20,
    }


@pytest.fixture(scope="session", autouse=True)
def configure_ocr(ocr_cfg):
    from app.ingestion.ocr import configure_tesseract

    configure_tesseract(ocr_cfg["tesseract_cmd"])


@pytest.fixture
def tmp_db_path(tmp_path):
    return tmp_path / "test_index.db"


@pytest.fixture
def tmp_db_conn(tmp_db_path):
    from app.search.db import init_db

    conn = init_db(tmp_db_path)
    yield conn
    conn.close()


def tesseract_available() -> bool:
    return Path(TESSERACT_CMD).exists()
