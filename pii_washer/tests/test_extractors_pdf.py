import io

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pii_washer.extractors.pdf import PdfExtractor


# === Helpers ===


def _make_pdf(pages: list[list[str]]) -> bytes:
    """Build a PDF in memory and return raw bytes.

    Args:
        pages: A list of pages; each page is a list of text strings to draw,
               one per line, starting near the top of the page.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for page_lines in pages:
        y = 750
        for line in page_lines:
            c.drawString(72, y, line)
            y -= 20
        c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def extractor():
    return PdfExtractor()


# === Happy path ===


def test_returns_string_type(extractor):
    content = _make_pdf([["Hello world"]])
    result = extractor.extract(content, "test.pdf")
    assert isinstance(result, str)


def test_single_page_extraction(extractor):
    content = _make_pdf([["Jane Doe called (555) 123-4567 yesterday."]])
    result = extractor.extract(content, "test.pdf")
    assert "Jane Doe" in result
    assert "555" in result


def test_multi_page_extraction(extractor):
    content = _make_pdf([
        ["First page content."],
        ["Second page content."],
    ])
    result = extractor.extract(content, "multi.pdf")
    assert "First page content." in result
    assert "Second page content." in result


# === Error handling ===


def test_corrupted_file_raises_value_error(extractor):
    garbage = b"This is not a valid PDF \x00\x01\x02"
    with pytest.raises(ValueError, match="could not be read"):
        extractor.extract(garbage, "bad.pdf")


def test_empty_pdf_raises_value_error(extractor):
    """A PDF with a page that has no text should raise ValueError."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    # Add a page with no text content
    c.showPage()
    c.save()
    buf.seek(0)
    content = buf.getvalue()
    with pytest.raises(ValueError, match="No text content"):
        extractor.extract(content, "empty.pdf")
