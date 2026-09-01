import voyageai.error
from fastapi.testclient import TestClient

from app.main import app
from app.search.db import init_db
from app.search.embeddings import EmbeddingsClient


def _seed_db(db_path):
    conn = init_db(db_path)
    conn.execute(
        "INSERT INTO documents (path, filename, doc_type) VALUES (?, ?, ?)",
        (str(db_path.parent / "widget.pdf"), "widget.pdf", "pdf"),
    )
    conn.commit()
    doc_id = conn.execute("SELECT id FROM documents").fetchone()["id"]
    conn.execute(
        """INSERT INTO chunks (doc_id, chunk_index, page_number, text, source)
           VALUES (?, 0, 1, ?, 'text_layer')""",
        (doc_id, "The widget bracket requires a torque of 12 Nm on all fasteners."),
    )
    conn.commit()
    conn.close()


def test_keyword_search_endpoint(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)

    monkeypatch.setattr("app.api.routes_search.DB_PATH", db_path)

    client = TestClient(app)
    resp = client.get("/api/search", params={"q": "torque", "type": "keyword"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["filename"] == "widget.pdf"
    assert "<mark>" in data["results"][0]["snippet_html"]


def test_semantic_search_without_api_key_returns_400(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)
    monkeypatch.setattr("app.api.routes_search.DB_PATH", db_path)

    def fake_settings():
        return {
            "search": {"fts_top_k": 50, "vector_top_k": 50, "rrf_k": 60, "results_limit": 20},
            "voyage_api_key": "",
        }

    monkeypatch.setattr("app.api.routes_search.get_settings", fake_settings)

    client = TestClient(app)
    resp = client.get("/api/search", params={"q": "torque", "type": "semantic"})
    assert resp.status_code == 400


def _break_embed_query(monkeypatch):
    def fake_settings():
        return {
            "search": {"fts_top_k": 50, "vector_top_k": 50, "rrf_k": 60, "results_limit": 20},
            "embeddings": {"model": "voyage-3", "batch_size": 128},
            "voyage_api_key": "bad-key",
        }

    monkeypatch.setattr("app.api.routes_search.get_settings", fake_settings)

    def fake_embed_query(self, text):
        raise voyageai.error.AuthenticationError("This API key cannot access this endpoint.")

    monkeypatch.setattr(EmbeddingsClient, "embed_query", fake_embed_query)


def test_hybrid_search_falls_back_to_keyword_when_embeddings_fail(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)
    monkeypatch.setattr("app.api.routes_search.DB_PATH", db_path)
    _break_embed_query(monkeypatch)

    client = TestClient(app)
    resp = client.get("/api/search", params={"q": "torque", "type": "hybrid"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert "warning" in data


def test_semantic_search_embeddings_failure_returns_502(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)
    monkeypatch.setattr("app.api.routes_search.DB_PATH", db_path)
    _break_embed_query(monkeypatch)

    client = TestClient(app)
    resp = client.get("/api/search", params={"q": "torque", "type": "semantic"})
    assert resp.status_code == 502
