import datetime
import sqlite3
from pathlib import Path

from app.ingestion.chunker import chunk_document
from app.ingestion.docx_parser import parse_docx
from app.ingestion.ocr import configure_tesseract
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.walker import discover_files, file_fingerprint, sha256_of
from app.search import db as db_mod
from app.search.embeddings import EmbeddingsClient
from app.search.vector_store import upsert as upsert_vector

STATUS = {
    "status": "idle",
    "files_processed": 0,
    "files_total": 0,
    "last_run_at": None,
    "errors": [],
}


def _get_or_create_doc_row(conn: sqlite3.Connection, path: Path, doc_type: str) -> int:
    row = conn.execute(
        "SELECT id FROM documents WHERE path = ?", (str(path),)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO documents (path, filename, doc_type) VALUES (?, ?, ?)",
        (str(path), path.name, doc_type),
    )
    conn.commit()
    return cur.lastrowid


def run_pipeline(config: dict, db_path: Path) -> dict:
    STATUS.update(status="running", files_processed=0, files_total=0, errors=[])

    ocr_cfg = config.get("ocr", {})
    configure_tesseract(ocr_cfg.get("tesseract_cmd"))

    chunking_cfg = config.get("chunking", {})
    embed_cfg = config.get("embeddings", {})
    api_key = config.get("voyage_api_key", "")

    embeddings_client = None
    if api_key:
        embeddings_client = EmbeddingsClient(
            api_key=api_key,
            model=embed_cfg.get("model", "voyage-3"),
            batch_size=embed_cfg.get("batch_size", 128),
        )

    conn = db_mod.init_db(db_path)

    folders = config.get("watched_folders_resolved", [])
    disk_files = discover_files(folders)
    disk_paths = {str(p) for p in disk_files}

    STATUS["files_total"] = len(disk_files)

    existing = {
        row["path"]: dict(row)
        for row in conn.execute(
            "SELECT id, path, size, mtime, sha256 FROM documents"
        ).fetchall()
    }

    for path in disk_files:
        try:
            doc_type = "pdf" if path.suffix.lower() == ".pdf" else "docx"
            size, mtime = file_fingerprint(path)
            prior = existing.get(str(path))

            needs_parse = True
            if prior and prior["size"] == size and prior["mtime"] == mtime:
                needs_parse = False
            elif prior:
                new_hash = sha256_of(path)
                if new_hash == prior["sha256"]:
                    needs_parse = False
                    conn.execute(
                        "UPDATE documents SET mtime = ? WHERE id = ?",
                        (mtime, prior["id"]),
                    )
                    conn.commit()

            doc_id = _get_or_create_doc_row(conn, path, doc_type)

            if needs_parse:
                if doc_type == "pdf":
                    parsed = parse_pdf(str(path), ocr_cfg)
                else:
                    parsed = parse_docx(str(path))

                chunks = chunk_document(
                    parsed,
                    doc_id,
                    target_tokens=chunking_cfg.get("target_tokens", 650),
                    overlap_ratio=chunking_cfg.get("overlap_ratio", 0.15),
                )

                db_mod.delete_chunks_for_doc(conn, doc_id)

                chunk_ids = []
                for chunk in chunks:
                    cur = conn.execute(
                        """INSERT INTO chunks
                           (doc_id, chunk_index, page_number, section_heading, text, source, char_start, char_end)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            chunk.doc_id,
                            chunk.chunk_index,
                            chunk.page_number,
                            chunk.section_heading,
                            chunk.text,
                            chunk.source,
                            chunk.char_start,
                            chunk.char_end,
                        ),
                    )
                    chunk_ids.append(cur.lastrowid)
                conn.commit()

                if embeddings_client and chunks:
                    texts = [c.text for c in chunks]
                    vectors = embeddings_client.embed_documents(texts)
                    for chunk_id, vector in zip(chunk_ids, vectors):
                        upsert_vector(conn, chunk_id, vector)
                    conn.commit()

                new_hash = sha256_of(path)
                sha = new_hash
                conn.execute(
                    """UPDATE documents
                       SET size = ?, mtime = ?, sha256 = ?, last_indexed_at = ?
                       WHERE id = ?""",
                    (size, mtime, sha, datetime.datetime.now().isoformat(), doc_id),
                )
                conn.commit()
            elif embeddings_client:
                # File is unchanged, but chunks may still be missing vectors —
                # e.g. embeddings were skipped/failed on a prior run because no
                # (working) API key was configured yet. Backfill without re-parsing.
                unembedded = conn.execute(
                    """SELECT c.id, c.text FROM chunks c
                       LEFT JOIN chunk_vectors cv ON cv.chunk_id = c.id
                       WHERE c.doc_id = ? AND cv.chunk_id IS NULL""",
                    (doc_id,),
                ).fetchall()
                if unembedded:
                    texts = [row["text"] for row in unembedded]
                    vectors = embeddings_client.embed_documents(texts)
                    for row, vector in zip(unembedded, vectors):
                        upsert_vector(conn, row["id"], vector)
                    conn.commit()

            STATUS["files_processed"] += 1
        except Exception as e:  # noqa: BLE001
            STATUS["errors"].append({"path": str(path), "error": str(e)})
            STATUS["files_processed"] += 1

    for path_str, row in existing.items():
        if path_str not in disk_paths:
            db_mod.delete_document(conn, row["id"])

    conn.close()

    STATUS["status"] = "done" if not STATUS["errors"] else "done_with_errors"
    STATUS["last_run_at"] = datetime.datetime.now().isoformat()
    return dict(STATUS)


def get_status() -> dict:
    return dict(STATUS)


if __name__ == "__main__":
    import json

    from app.config import DB_PATH, get_settings

    result = run_pipeline(get_settings(), DB_PATH)
    print(json.dumps(result, indent=2, default=str))
