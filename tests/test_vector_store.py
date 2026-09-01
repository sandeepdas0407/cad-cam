from app.search import vector_store


def test_vector_search_returns_nearest_first(tmp_db_conn):
    conn = tmp_db_conn
    conn.execute("INSERT INTO documents (path, filename, doc_type) VALUES ('a', 'a.pdf', 'pdf')")
    conn.commit()
    doc_id = conn.execute("SELECT id FROM documents WHERE path='a'").fetchone()["id"]

    ids = []
    for i in range(3):
        cur = conn.execute(
            "INSERT INTO chunks (doc_id, chunk_index, text, source) VALUES (?, ?, 'x', 'text_layer')",
            (doc_id, i),
        )
        ids.append(cur.lastrowid)
    conn.commit()

    vector_store.upsert(conn, ids[0], [1.0, 0.0, 0.0])
    vector_store.upsert(conn, ids[1], [0.0, 1.0, 0.0])
    vector_store.upsert(conn, ids[2], [0.9, 0.1, 0.0])
    conn.commit()

    results = vector_store.search(conn, [1.0, 0.0, 0.0], None, top_k=3)
    ranked_ids = [r[0] for r in results]

    assert ranked_ids[0] == ids[0]
    assert ranked_ids[1] == ids[2]
    assert ranked_ids[2] == ids[1]


def test_vector_search_drops_results_below_min_score(tmp_db_conn):
    conn = tmp_db_conn
    conn.execute("INSERT INTO documents (path, filename, doc_type) VALUES ('a', 'a.pdf', 'pdf')")
    conn.commit()
    doc_id = conn.execute("SELECT id FROM documents WHERE path='a'").fetchone()["id"]

    ids = []
    for i in range(3):
        cur = conn.execute(
            "INSERT INTO chunks (doc_id, chunk_index, text, source) VALUES (?, ?, 'x', 'text_layer')",
            (doc_id, i),
        )
        ids.append(cur.lastrowid)
    conn.commit()

    vector_store.upsert(conn, ids[0], [1.0, 0.0, 0.0])  # cos = 1.0
    vector_store.upsert(conn, ids[1], [0.0, 1.0, 0.0])  # cos = 0.0
    vector_store.upsert(conn, ids[2], [0.9, 0.1, 0.0])  # cos ~ 0.994
    conn.commit()

    results = vector_store.search(conn, [1.0, 0.0, 0.0], None, top_k=3, min_score=0.5)
    ranked_ids = [r[0] for r in results]

    assert ranked_ids == [ids[0], ids[2]]
