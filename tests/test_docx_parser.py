from app.ingestion.docx_parser import parse_docx
from tests.conftest import FIXTURES


def test_docx_headings_and_table():
    doc = parse_docx(str(FIXTURES / "sample.docx"))
    headings = [p.section_heading for p in doc.pages]
    assert "Gearbox Assembly Notes" in headings
    assert "Torque Tolerances" in headings
    assert "Lubrication" in headings

    table_page = next(p for p in doc.pages if "Fastener" in p.text)
    assert table_page.section_heading == "Torque Tolerances"
    assert "M10 Shaft Retainer" in table_page.text
