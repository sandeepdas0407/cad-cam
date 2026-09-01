# CAD-CAM Document Search

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC.svg)](#tests)

Local web app for searching CAD/CAM PDFs (text and scanned) and Word documents, combining full-text keyword search with Voyage AI semantic search.

## Setup

1. **Python**: this project targets Python 3.11. A venv is already created at `venv/`.
   ```
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Tesseract OCR** (required for scanned/image PDF pages): install from
   https://github.com/UB-Mannheim/tesseract/wiki (or `winget install --id UB-Mannheim.TesseractOCR -e`).
   Default install path `C:\Program Files\Tesseract-OCR\tesseract.exe` is already set in `config.yaml` (`ocr.tesseract_cmd`).

3. **Voyage API key** (required for semantic/hybrid search): copy `.env.example` to `.env` and set `VOYAGE_API_KEY`.
   Get a key at https://www.voyageai.com/. Without a key, keyword search still works; semantic/hybrid search will error.

4. **Configure folders to index**: edit `watched_folders` in `config.yaml`. Defaults to `./sample_docs`.

## Running

```
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://localhost:8000, click **Reindex**, then search.

CLI-only reindex (no server): `venv\Scripts\python.exe -m app.ingestion.pipeline`

## Tests

```
venv\Scripts\python.exe -m pytest
```

## Known limitations (v1)

- Embedded images inside .docx files are not OCR'd (only scanned/image PDF pages are).
- Watched folders are edited via `config.yaml`, no in-app settings UI.
- Re-indexing is manual (no background file watcher).
