import pytest

from pii_washer.document_loader import DocumentLoader


def create_test_file(tmp_path, filename, content, encoding="utf-8"):
    """Write a test file and return its path."""
    filepath = tmp_path / filename
    filepath.write_bytes(content.encode(encoding) if isinstance(content, str) else content)
    return str(filepath)


@pytest.fixture
def loader():
    return DocumentLoader()


# === Loading Files — Happy Path ===


def test_load_txt_file(loader, tmp_path):
    path = create_test_file(tmp_path, "test.txt", "Hello, this is a test document.")
    result = loader.load_file(path)
    assert result["text"] == "Hello, this is a test document."
    assert result["source_format"] == ".txt"
    assert result["filename"] == "test.txt"


def test_load_md_file(loader, tmp_path):
    content = "# Heading\n\nSome **bold** text."
    path = create_test_file(tmp_path, "test.md", content)
    result = loader.load_file(path)
    assert result["text"] == "# Heading\n\nSome **bold** text."
    assert result["source_format"] == ".md"


def test_load_file_case_insensitive_extension(loader, tmp_path):
    path = create_test_file(tmp_path, "NOTES.TXT", "Some content")
    result = loader.load_file(path)
    assert result["source_format"] == ".txt"

    path2 = create_test_file(tmp_path, "readme.MD", "More content")
    result2 = loader.load_file(path2)
    assert result2["source_format"] == ".md"


def test_load_file_filename_extraction(loader, tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    filepath = subdir / "notes.txt"
    filepath.write_bytes(b"Some content")
    result = loader.load_file(str(filepath))
    assert result["filename"] == "notes.txt"


# === Loading Files — Normalization ===


def test_load_file_strips_bom(loader, tmp_path):
    path = create_test_file(tmp_path, "bom.txt", b"\xef\xbb\xbfHello BOM")
    result = loader.load_file(path)
    assert result["text"] == "Hello BOM"


def test_load_file_normalizes_crlf(loader, tmp_path):
    path = create_test_file(tmp_path, "crlf.txt", "Line 1\r\nLine 2\r\nLine 3")
    result = loader.load_file(path)
    assert result["text"] == "Line 1\nLine 2\nLine 3"


def test_load_file_normalizes_cr(loader, tmp_path):
    path = create_test_file(tmp_path, "cr.txt", "Line 1\rLine 2")
    result = loader.load_file(path)
    assert result["text"] == "Line 1\nLine 2"


def test_load_file_strips_surrounding_whitespace(loader, tmp_path):
    path = create_test_file(tmp_path, "ws.txt", "\n\n  Hello  \n\n")
    result = loader.load_file(path)
    assert result["text"] == "Hello"


def test_load_file_preserves_internal_whitespace(loader, tmp_path):
    content = "Paragraph one.\n\n  Indented line.\n\nParagraph three."
    path = create_test_file(tmp_path, "internal.txt", content)
    result = loader.load_file(path)
    assert result["text"] == content


# === Loading Files — Encoding ===


def test_load_file_utf8(loader, tmp_path):
    path = create_test_file(tmp_path, "utf8.txt", "Café résumé naïve")
    result = loader.load_file(path)
    assert result["text"] == "Café résumé naïve"


def test_load_file_latin1_fallback(loader, tmp_path):
    path = create_test_file(tmp_path, "latin1.txt", b"Caf\xe9 r\xe9sum\xe9")
    result = loader.load_file(path)
    assert "sum" in result["text"]


# === Loading Files — Validation Errors ===


def test_load_file_unsupported_format(loader, tmp_path):
    path = create_test_file(tmp_path, "document.docx", "content")
    with pytest.raises(ValueError, match="Unsupported file format"):
        loader.load_file(path)


def test_load_file_no_extension(loader, tmp_path):
    path = create_test_file(tmp_path, "README", "content")
    with pytest.raises(ValueError, match="Unsupported file format.*no extension"):
        loader.load_file(path)


def test_load_file_not_found(loader):
    with pytest.raises(FileNotFoundError, match="File not found"):
        loader.load_file("/nonexistent/path/notes.txt")


def test_load_file_too_large(loader, tmp_path):
    path = create_test_file(tmp_path, "big.txt", "x" * 1_048_577)
    with pytest.raises(ValueError, match="exceeds maximum size"):
        loader.load_file(path)


def test_load_file_exactly_max_size(loader, tmp_path):
    path = create_test_file(tmp_path, "maxsize.txt", "x" * 1_048_576)
    result = loader.load_file(path)
    assert len(result["text"]) == 1_048_576


def test_load_file_empty(loader, tmp_path):
    path = create_test_file(tmp_path, "empty.txt", "")
    with pytest.raises(ValueError, match="File is empty"):
        loader.load_file(path)


def test_load_file_whitespace_only(loader, tmp_path):
    path = create_test_file(tmp_path, "ws_only.txt", "   \n\n\t  \n  ")
    with pytest.raises(ValueError, match="File is empty"):
        loader.load_file(path)


def test_load_file_binary_content(loader, tmp_path):
    path = create_test_file(tmp_path, "data.txt", b"Hello\x00World")
    with pytest.raises(ValueError, match="binary"):
        loader.load_file(path)


# === Loading Files — Validation Order ===


def test_validation_order_format_before_existence(loader):
    with pytest.raises(ValueError, match="Unsupported file format"):
        loader.load_file("/fake/path/file.docx")


# === Loading Text — Happy Path ===


def test_load_text_basic(loader):
    result = loader.load_text("Hello, this is pasted text.")
    assert result["text"] == "Hello, this is pasted text."
    assert result["source_format"] == "paste"
    assert result["filename"] is None


def test_load_text_multiline(loader):
    result = loader.load_text("Line 1\nLine 2\nLine 3")
    assert result["text"] == "Line 1\nLine 2\nLine 3"


def test_load_text_unicode(loader):
    result = loader.load_text("Names: José García, François Müller")
    assert result["text"] == "Names: José García, François Müller"


# === Loading Text — Normalization ===


def test_load_text_normalizes_crlf(loader):
    result = loader.load_text("Line 1\r\nLine 2")
    assert result["text"] == "Line 1\nLine 2"


def test_load_text_strips_surrounding_whitespace(loader):
    result = loader.load_text("\n\n  Some text  \n\n")
    assert result["text"] == "Some text"


# === Loading Text — Validation Errors ===


def test_load_text_empty(loader):
    with pytest.raises(ValueError, match="cannot be empty"):
        loader.load_text("")


def test_load_text_whitespace_only(loader):
    with pytest.raises(ValueError, match="cannot be empty"):
        loader.load_text("   \n\t\n  ")


def test_load_text_not_a_string(loader):
    with pytest.raises(TypeError, match="must be a string"):
        loader.load_text(12345)
    with pytest.raises(TypeError, match="must be a string"):
        loader.load_text(None)


# === Utility Methods ===


def test_get_supported_formats(loader):
    formats = loader.get_supported_formats()
    assert formats == [".txt", ".md"]
    assert isinstance(formats, list)


def test_get_max_file_size(loader):
    size = loader.get_max_file_size()
    assert size == 1048576
    assert isinstance(size, int)


# === Integration Readiness ===


def test_output_compatible_with_session_creation(loader, tmp_path):
    # Test with load_text
    result = loader.load_text("Test document for session creation.")
    assert set(result.keys()) == {"text", "source_format", "filename"}
    assert isinstance(result["text"], str) and len(result["text"]) > 0
    assert result["source_format"] in (".txt", ".md", "paste")
    assert result["filename"] is None

    # Test with load_file
    path = create_test_file(tmp_path, "session_test.txt", "Test document for session creation.")
    result2 = loader.load_file(path)
    assert set(result2.keys()) == {"text", "source_format", "filename"}
    assert isinstance(result2["text"], str) and len(result2["text"]) > 0
    assert result2["source_format"] in (".txt", ".md", "paste")
    assert isinstance(result2["filename"], str)
