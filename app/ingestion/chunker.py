from app.models import Chunk, ParsedDocument


def _split_words_with_offsets(text: str) -> list[tuple[str, int, int]]:
    words = []
    i = 0
    n = len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        start = i
        while i < n and not text[i].isspace():
            i += 1
        if i > start:
            words.append((text[start:i], start, i))
    return words


def chunk_document(
    doc: ParsedDocument,
    doc_id: int,
    target_tokens: int = 650,
    overlap_ratio: float = 0.15,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_index = 0
    overlap_words = max(1, int(target_tokens * overlap_ratio))

    for page in doc.pages:
        words = _split_words_with_offsets(page.text)
        if not words:
            continue

        start_idx = 0
        while start_idx < len(words):
            end_idx = min(start_idx + target_tokens, len(words))
            chunk_words = words[start_idx:end_idx]
            char_start = chunk_words[0][1]
            char_end = chunk_words[-1][2]
            chunk_text = page.text[char_start:char_end]

            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    page_number=page.page_number,
                    section_heading=page.section_heading,
                    source=page.source,
                    char_start=char_start,
                    char_end=char_end,
                )
            )
            chunk_index += 1

            if end_idx >= len(words):
                break
            start_idx = end_idx - overlap_words

    return chunks
