import voyageai


class EmbeddingsClient:
    def __init__(self, api_key: str, model: str = "voyage-3", batch_size: int = 128):
        if not api_key:
            raise ValueError(
                "VOYAGE_API_KEY is not set. Add it to .env before running "
                "the indexer (semantic search requires it)."
            )
        self.client = voyageai.Client(api_key=api_key)
        self.model = model
        self.batch_size = batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            resp = self.client.embed(batch, model=self.model, input_type="document")
            results.extend(resp.embeddings)
        return results

    def embed_query(self, text: str) -> list[float]:
        resp = self.client.embed([text], model=self.model, input_type="query")
        return resp.embeddings[0]
