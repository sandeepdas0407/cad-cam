from pathlib import Path

import fitz
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app.config import DB_PATH, PAGE_CACHE_DIR
from app.search.db import get_connection

router = APIRouter()


def _get_doc_path(doc_id: int) -> Path:
    conn = get_connection(DB_PATH)
    row = conn.execute("SELECT path FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(row["path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File no longer exists on disk")
    return path


@router.get("/api/file/{doc_id}")
def get_file(doc_id: int, page: int | None = Query(default=None)):
    path = _get_doc_path(doc_id)
    return FileResponse(path, filename=path.name)


@router.get("/api/preview/{doc_id}/{page}")
def get_preview(doc_id: int, page: int):
    path = _get_doc_path(doc_id)
    if path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Preview only supported for PDFs")

    cache_path = PAGE_CACHE_DIR / f"{doc_id}_{page}.png"
    if cache_path.exists():
        return FileResponse(cache_path, media_type="image/png")

    with fitz.open(path) as pdf:
        if page < 1 or page > len(pdf):
            raise HTTPException(status_code=404, detail="Page out of range")
        pix = pdf[page - 1].get_pixmap(dpi=150)
        pix.save(str(cache_path))

    return FileResponse(cache_path, media_type="image/png")
