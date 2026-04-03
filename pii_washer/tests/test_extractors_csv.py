import pytest

from pii_washer.extractors.csv_ext import CsvExtractor


@pytest.fixture
def extractor():
    return CsvExtractor()


# === Happy path ===


def test_returns_string_type(extractor):
    content = b"Name,Email\nJohn Smith,john@example.com\n"
    result = extractor.extract(content, "test.csv")
    assert isinstance(result, str)


def test_simple_extraction(extractor):
    """Name/Email rows produce pipe-delimited output."""
    content = b"Name,Email\nJohn Smith,john@example.com\n"
    result = extractor.extract(content, "test.csv")
    assert "| Name | Email |" in result
    assert "| John Smith | john@example.com |" in result


def test_header_row_preserved(extractor):
    """The header row appears first in the output."""
    content = b"First,Last,Phone\nAlice,Smith,555-1234\n"
    result = extractor.extract(content, "test.csv")
    lines = result.splitlines()
    assert lines[0] == "| First | Last | Phone |"
    assert lines[1] == "| Alice | Smith | 555-1234 |"


def test_quoted_fields_with_commas(extractor):
    """Quoted fields containing commas are treated as a single cell."""
    content = b'Name,Address\n"Smith, John","123 Main St, Springfield"\n'
    result = extractor.extract(content, "test.csv")
    assert "| Smith, John | 123 Main St, Springfield |" in result


def test_empty_rows_skipped(extractor):
    """Blank lines in the CSV do not appear in the output."""
    content = b"Name,Email\n\nJohn,john@example.com\n\n"
    result = extractor.extract(content, "test.csv")
    lines = [l for l in result.splitlines() if l]
    assert len(lines) == 2


def test_header_only_csv_extracts_header(extractor):
    """A CSV with only a header row still returns that row."""
    content = b"Name,Email,Phone\n"
    result = extractor.extract(content, "header_only.csv")
    assert "| Name | Email | Phone |" in result


def test_latin1_encoding_fallback(extractor):
    """Files that are not valid UTF-8 fall back to latin-1 decoding."""
    # Build a CSV with a latin-1 encoded name (accented character)
    row = "Name,City\nJos\xe9,Lyon\n"
    content = row.encode("latin-1")
    result = extractor.extract(content, "latin.csv")
    assert "Jos" in result
    assert "Lyon" in result


# === Error handling ===


def test_empty_csv_raises_value_error(extractor):
    with pytest.raises(ValueError, match="No text content"):
        extractor.extract(b"", "empty.csv")


def test_whitespace_only_csv_raises_value_error(extractor):
    """A CSV with only blank lines is treated as empty."""
    with pytest.raises(ValueError, match="No text content"):
        extractor.extract(b"\n\n\n", "blank.csv")
