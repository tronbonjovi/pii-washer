import pytest

from pii_washer.extractors.html import HtmlExtractor


@pytest.fixture
def extractor():
    return HtmlExtractor()


# === Happy path ===


def test_returns_string_type(extractor):
    content = b"<html><body><p>Hello world.</p></body></html>"
    result = extractor.extract(content, "test.html")
    assert isinstance(result, str)


def test_paragraph_extraction(extractor):
    """Text inside <p> tags is extracted."""
    content = b"<html><body><p>John Smith called today.</p></body></html>"
    result = extractor.extract(content, "test.html")
    assert "John Smith called today." in result


def test_paragraph_breaks_preserved(extractor):
    """Multiple <p> tags are separated by double newlines."""
    content = b"<html><body><p>First paragraph.</p><p>Second paragraph.</p></body></html>"
    result = extractor.extract(content, "test.html")
    assert "First paragraph." in result
    assert "Second paragraph." in result
    assert "\n\n" in result


def test_heading_extraction(extractor):
    """Headings (h1-h6) are extracted as text."""
    content = b"<html><body><h1>Report Title</h1><p>Body text.</p></body></html>"
    result = extractor.extract(content, "test.html")
    assert "Report Title" in result
    assert "Body text." in result


def test_unordered_list_extraction(extractor):
    """Unordered list items are extracted with dash prefix."""
    content = b"<html><body><ul><li>Alice</li><li>Bob</li></ul></body></html>"
    result = extractor.extract(content, "test.html")
    assert "- Alice" in result
    assert "- Bob" in result


def test_ordered_list_extraction(extractor):
    """Ordered list items are extracted with number prefix."""
    content = b"<html><body><ol><li>First item</li><li>Second item</li></ol></body></html>"
    result = extractor.extract(content, "test.html")
    assert "1. First item" in result
    assert "2. Second item" in result


def test_table_extraction(extractor):
    """Tables are extracted as pipe-delimited rows."""
    content = b"""
    <html><body>
    <table>
      <tr><th>Name</th><th>Email</th></tr>
      <tr><td>John Smith</td><td>john@example.com</td></tr>
    </table>
    </body></html>
    """
    result = extractor.extract(content, "test.html")
    assert "| Name | Email |" in result
    assert "| John Smith | john@example.com |" in result


def test_scripts_stripped(extractor):
    """<script> tags and their content are removed."""
    content = b"<html><body><script>alert('xss');</script><p>Real content.</p></body></html>"
    result = extractor.extract(content, "test.html")
    assert "alert" not in result
    assert "Real content." in result


def test_styles_stripped(extractor):
    """<style> tags and their content are removed."""
    content = b"<html><head><style>body { color: red; }</style></head><body><p>Text.</p></body></html>"
    result = extractor.extract(content, "test.html")
    assert "color" not in result
    assert "Text." in result


def test_br_converted_to_newline(extractor):
    """<br> tags are converted to newlines."""
    content = b"<html><body><p>Line one.<br>Line two.</p></body></html>"
    result = extractor.extract(content, "test.html")
    assert "Line one." in result
    assert "Line two." in result
    assert "\n" in result


def test_bytes_input(extractor):
    """Accepts bytes and decodes correctly."""
    content = "<html><body><p>Jane Doe called (555) 123-4567.</p></body></html>".encode("utf-8")
    result = extractor.extract(content, "test.html")
    assert "Jane Doe" in result


def test_noscript_stripped(extractor):
    """<noscript> tags and their content are removed."""
    content = b"<html><body><noscript>Enable JS</noscript><p>Content.</p></body></html>"
    result = extractor.extract(content, "test.html")
    assert "Enable JS" not in result
    assert "Content." in result


def test_div_content_extracted(extractor):
    """Content inside <div> is extracted."""
    content = b"<html><body><div>Some div content.</div></body></html>"
    result = extractor.extract(content, "test.html")
    assert "Some div content." in result


def test_multiple_paragraphs_double_newline_separated(extractor):
    """Three paragraphs each separated by \\n\\n."""
    content = b"<p>Para one.</p><p>Para two.</p><p>Para three.</p>"
    result = extractor.extract(content, "test.html")
    blocks = [b.strip() for b in result.split("\n\n") if b.strip()]
    assert len(blocks) >= 3


# === Error handling ===


def test_empty_html_raises_value_error(extractor):
    """HTML with no visible text content raises ValueError."""
    with pytest.raises(ValueError, match="No text content"):
        extractor.extract(b"<html><body></body></html>", "empty.html")


def test_empty_bytes_raises_value_error(extractor):
    """Completely empty bytes raises ValueError."""
    with pytest.raises(ValueError, match="No text content"):
        extractor.extract(b"", "empty.html")


def test_script_only_raises_value_error(extractor):
    """HTML containing only script tags (no visible text) raises ValueError."""
    with pytest.raises(ValueError, match="No text content"):
        extractor.extract(b"<html><body><script>var x = 1;</script></body></html>", "script_only.html")
