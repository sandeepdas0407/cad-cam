from app.search.hybrid import reciprocal_rank_fusion


def test_rrf_favors_items_ranked_high_in_both_lists():
    keyword = [(1, 10.0), (2, 5.0), (3, 1.0)]
    vector = [(2, 0.9), (1, 0.5), (4, 0.1)]

    ranked = reciprocal_rank_fusion([keyword, vector], k=60)
    ranked_ids = [r[0] for r in ranked]

    assert ranked_ids[0] in (1, 2)  # both appear near the top of both lists
    assert set(ranked_ids) == {1, 2, 3, 4}


def test_rrf_handles_empty_list():
    ranked = reciprocal_rank_fusion([[], [(1, 0.5)]], k=60)
    assert ranked == [(1, 1 / 61)]
