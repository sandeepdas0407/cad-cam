import shutil

import pytest

from app.ingestion.pipeline import run_pipeline
from app.search.embeddings import EmbeddingsClient

FIXTURES = __import__("pathlib").Path(__file__).parent / "fixtures"


class FakeEmbeddingsClient:
    def __init__(self, *args, **kwargs):
        pass

    def embed_documents(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _config(folders, api_key=""):
    return {
        "watched_folders_resolved": folders,
        "ocr": {},
        "chunking": {"target_tokens": 650, "overlap_ratio": 0.15},
        "embeddings": {"model": "voyage-3", "batch_size": 128},
        "voyage_api_key": api_key,
    }


@pytest.fixture
def watched_folder(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    shutil.copy(FIXTURES / "sample.docx", folder / "sample.docx")
    return folder


def test_reindex_backfills_embeddings_for_unchanged_files(tmp_path, watched_folder, monkeypatch):
    """A file indexed before a Voyage key was configured must get embeddings
    filled in on a later reindex, even though the file itself hasn't changed
    (this was the bug: unchanged files were skipped entirely, leaving them
    permanently unembedded once a key was added)."""
    monkeypatch.setattr("app.ingestion.pipeline.EmbeddingsClient", FakeEmbeddingsClient)
    db_path = tmp_path / "index.db"

    # First run: no API key, mirrors indexing before VOYAGE_API_KEY was set.
    result1 = run_pipeline(_config([watched_folder], api_key=""), db_path)
    assert result1["errors"] == []

    import sqlite3

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT count(*) FROM chunks").fetchone()[0] > 0
    assert conn.execute("SELECT count(*) FROM chunk_vectors").fetchone()[0] == 0
    conn.close()

    # Second run: key now configured, file on disk is untouched.
    monkeypatch.setattr("app.ingestion.pipeline.parse_docx", lambda path: (_ for _ in ()).throw(
        AssertionError("should not re-parse an unchanged file")
    ))
    result2 = run_pipeline(_config([watched_folder], api_key="pa-fake-key"), db_path)
    assert result2["errors"] == []

    conn = sqlite3.connect(db_path)
    chunk_count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    vector_count = conn.execute("SELECT count(*) FROM chunk_vectors").fetchone()[0]
    conn.close()

    assert vector_count == chunk_count
    assert vector_count > 0
