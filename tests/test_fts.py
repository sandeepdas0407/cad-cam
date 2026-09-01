from app.search.fts import keyword_search


def _insert_chunk(conn, doc_id, text):
    cur = conn.execute(
        "INSERT INTO chunks (doc_id, chunk_index, text, source) VALUES (?, 0, ?, 'text_layer')",
        (doc_id, text),
    )
    conn.commit()
    return cur.lastrowid


def test_keyword_search_ranks_best_match_first(tmp_db_conn):
    conn = tmp_db_conn
    conn.execute("INSERT INTO documents (path, filename, doc_type) VALUES ('a', 'a.pdf', 'pdf')")
    conn.execute("INSERT INTO documents (path, filename, doc_type) VALUES ('b', 'b.pdf', 'pdf')")
    conn.commit()

    doc_a = conn.execute("SELECT id FROM documents WHERE path='a'").fetchone()["id"]
    doc_b = conn.execute("SELECT id FROM documents WHERE path='b'").fetchone()["id"]

    _insert_chunk(conn, doc_a, "torque torque torque specification for the mounting bolts")
    _insert_chunk(conn, doc_b, "the assembly mentions torque once in passing")

    results = keyword_search(conn, "torque", None, 10)
    assert len(results) == 2
    assert results[0][0] != results[1][0]


def test_keyword_search_matches_on_partial_term_overlap(tmp_db_conn):
    """A multi-word query should still surface a chunk that matches only some
    of the terms (OR semantics) rather than requiring every term verbatim —
    otherwise one misspelled/absent word (e.g. British vs. American spelling)
    zeroes out keyword results entirely."""
    conn = tmp_db_conn
    conn.execute("INSERT INTO documents (path, filename, doc_type) VALUES ('a', 'a.pdf', 'pdf')")
    conn.commit()
    doc_a = conn.execute("SELECT id FROM documents WHERE path='a'").fetchone()["id"]

    _insert_chunk(conn, doc_a, "Material: 6061-T6 Aluminum Alloy")

    results = keyword_search(conn, "aluminium alloy", None, 10)
    assert len(results) == 1


def test_keyword_search_doc_type_filter(tmp_db_conn):
    conn = tmp_db_conn
    conn.execute("INSERT INTO documents (path, filename, doc_type) VALUES ('a', 'a.pdf', 'pdf')")
    conn.execute("INSERT INTO documents (path, filename, doc_type) VALUES ('b', 'b.docx', 'docx')")
    conn.commit()
    doc_a = conn.execute("SELECT id FROM documents WHERE path='a'").fetchone()["id"]
    doc_b = conn.execute("SELECT id FROM documents WHERE path='b'").fetchone()["id"]

    _insert_chunk(conn, doc_a, "keyway tolerance spec")
    _insert_chunk(conn, doc_b, "keyway tolerance spec")

    results = keyword_search(conn, "keyway", "docx", 10)
    assert len(results) == 1
