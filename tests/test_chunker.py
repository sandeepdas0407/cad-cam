from app.ingestion.chunker import chunk_document
from app.models import ParsedDocument, ParsedPage


def test_chunk_respects_target_size_and_overlap():
    text = " ".join(f"word{i}" for i in range(200))
    doc = ParsedDocument(
        path="x", doc_type="pdf", pages=[ParsedPage(page_number=1, text=text, source="text_layer")]
    )
    chunks = chunk_document(doc, doc_id=1, target_tokens=50, overlap_ratio=0.2)

    assert len(chunks) > 1
    for c in chunks:
        word_count = len(c.text.split())
        assert word_count <= 51  # target + slack for boundary rounding

    # verify overlap: end of chunk 0 and start of chunk 1 share words
    # (overlap window is ~10 words given target_tokens=50, overlap_ratio=0.2)
    words0 = chunks[0].text.split()
    words1 = chunks[1].text.split()
    assert set(words0[-10:]) & set(words1[:10])


def test_chunk_empty_page_produces_no_chunks():
    doc = ParsedDocument(
        path="x", doc_type="pdf", pages=[ParsedPage(page_number=1, text="   ", source="text_layer")]
    )
    chunks = chunk_document(doc, doc_id=1)
    assert chunks == []
