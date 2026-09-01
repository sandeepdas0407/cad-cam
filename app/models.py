from dataclasses import dataclass, field


@dataclass
class ParsedPage:
    page_number: int | None
    text: str
    source: str  # "text_layer" | "ocr" | "mixed"
    section_heading: str | None = None


@dataclass
class ParsedDocument:
    path: str
    doc_type: str  # "pdf" | "docx"
    pages: list[ParsedPage] = field(default_factory=list)


@dataclass
class Chunk:
    doc_id: int
    chunk_index: int
    text: str
    page_number: int | None
    section_heading: str | None
    source: str
    char_start: int
    char_end: int


@dataclass
class SearchResult:
    doc_id: int
    filename: str
    path: str
    doc_type: str
    page_number: int | None
    section_heading: str | None
    snippet_html: str
    score: float
    chunk_id: int
    source: str
