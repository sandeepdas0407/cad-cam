import re
import sqlite3

_FTS_SPECIAL = re.compile(r'["*^]')


def _sanitize_query(q: str) -> str:
    """Build a simple FTS5 MATCH expression: quote each token and OR them,
    avoiding FTS5 query-syntax errors from user-typed punctuation.

    OR (not AND) so a single missing/misspelled term doesn't zero out the whole
    keyword leg — bm25() ranking already rewards chunks matching more terms, and
    the hybrid RRF fusion needs this leg's signal even on a partial match (e.g. a
    spelling variant like "aluminium" vs "aluminum" would otherwise leave hybrid
    ranking entirely to the semantic leg, which can rank a topically-similar but
    factually wrong chunk above a chunk with a literal partial-term match)."""
    tokens = [t for t in re.split(r"\s+", q.strip()) if t]
    tokens = [_FTS_SPECIAL.sub("", t) for t in tokens]
    tokens = [t for t in tokens if t]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in tokens)


def keyword_search(
    conn: sqlite3.Connection, query: str, doc_type: str | None, top_k: int
) -> list[tuple[int, float]]:
    """Returns list of (chunk_id, bm25_score) — lower bm25() is better, so we
    return negated score so higher is better, consistent with vector search."""
    fts_query = _sanitize_query(query)
    if not fts_query:
        return []

    sql = """
        SELECT c.id AS chunk_id, bm25(chunks_fts) AS rank
        FROM chunks_fts
        JOIN chunks c ON c.id = chunks_fts.rowid
        JOIN documents d ON d.id = c.doc_id
        WHERE chunks_fts MATCH ?
    """
    params: list = [fts_query]
    if doc_type and doc_type != "all":
        sql += " AND d.doc_type = ?"
        params.append(doc_type)
    sql += " ORDER BY rank LIMIT ?"
    params.append(top_k)

    rows = conn.execute(sql, params).fetchall()
    return [(row["chunk_id"], -row["rank"]) for row in rows]
