# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local FastAPI web app that indexes CAD/CAM PDFs (text and scanned) and Word documents from configured folders, then serves hybrid search (SQLite FTS5 keyword search + Voyage AI semantic search, combined via reciprocal rank fusion). Single-user, local-only — no auth, no multi-tenancy.

## Commands

```
venv\Scripts\activate
pip install -r requirements.txt                       # install deps (Python 3.11, venv already created)

venv\Scripts\python.exe -m uvicorn app.main:app --reload   # run the server (http://localhost:8000)
venv\Scripts\python.exe -m app.ingestion.pipeline           # CLI-only reindex, no server

venv\Scripts\python.exe -m pytest                      # run all tests
venv\Scripts\python.exe -m pytest tests/test_hybrid.py  # run a single test file
venv\Scripts\python.exe -m pytest tests/test_hybrid.py::test_name -v   # run a single test
```

Requires Tesseract OCR installed for scanned/image PDF pages (`ocr.tesseract_cmd` in `config.yaml`, default `C:\Program Files\Tesseract-OCR\tesseract.exe`). Without it, OCR-only PDF pages fail; keyword/semantic search over already-indexed text still works.

Semantic/hybrid search requires `VOYAGE_API_KEY` in `.env` (copy from `.env.example`). Without it, keyword search still works; the search API falls back to keyword-only for `type=hybrid` (with a `warning` in the response) and returns 400 for `type=semantic`.

## Architecture

**Pipeline (index-time), `app/ingestion/`:**
`walker.py` discovers files under `watched_folders` → `pdf_parser.py`/`docx_parser.py` parse into a `ParsedDocument` of `ParsedPage`s (`app/models.py`) → `chunker.py` splits each page's text into overlapping word-count-based `Chunk`s → `pipeline.py` orchestrates all of it, writes rows to SQLite, and (if a Voyage key is configured) embeds each chunk via `EmbeddingsClient` and stores the vector.

- PDF pages are classified per-page as `text_only` / `mixed` / `image_only` based on extracted text length and presence of images (`pdf_parser.classify_page`); `mixed`/`image_only` pages get OCR'd via `ocr.py` (Tesseract) and the page's `source` field records provenance (`text_layer` / `ocr` / `mixed`).
- `pipeline.run_pipeline` is incremental: it skips re-parsing a file whose size+mtime match what's stored, falls back to a SHA-256 comparison if only mtime changed, and deletes DB rows for files no longer present on disk. A module-level `STATUS` dict tracks progress and is polled by `GET /api/index/status`; reindex runs in a background thread (`app/api/routes_index.py`) guarded by a `threading.Lock` so only one run happens at a time.

**Storage, `app/search/db.py`:** single SQLite file (`data/index.db`, gitignored) with `documents`, `chunks`, an FTS5 virtual table `chunks_fts` (external-content, kept in sync with `chunks` via `AFTER INSERT`/`AFTER DELETE` triggers), and `chunk_vectors` (embeddings stored as raw float32 blobs, no vector extension — similarity search is a brute-force NumPy cosine scan over all rows in `vector_store.search`).

**Search (query-time), `app/api/routes_search.py`:** for `type=hybrid`, runs `fts.keyword_search` (BM25 via FTS5, sanitized/quoted-token query building in `_sanitize_query`) and `vector_store.search` (cosine similarity) independently, then merges their ranked chunk-id lists with `hybrid.reciprocal_rank_fusion` — scores from the two are never compared directly, only their ranks are. Snippets are built and `<mark>`-highlighted server-side in `_build_snippet`.

**Config, `app/config.py`:** `get_settings()` re-reads `config.yaml` (chunking/OCR/embedding/search tuning + `watched_folders`) on every call — no restart needed to pick up `watched_folders` changes — and merges in `VOYAGE_API_KEY` from `.env` via a `pydantic-settings` `Secrets` model. `watched_folders` entries are resolved to absolute paths as `watched_folders_resolved`.

**API surface (`app/api/`):** `routes_index.py` (`POST /api/reindex`, `GET /api/index/status`, `GET /api/folders`), `routes_search.py` (`GET /api/search`), `routes_files.py` (`GET /api/file/{doc_id}` raw file download, `GET /api/preview/{doc_id}/{page}` renders/caches a PDF page as PNG into `data/page_cache/` via PyMuPDF).

**Frontend:** server-rendered Jinja2 (`frontend/templates/index.html`) + vanilla JS (`frontend/static/js/search.js`) calling the JSON API — no build step, no framework.

## Notes

- `doc_type` filter values are `"pdf" | "docx" | "all"`, threaded through both keyword and vector search paths identically.
- Tests use real fixture files (`tests/fixtures/*.pdf`, `*.docx`) rather than mocks for parser/chunker/search tests; `tests/conftest.py` configures the real Tesseract path for OCR-dependent tests.
