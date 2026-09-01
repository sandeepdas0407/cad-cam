import sqlite3

import numpy as np


def to_blob(vector: list[float]) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def upsert(conn: sqlite3.Connection, chunk_id: int, vector: list[float]) -> None:
    arr = np.asarray(vector, dtype=np.float32)
    conn.execute(
        "INSERT OR REPLACE INTO chunk_vectors (chunk_id, embedding, dim) VALUES (?, ?, ?)",
        (chunk_id, arr.tobytes(), arr.shape[0]),
    )


def search(
    conn: sqlite3.Connection,
    query_vector: list[float],
    doc_type: str | None,
    top_k: int,
    min_score: float = 0.0,
) -> list[tuple[int, float]]:
    sql = """
        SELECT cv.chunk_id AS chunk_id, cv.embedding AS embedding
        FROM chunk_vectors cv
        JOIN chunks c ON c.id = cv.chunk_id
        JOIN documents d ON d.id = c.doc_id
    """
    params: list = []
    if doc_type and doc_type != "all":
        sql += " WHERE d.doc_type = ?"
        params.append(doc_type)

    rows = conn.execute(sql, params).fetchall()
    if not rows:
        return []

    chunk_ids = [row["chunk_id"] for row in rows]
    matrix = np.stack([from_blob(row["embedding"]) for row in rows])
    q = np.asarray(query_vector, dtype=np.float32)

    matrix_norms = np.linalg.norm(matrix, axis=1)
    q_norm = np.linalg.norm(q)
    denom = matrix_norms * q_norm
    denom[denom == 0] = 1e-10
    sims = (matrix @ q) / denom

    order = np.argsort(-sims)[:top_k]
    return [
        (chunk_ids[i], float(sims[i])) for i in order if sims[i] >= min_score
    ]
