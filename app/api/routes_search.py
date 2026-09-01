import html
import re

import voyageai.error
from fastapi import APIRouter, HTTPException, Query

from app.config import DB_PATH, get_settings
from app.search import fts as fts_mod
from app.search import vector_store
from app.search.db import get_connection
from app.search.embeddings import EmbeddingsClient
from app.search.hybrid import reciprocal_rank_fusion

router = APIRouter()


def _clean_error_message(e: voyageai.error.VoyageError) -> str:
    """voyageai.error.APIError's default __str__ dumps the raw HTTP body/headers
    for non-4xx-mapped status codes; prefer the API's own "detail" field."""
    json_body = getattr(e, "json_body", None)
    if isinstance(json_body, dict) and json_body.get("detail"):
        return str(json_body["detail"])
    return str(e)


def _build_snippet(text: str, query: str, window: int = 90) -> str:
    tokens = [t for t in re.split(r"\s+", query.strip()) if t]
    lower_text = text.lower()
    pos = -1
    for t in tokens:
        idx = lower_text.find(t.lower())
        if idx != -1:
            pos = idx
            break

    if pos == -1:
        snippet = text[: window * 2]
    else:
        start = max(0, pos - window)
        end = min(len(text), pos + window)
        snippet = text[start:end]

    escaped = html.escape(snippet)
    for t in tokens:
        if not t:
            continue
        pattern = re.compile(re.escape(html.escape(t)), re.IGNORECASE)
        escaped = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped)
    return escaped


@router.get("/api/search")
def search(
    q: str = Query(..., min_length=1),
    type: str = Query("hybrid", pattern="^(hybrid|keyword|semantic)$"),
    doc_type: str = Query("all"),
    limit: int = Query(20, ge=1, le=100),
):
    config = get_settings()
    search_cfg = config.get("search", {})
    conn = get_connection(DB_PATH)

    keyword_results: list[tuple[int, float]] = []
    vector_results: list[tuple[int, float]] = []
    warning: str | None = None

    if type in ("hybrid", "keyword"):
        keyword_results = fts_mod.keyword_search(
            conn, q, doc_type, search_cfg.get("fts_top_k", 50)
        )

    if type in ("hybrid", "semantic"):
        api_key = config.get("voyage_api_key", "")
        if not api_key:
            if type == "semantic":
                conn.close()
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Semantic search requires a VOYAGE_API_KEY. Set it in .env "
                        "and restart the server, or use type=keyword instead."
                    ),
                )
            warning = (
                "VOYAGE_API_KEY is not configured — showing keyword-only results. "
                "Set it in .env to enable semantic search."
            )
        else:
            embed_cfg = config.get("embeddings", {})
            client = EmbeddingsClient(
                api_key=api_key,
                model=embed_cfg.get("model", "voyage-3"),
                batch_size=embed_cfg.get("batch_size", 128),
            )
            try:
                query_vector = client.embed_query(q)
                vector_results = vector_store.search(
                    conn,
                    query_vector,
                    doc_type,
                    search_cfg.get("vector_top_k", 50),
                    min_score=search_cfg.get("min_vector_score", 0.0),
                )
            except voyageai.error.VoyageError as e:
                reason = _clean_error_message(e)
                if type == "semantic":
                    conn.close()
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            f"Semantic search failed: {reason} Check VOYAGE_API_KEY in "
                            ".env, or use type=keyword instead."
                        ),
                    )
                warning = (
                    f"Semantic search is unavailable ({reason}) — showing keyword-only "
                    "results."
                )

    if type == "hybrid":
        ranked = reciprocal_rank_fusion(
            [keyword_results, vector_results], k=search_cfg.get("rrf_k", 60)
        )
    elif type == "keyword":
        ranked = keyword_results
    else:
        ranked = vector_results

    ranked = ranked[: limit or search_cfg.get("results_limit", 20)]

    results = []
    for chunk_id, score in ranked:
        row = conn.execute(
            """
            SELECT c.id AS chunk_id, c.text, c.page_number, c.section_heading, c.source,
                   d.id AS doc_id, d.filename, d.path, d.doc_type
            FROM chunks c JOIN documents d ON d.id = c.doc_id
            WHERE c.id = ?
            """,
            (chunk_id,),
        ).fetchone()
        if not row:
            continue
        results.append(
            {
                "doc_id": row["doc_id"],
                "filename": row["filename"],
                "path": row["path"],
                "doc_type": row["doc_type"],
                "page_number": row["page_number"],
                "section_heading": row["section_heading"],
                "snippet_html": _build_snippet(row["text"], q),
                "score": score,
                "chunk_id": row["chunk_id"],
                "source": row["source"],
            }
        )

    conn.close()
    response = {"query": q, "type": type, "results": results}
    if warning:
        response["warning"] = warning
    return response
