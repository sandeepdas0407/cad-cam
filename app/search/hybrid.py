def reciprocal_rank_fusion(
    result_lists: list[list[tuple[int, float]]], k: int = 60
) -> list[tuple[int, float]]:
    """Each result_list is a ranked list of (chunk_id, score) — score is used
    only for ordering to derive rank, not combined directly (RRF avoids
    needing comparable score scales across BM25 and cosine similarity)."""
    scores: dict[int, float] = {}
    for results in result_lists:
        for rank, (chunk_id, _score) in enumerate(results, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return ranked
