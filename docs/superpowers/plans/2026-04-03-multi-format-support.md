# Multi-Format File Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add .docx, .pdf, .csv, .xlsx, and .html file support to PII Washer using strategy-pattern extractors in DocumentLoader.

**Architecture:** Each file format gets its own extractor class in `pii_washer/extractors/`, all implementing the same `BaseExtractor.extract(bytes, filename) -> str` interface. DocumentLoader gains a `load_bytes()` method and a format-to-extractor registry. The upload endpoint in the API router branches on file extension to decide whether to use the existing UTF-8 text path or the new bytes-to-extractor path.

**Tech Stack:** python-docx, pdfplumber, openpyxl, beautifulsoup4, pytest, FastAPI

**Spec:** `docs/superpowers/specs/2026-04-03-multi-format-support-design.md`

---

## Phase 1a: `.docx` Support + Architecture Foundation

This is the largest phase because it establishes the extractor infrastructure that all subsequent phases reuse.

### Task 1: Create extractor base class and package

**Files:**
- Create: `pii_washer/extractors/__init__.py`
- Create: `pii_washer/extractors/base.py`
- Test: `pii_washer/tests/test_extractors_base.py`

- [ ] **Step 1: Write the failing test**

Create `pii_washer/tests/test_extractors_base.py`:

```python
import pytest

from pii_washer.extractors.base import BaseExtractor


def test_base_extractor_cannot_be_used_directly():
    extractor = BaseExtractor()
    with pytest.raises(NotImplementedError):
        extractor.extract(b"some bytes", "test.txt")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest pii_washer/tests/test_extractors_base.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

Create `pii_washer/extractors/__init__.py`:

```python
```

Create `pii_washer/extractors/base.py`:

```python
class BaseExtractor:
    """Base class for format-specific text extractors.

    All extractors take raw file bytes and return structured plain text
    with document structure preserved via whitespace and newlines.
    """

    def extract(self, content: bytes, filename: str) -> str:
        """Extract text from file bytes. Subclasses must override."""
        raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest pii_washer/tests/test_extractors_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pii_washer/extractors/__init__.py pii_washer/extractors/base.py pii_washer/tests/test_extractors_base.py
git commit -m "feat: add extractor base class and package"
```

---

### Task 2: Build the docx extractor

**Files:**
- Create: `pii_washer/extractors/docx.py`
- Create: `pii_washer/tests/test_extractors_docx.py`
- Create: `pii_washer/tests/fixtures/` (directory)
- Create: `pii_washer/tests/fixtures/sample.docx` (generated in test setup)

**Dependencies:** `python-docx >= 1.1.0` — add to `pyproject.toml` before starting.

- [ ] **Step 1: Add python-docx dependency**

In `pyproject.toml`, add `"python-docx >= 1.1.0"` to `dependencies`:

```toml
dependencies = [
    "presidio-analyzer >= 2.2.359",
    "spacy >= 3.8.0, < 4.0",
    "fastapi >= 0.111.0",
    "uvicorn >= 0.29.0",
    "python-multipart >= 0.0.9",
    "tldextract >= 5.0",
    "httpx >= 0.27.0",
    "python-docx >= 1.1.0",
]
```

Run: `pip install -e .`

- [ ] **Step 2: Write the failing tests**

Create `pii_washer/tests/test_extractors_docx.py`:

```python
import io

import pytest
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from pii_washer.extractors.docx import DocxExtractor


def _make_docx(**kwargs) -> bytes:
    """Build a .docx in memory and return its bytes."""
    doc = Document()
    if "paragraphs" in kwargs:
        for text in kwargs["paragraphs"]:
            doc.add_paragraph(text)
    if "heading" in kwargs:
        doc.add_heading(kwargs["heading"], level=1)
    if "headings_and_paragraphs" in kwargs:
        for item in kwargs["headings_and_paragraphs"]:
            if item["type"] == "heading":
                doc.add_heading(item["text"], level=item.get("level", 1))
            else:
                doc.add_paragraph(item["text"])
    if "bullets" in kwargs:
        for text in kwargs["bullets"]:
            doc.add_paragraph(text, style="List Bullet")
    if "numbered" in kwargs:
        for text in kwargs["numbered"]:
            doc.add_paragraph(text, style="List Number")
    if "table" in kwargs:
        rows = kwargs["table"]
        table = doc.add_table(rows=len(rows), cols=len(rows[0]))
        for i, row_data in enumerate(rows):
            for j, cell_text in enumerate(row_data):
                table.rows[i].cells[j].text = cell_text
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
def extractor():
    return DocxExtractor()


class TestDocxExtractorHappyPath:
    def test_extracts_paragraphs(self, extractor):
        content = _make_docx(paragraphs=["First paragraph.", "Second paragraph."])
        result = extractor.extract(content, "test.docx")
        assert "First paragraph." in result
        assert "Second paragraph." in result
        # Paragraphs separated by blank lines
        assert "First paragraph.\n\nSecond paragraph." in result

    def test_extracts_headings(self, extractor):
        content = _make_docx(headings_and_paragraphs=[
            {"type": "heading", "text": "Introduction", "level": 1},
            {"type": "paragraph", "text": "Some intro text."},
        ])
        result = extractor.extract(content, "test.docx")
        assert "Introduction" in result
        assert "Some intro text." in result

    def test_extracts_bullet_lists(self, extractor):
        content = _make_docx(bullets=["Item one", "Item two", "Item three"])
        result = extractor.extract(content, "test.docx")
        assert "- Item one" in result
        assert "- Item two" in result
        assert "- Item three" in result

    def test_extracts_numbered_lists(self, extractor):
        content = _make_docx(numbered=["First step", "Second step"])
        result = extractor.extract(content, "test.docx")
        assert "1. First step" in result
        assert "2. Second step" in result

    def test_extracts_tables(self, extractor):
        content = _make_docx(table=[
            ["Name", "Email"],
            ["John Smith", "john@example.com"],
        ])
        result = extractor.extract(content, "test.docx")
        assert "Name" in result
        assert "John Smith" in result
        assert "john@example.com" in result
        assert "|" in result

    def test_returns_string(self, extractor):
        content = _make_docx(paragraphs=["Hello world."])
        result = extractor.extract(content, "test.docx")
        assert isinstance(result, str)


class TestDocxExtractorEdgeCases:
    def test_empty_document_raises(self, extractor):
        doc = Document()
        buf = io.BytesIO()
        doc.save(buf)
        with pytest.raises(ValueError, match="No text content"):
            extractor.extract(buf.getvalue(), "empty.docx")

    def test_corrupted_file_raises(self, extractor):
        with pytest.raises(ValueError, match="could not be read"):
            extractor.extract(b"this is not a docx file", "bad.docx")

    def test_preserves_paragraph_separation(self, extractor):
        content = _make_docx(paragraphs=[
            "Paragraph one with some text.",
            "Paragraph two with more text.",
            "Paragraph three wraps up.",
        ])
        result = extractor.extract(content, "test.docx")
        lines = result.split("\n\n")
        assert len(lines) >= 3
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_extractors_docx.py -v`
Expected: FAIL — module `pii_washer.extractors.docx` not found

- [ ] **Step 4: Write the docx extractor**

Create `pii_washer/extractors/docx.py`:

```python
import io

from .base import BaseExtractor


class DocxExtractor(BaseExtractor):
    """Extracts structured text from .docx files."""

    # python-docx list style prefixes
    _BULLET_STYLES = {"List Bullet", "List Bullet 2", "List Bullet 3"}
    _NUMBER_STYLES = {"List Number", "List Number 2", "List Number 3"}

    def extract(self, content: bytes, filename: str) -> str:
        try:
            from docx import Document
        except ImportError:
            raise RuntimeError("python-docx is required for .docx support: pip install python-docx")

        try:
            doc = Document(io.BytesIO(content))
        except Exception:
            raise ValueError(f"This file could not be read. It may be corrupted or in an unexpected format.")

        parts = []

        # Extract body content
        numbered_counter = 0
        prev_was_numbered = False

        for element in doc.element.body:
            tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

            if tag == "p":
                para = None
                for p in doc.paragraphs:
                    if p._element is element:
                        para = p
                        break
                if para is None or not para.text.strip():
                    if prev_was_numbered:
                        numbered_counter = 0
                        prev_was_numbered = False
                    continue

                style_name = para.style.name if para.style else ""

                if style_name in self._BULLET_STYLES:
                    parts.append(f"- {para.text.strip()}")
                    prev_was_numbered = False
                elif style_name in self._NUMBER_STYLES:
                    numbered_counter += 1
                    parts.append(f"{numbered_counter}. {para.text.strip()}")
                    prev_was_numbered = True
                elif style_name.startswith("Heading"):
                    if prev_was_numbered:
                        numbered_counter = 0
                        prev_was_numbered = False
                    parts.append(para.text.strip())
                else:
                    if prev_was_numbered:
                        numbered_counter = 0
                        prev_was_numbered = False
                    parts.append(para.text.strip())

            elif tag == "tbl":
                if prev_was_numbered:
                    numbered_counter = 0
                    prev_was_numbered = False
                for table in doc.tables:
                    if table._element is element:
                        parts.append(self._extract_table(table))
                        break

        text = "\n\n".join(parts).strip()

        if not text:
            raise ValueError("No text content could be extracted from this file.")

        return text

    def _extract_table(self, table) -> str:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join(rows)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_extractors_docx.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add pii_washer/extractors/docx.py pii_washer/tests/test_extractors_docx.py pyproject.toml
git commit -m "feat: add docx extractor with structure preservation"
```

---

### Task 3: Add `load_bytes()` to DocumentLoader and extractor registry

**Files:**
- Modify: `pii_washer/document_loader.py`
- Modify: `pii_washer/tests/test_document_loader.py`

- [ ] **Step 1: Write the failing tests**

Append to `pii_washer/tests/test_document_loader.py`:

```python
# === Loading Bytes — Extractor Path ===

def test_load_bytes_docx(loader):
    """load_bytes with .docx extension dispatches to DocxExtractor."""
    import io
    from docx import Document

    doc = Document()
    doc.add_paragraph("John Smith lives in Springfield.")
    buf = io.BytesIO()
    doc.save(buf)

    result = loader.load_bytes(buf.getvalue(), ".docx", "test.docx")
    assert "John Smith" in result["text"]
    assert "Springfield" in result["text"]
    assert result["source_format"] == ".docx"
    assert result["filename"] == "test.docx"


def test_load_bytes_unsupported_format(loader):
    with pytest.raises(ValueError, match="Unsupported file format"):
        loader.load_bytes(b"data", ".xyz", "test.xyz")


def test_load_bytes_empty_extraction(loader):
    """If extractor returns empty text after normalization, raise ValueError."""
    import io
    from docx import Document

    doc = Document()
    buf = io.BytesIO()
    doc.save(buf)

    with pytest.raises(ValueError, match="No text content"):
        loader.load_bytes(buf.getvalue(), ".docx", "empty.docx")


def test_get_supported_formats_includes_docx(loader):
    formats = loader.get_supported_formats()
    assert ".docx" in formats
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_document_loader.py::test_load_bytes_docx -v`
Expected: FAIL — `load_bytes` not defined

- [ ] **Step 3: Update DocumentLoader**

Replace the contents of `pii_washer/document_loader.py` with:

```python
import os

from pii_washer.extractors.base import BaseExtractor
from pii_washer.extractors.docx import DocxExtractor


class DocumentLoader:
    SUPPORTED_FORMATS = [".txt", ".md", ".docx"]
    MAX_FILE_SIZE = 1_048_576  # 1 MB in bytes

    # Binary formats that use extractors (bytes path)
    _EXTRACTOR_MAP: dict[str, BaseExtractor] = {
        ".docx": DocxExtractor(),
    }

    # Text formats that use UTF-8 decode path
    _TEXT_FORMATS = {".txt", ".md"}

    def load_file(self, filepath: str) -> dict:
        # 1. Validate extension
        _, ext = os.path.splitext(filepath)
        if not ext:
            raise ValueError("Unsupported file format: (no extension)")
        ext_lower = ext.lower()
        if ext_lower not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}")

        # 2. Check existence
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        # 3. Check size
        file_size = os.path.getsize(filepath)
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError("File exceeds maximum size of 1 MB")

        # 4. Binary formats use extractors
        if ext_lower in self._EXTRACTOR_MAP:
            with open(filepath, "rb") as f:
                content = f.read()
            return self.load_bytes(content, ext_lower, os.path.basename(filepath))

        # 5. Text formats: read with encoding fallback
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, encoding="latin-1") as f:
                content = f.read()

        # 6. Check for null bytes (binary detection)
        if "\x00" in content:
            raise ValueError("File appears to be binary, not text")

        # 7. Normalize
        text = self._normalize(content, strip_bom=True)

        # 8. Check non-empty
        if not text:
            raise ValueError("File is empty")

        return {
            "text": text,
            "source_format": ext_lower,
            "filename": os.path.basename(filepath),
        }

    def load_text(self, text: str) -> dict:
        # 1. Type check
        if not isinstance(text, str):
            raise TypeError("Input must be a string")

        # 2. Normalize (no BOM stripping for pasted text)
        normalized = self._normalize(text, strip_bom=False)

        # 3. Check non-empty
        if not normalized:
            raise ValueError("Text cannot be empty")

        return {
            "text": normalized,
            "source_format": "paste",
            "filename": None,
        }

    def load_bytes(self, content: bytes, extension: str, filename: str) -> dict:
        """Load a file from raw bytes using the appropriate extractor."""
        ext_lower = extension.lower()
        extractor = self._EXTRACTOR_MAP.get(ext_lower)
        if extractor is None:
            raise ValueError(f"Unsupported file format: {extension}")

        text = extractor.extract(content, filename)

        # Normalize the extracted text
        text = self._normalize(text, strip_bom=False)

        if not text:
            raise ValueError("No text content could be extracted from this file.")

        return {
            "text": text,
            "source_format": ext_lower,
            "filename": filename,
        }

    def get_supported_formats(self) -> list[str]:
        return self.SUPPORTED_FORMATS

    def get_max_file_size(self) -> int:
        return self.MAX_FILE_SIZE

    def _normalize(self, text: str, strip_bom: bool = False) -> str:
        if strip_bom and text.startswith("\ufeff"):
            text = text[1:]
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.strip()
        return text
```

- [ ] **Step 4: Run all DocumentLoader tests**

Run: `pytest pii_washer/tests/test_document_loader.py -v`
Expected: All PASS. Note: `test_load_file_unsupported_format` tests `.docx` — this test must be updated since `.docx` is now supported. Change it to test `.xyz` instead:

In `test_document_loader.py`, update the existing test:

```python
def test_load_file_unsupported_format(loader, tmp_path):
    path = create_test_file(tmp_path, "document.xyz", "content")
    with pytest.raises(ValueError, match="Unsupported file format"):
        loader.load_file(path)
```

Also update `test_validation_order_format_before_existence`:

```python
def test_validation_order_format_before_existence(loader):
    with pytest.raises(ValueError, match="Unsupported file format"):
        loader.load_file("/fake/path/file.xyz")
```

And update `test_get_supported_formats`:

```python
def test_get_supported_formats(loader):
    formats = loader.get_supported_formats()
    assert ".txt" in formats
    assert ".md" in formats
    assert ".docx" in formats
    assert isinstance(formats, list)
```

- [ ] **Step 5: Run full test suite**

Run: `pytest pii_washer/tests/test_document_loader.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add pii_washer/document_loader.py pii_washer/tests/test_document_loader.py
git commit -m "feat: add load_bytes() and extractor registry to DocumentLoader"
```

---

### Task 4: Update API router to handle binary uploads

**Files:**
- Modify: `pii_washer/api/config.py`
- Modify: `pii_washer/api/router.py`
- Modify: `pii_washer/session_manager.py`
- Modify: `pii_washer/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

Add to `pii_washer/tests/test_api.py`, after the existing upload tests:

```python
def test_upload_docx_file(client):
    """Uploading a .docx creates a session with extracted text."""
    import io
    from docx import Document

    doc = Document()
    doc.add_paragraph("John Smith lives in Springfield.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    resp = client.post(
        "/api/v1/sessions/upload",
        files={"file": ("test.docx", buf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_format"] == ".docx"
    assert data["source_filename"] == "test.docx"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest pii_washer/tests/test_api.py::test_upload_docx_file -v`
Expected: FAIL — `.docx` not in `ALLOWED_EXTENSIONS`

- [ ] **Step 3: Update config**

In `pii_washer/api/config.py`:

```python
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"
DEFAULT_PORT = 8000
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx"}
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
]
APP_VERSION = "1.1.1"

# Binary formats that require extractor-based processing (not UTF-8 text decode)
BINARY_FORMATS = {".docx"}
```

- [ ] **Step 4: Update router upload endpoint**

In `pii_washer/api/router.py`, replace the `upload_session` function:

```python
@router.post("/sessions/upload", status_code=201, response_model=SessionCreatedResponse)
async def upload_session(file: UploadFile, request: Request):
    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        supported = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "UNSUPPORTED_FORMAT",
                f"File type '{suffix}' is not supported. Allowed: {supported}",
            ),
        )

    # Read content with streaming size check (1MB limit, aligned with DocumentLoader)
    max_size = DocumentLoader.MAX_FILE_SIZE
    chunks = []
    total = 0
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            return JSONResponse(
                status_code=413,
                content=_error_body(
                    "FILE_TOO_LARGE",
                    f"File exceeds the {max_size // (1024 * 1024)} MB limit",
                ),
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    sm = _sm(request)

    try:
        # Binary formats go through extractor path
        if suffix in BINARY_FORMATS:
            session_id = sm.load_uploaded_bytes(content, suffix, file.filename)
        else:
            # Text formats: decode UTF-8 first
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                return JSONResponse(
                    status_code=422,
                    content=_error_body(
                        "DECODE_ERROR",
                        "File could not be decoded as UTF-8 text",
                    ),
                )
            session_id = sm.load_uploaded_content(text, suffix, file.filename)

        session = sm.get_session(session_id)
        return _to_session_created(session)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)
```

Add `BINARY_FORMATS` to the import line in router.py:

```python
from .config import ALLOWED_EXTENSIONS, APP_VERSION, BINARY_FORMATS
```

- [ ] **Step 5: Add `load_uploaded_bytes` to SessionManager**

In `pii_washer/session_manager.py`, add after the `load_uploaded_content` method:

```python
    def load_uploaded_bytes(self, content, extension, filename):
        """Create a session from uploaded binary file content using extractors."""
        result = self.document_loader.load_bytes(content, extension, filename)
        session_id = self.store.create_session(
            result["text"], result["source_format"], result["filename"]
        )
        return session_id
```

- [ ] **Step 6: Run the test**

Run: `pytest pii_washer/tests/test_api.py::test_upload_docx_file -v`
Expected: PASS

- [ ] **Step 7: Run full test suite to check for regressions**

Run: `pytest pii_washer/tests/ -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add pii_washer/api/config.py pii_washer/api/router.py pii_washer/session_manager.py pii_washer/tests/test_api.py
git commit -m "feat: route .docx uploads through extractor pipeline"
```

---

### Task 5: Update frontend to accept .docx

**Files:**
- Modify: `pii-washer-ui/src/components/tabs/InputTab.tsx`

- [ ] **Step 1: Update the file input accept attribute**

In `pii-washer-ui/src/components/tabs/InputTab.tsx`, find:

```tsx
accept=".txt,.md,text/plain,text/markdown"
```

Replace with:

```tsx
accept=".txt,.md,.docx,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
```

- [ ] **Step 2: Update the upload zone label**

In the same file, find:

```tsx
<span className="text-muted-foreground">Upload .txt / .md</span>
```

Replace with:

```tsx
<span className="text-muted-foreground">Upload file (.txt, .md, .docx)</span>
```

- [ ] **Step 3: Update the error message**

In the same file, find:

```tsx
return 'Unsupported file type. Only .txt and .md files are accepted.';
```

Replace with:

```tsx
return 'Unsupported file type. Supported formats: .txt, .md, .docx';
```

- [ ] **Step 4: Verify frontend builds**

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add pii-washer-ui/src/components/tabs/InputTab.tsx
git commit -m "feat: accept .docx uploads in frontend"
```

---

## Phase 1b: `.pdf` Support

### Task 6: Build the PDF extractor

**Files:**
- Create: `pii_washer/extractors/pdf.py`
- Create: `pii_washer/tests/test_extractors_pdf.py`

**Dependencies:** `pdfplumber >= 0.11.0` — add to `pyproject.toml`.

- [ ] **Step 1: Add pdfplumber dependency**

In `pyproject.toml`, add `"pdfplumber >= 0.11.0"` to `dependencies`. Run: `pip install -e .`

- [ ] **Step 2: Write the failing tests**

Create `pii_washer/tests/test_extractors_pdf.py`:

```python
import io

import pytest

from pii_washer.extractors.pdf import PdfExtractor


def _make_pdf(pages: list[str]) -> bytes:
    """Build a simple text PDF in memory using pdfplumber's underlying lib."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for page_text in pages:
        y = 750
        for line in page_text.split("\n"):
            c.drawString(72, y, line)
            y -= 14
        c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def extractor():
    return PdfExtractor()


class TestPdfExtractorHappyPath:
    def test_extracts_single_page(self, extractor):
        content = _make_pdf(["John Smith lives at 123 Main Street."])
        result = extractor.extract(content, "test.pdf")
        assert "John Smith" in result
        assert "123 Main Street" in result

    def test_extracts_multiple_pages(self, extractor):
        content = _make_pdf([
            "Page one content with Jane Doe.",
            "Page two content with john@example.com.",
        ])
        result = extractor.extract(content, "test.pdf")
        assert "Jane Doe" in result
        assert "john@example.com" in result

    def test_returns_string(self, extractor):
        content = _make_pdf(["Hello world."])
        result = extractor.extract(content, "test.pdf")
        assert isinstance(result, str)


class TestPdfExtractorEdgeCases:
    def test_corrupted_file_raises(self, extractor):
        with pytest.raises(ValueError, match="could not be read"):
            extractor.extract(b"not a pdf", "bad.pdf")

    def test_empty_pdf_raises(self, extractor):
        """A PDF with no extractable text should raise."""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.showPage()
        c.save()

        with pytest.raises(ValueError, match="No text content"):
            extractor.extract(buf.getvalue(), "empty.pdf")
```

Note: The tests use `reportlab` to generate PDFs in memory. Add `"reportlab >= 4.0"` to `[project.optional-dependencies] dev` in `pyproject.toml` and run `pip install -e ".[dev]"`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_extractors_pdf.py -v`
Expected: FAIL — module not found

- [ ] **Step 4: Write the PDF extractor**

Create `pii_washer/extractors/pdf.py`:

```python
import io

from .base import BaseExtractor


class PdfExtractor(BaseExtractor):
    """Extracts structured text from .pdf files."""

    def extract(self, content: bytes, filename: str) -> str:
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError("pdfplumber is required for .pdf support: pip install pdfplumber")

        try:
            pdf = pdfplumber.open(io.BytesIO(content))
        except Exception:
            raise ValueError("This file could not be read. It may be corrupted or in an unexpected format.")

        page_texts = []
        for page in pdf.pages:
            # Extract tables separately for structured output
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    rows = []
                    for row in table:
                        cells = [(cell or "").strip() for cell in row]
                        rows.append("| " + " | ".join(cells) + " |")
                    page_texts.append("\n".join(rows))

            # Extract remaining text
            text = page.extract_text()
            if text and text.strip():
                page_texts.append(text.strip())

        pdf.close()

        result = "\n\n".join(page_texts).strip()

        if not result:
            raise ValueError("No text content could be extracted from this file.")

        return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_extractors_pdf.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add pii_washer/extractors/pdf.py pii_washer/tests/test_extractors_pdf.py pyproject.toml
git commit -m "feat: add PDF extractor with table support"
```

---

### Task 7: Wire PDF into DocumentLoader, router, and frontend

**Files:**
- Modify: `pii_washer/document_loader.py`
- Modify: `pii_washer/api/config.py`
- Modify: `pii_washer/api/router.py` (only the error message string, if hardcoded)
- Modify: `pii-washer-ui/src/components/tabs/InputTab.tsx`
- Modify: `pii_washer/tests/test_api.py`

- [ ] **Step 1: Write the failing API test**

Add to `pii_washer/tests/test_api.py`:

```python
def test_upload_pdf_file(client):
    """Uploading a .pdf creates a session with extracted text."""
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 750, "Jane Doe called (555) 123-4567 yesterday.")
    c.showPage()
    c.save()
    buf.seek(0)

    resp = client.post(
        "/api/v1/sessions/upload",
        files={"file": ("test.pdf", buf, "application/pdf")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_format"] == ".pdf"
```

- [ ] **Step 2: Register PDF in DocumentLoader, config, and frontend**

In `pii_washer/document_loader.py`, add the import and registry entry:

```python
from pii_washer.extractors.pdf import PdfExtractor
```

Update `SUPPORTED_FORMATS`:

```python
SUPPORTED_FORMATS = [".txt", ".md", ".docx", ".pdf"]
```

Update `_EXTRACTOR_MAP`:

```python
_EXTRACTOR_MAP: dict[str, BaseExtractor] = {
    ".docx": DocxExtractor(),
    ".pdf": PdfExtractor(),
}
```

In `pii_washer/api/config.py`, update:

```python
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}
BINARY_FORMATS = {".docx", ".pdf"}
```

In `pii-washer-ui/src/components/tabs/InputTab.tsx`, update the accept attribute:

```tsx
accept=".txt,.md,.docx,.pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf"
```

Update the label:

```tsx
<span className="text-muted-foreground">Upload file (.txt, .md, .docx, .pdf)</span>
```

Update the error message:

```tsx
return 'Unsupported file type. Supported formats: .txt, .md, .docx, .pdf';
```

- [ ] **Step 3: Run all tests**

Run: `pytest pii_washer/tests/ -v`
Expected: All PASS

- [ ] **Step 4: Verify frontend builds**

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add pii_washer/document_loader.py pii_washer/api/config.py pii_washer/tests/test_api.py pii-washer-ui/src/components/tabs/InputTab.tsx
git commit -m "feat: wire PDF support into upload pipeline and frontend"
```

---

## Phase 2: `.csv` and `.xlsx` Support

### Task 8: Build the CSV extractor

**Files:**
- Create: `pii_washer/extractors/csv_ext.py`
- Create: `pii_washer/tests/test_extractors_csv.py`

- [ ] **Step 1: Write the failing tests**

Create `pii_washer/tests/test_extractors_csv.py`:

```python
import pytest

from pii_washer.extractors.csv_ext import CsvExtractor


@pytest.fixture
def extractor():
    return CsvExtractor()


class TestCsvExtractorHappyPath:
    def test_extracts_simple_csv(self, extractor):
        content = b"Name,Email,Department\nJohn Smith,john@example.com,Sales\nJane Doe,jane@example.com,Marketing\n"
        result = extractor.extract(content, "test.csv")
        assert "John Smith" in result
        assert "john@example.com" in result
        assert "|" in result

    def test_preserves_header_row(self, extractor):
        content = b"Name,Email\nJohn Smith,john@example.com\n"
        result = extractor.extract(content, "test.csv")
        assert "Name" in result
        assert "Email" in result

    def test_handles_quoted_fields(self, extractor):
        content = b'Name,Address\n"Smith, John","123 Main St, Springfield"\n'
        result = extractor.extract(content, "test.csv")
        assert "Smith, John" in result
        assert "123 Main St, Springfield" in result

    def test_returns_string(self, extractor):
        content = b"A,B\n1,2\n"
        result = extractor.extract(content, "test.csv")
        assert isinstance(result, str)


class TestCsvExtractorEdgeCases:
    def test_empty_csv_raises(self, extractor):
        with pytest.raises(ValueError, match="No text content"):
            extractor.extract(b"", "empty.csv")

    def test_header_only_csv(self, extractor):
        content = b"Name,Email\n"
        result = extractor.extract(content, "test.csv")
        assert "Name" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_extractors_csv.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the CSV extractor**

Create `pii_washer/extractors/csv_ext.py` (named `csv_ext` to avoid shadowing stdlib `csv`):

```python
import csv
import io

from .base import BaseExtractor


class CsvExtractor(BaseExtractor):
    """Extracts structured text from .csv files."""

    def extract(self, content: bytes, filename: str) -> str:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception:
                raise ValueError("This file could not be read. It may be corrupted or in an unexpected format.")

        reader = csv.reader(io.StringIO(text))
        rows = []
        for row in reader:
            if any(cell.strip() for cell in row):
                cells = [cell.strip() for cell in row]
                rows.append("| " + " | ".join(cells) + " |")

        result = "\n".join(rows).strip()

        if not result:
            raise ValueError("No text content could be extracted from this file.")

        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_extractors_csv.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add pii_washer/extractors/csv_ext.py pii_washer/tests/test_extractors_csv.py
git commit -m "feat: add CSV extractor"
```

---

### Task 9: Build the XLSX extractor

**Files:**
- Create: `pii_washer/extractors/xlsx.py`
- Create: `pii_washer/tests/test_extractors_xlsx.py`

**Dependencies:** `openpyxl >= 3.1.0` — add to `pyproject.toml`.

- [ ] **Step 1: Add openpyxl dependency**

In `pyproject.toml`, add `"openpyxl >= 3.1.0"` to `dependencies`. Run: `pip install -e .`

- [ ] **Step 2: Write the failing tests**

Create `pii_washer/tests/test_extractors_xlsx.py`:

```python
import io

import pytest
from openpyxl import Workbook

from pii_washer.extractors.xlsx import XlsxExtractor


def _make_xlsx(sheets: dict[str, list[list[str]]]) -> bytes:
    """Build an .xlsx in memory. sheets = {"Sheet1": [["A1", "B1"], ["A2", "B2"]]}"""
    wb = Workbook()
    first = True
    for name, rows in sheets.items():
        if first:
            ws = wb.active
            ws.title = name
            first = False
        else:
            ws = wb.create_sheet(name)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def extractor():
    return XlsxExtractor()


class TestXlsxExtractorHappyPath:
    def test_extracts_single_sheet(self, extractor):
        content = _make_xlsx({"Sheet1": [
            ["Name", "Email"],
            ["John Smith", "john@example.com"],
        ]})
        result = extractor.extract(content, "test.xlsx")
        assert "John Smith" in result
        assert "john@example.com" in result
        assert "|" in result

    def test_extracts_multiple_sheets(self, extractor):
        content = _make_xlsx({
            "Employees": [["Name"], ["John Smith"]],
            "Contacts": [["Email"], ["jane@example.com"]],
        })
        result = extractor.extract(content, "test.xlsx")
        assert "Employees" in result
        assert "Contacts" in result
        assert "John Smith" in result
        assert "jane@example.com" in result

    def test_returns_string(self, extractor):
        content = _make_xlsx({"Sheet1": [["A", "B"], ["1", "2"]]})
        result = extractor.extract(content, "test.xlsx")
        assert isinstance(result, str)


class TestXlsxExtractorEdgeCases:
    def test_empty_workbook_raises(self, extractor):
        wb = Workbook()
        buf = io.BytesIO()
        wb.save(buf)
        with pytest.raises(ValueError, match="No text content"):
            extractor.extract(buf.getvalue(), "empty.xlsx")

    def test_corrupted_file_raises(self, extractor):
        with pytest.raises(ValueError, match="could not be read"):
            extractor.extract(b"not an xlsx", "bad.xlsx")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_extractors_xlsx.py -v`
Expected: FAIL — module not found

- [ ] **Step 4: Write the XLSX extractor**

Create `pii_washer/extractors/xlsx.py`:

```python
import io

from .base import BaseExtractor


class XlsxExtractor(BaseExtractor):
    """Extracts structured text from .xlsx files."""

    def extract(self, content: bytes, filename: str) -> str:
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise RuntimeError("openpyxl is required for .xlsx support: pip install openpyxl")

        try:
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception:
            raise ValueError("This file could not be read. It may be corrupted or in an unexpected format.")

        sheet_parts = []
        multiple_sheets = len(wb.sheetnames) > 1

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(values_only=True):
                cells = [(str(cell) if cell is not None else "") for cell in row]
                if any(c.strip() for c in cells):
                    rows.append("| " + " | ".join(cells) + " |")

            if rows:
                if multiple_sheets:
                    sheet_parts.append(f"[{sheet_name}]\n\n" + "\n".join(rows))
                else:
                    sheet_parts.append("\n".join(rows))

        wb.close()

        result = "\n\n".join(sheet_parts).strip()

        if not result:
            raise ValueError("No text content could be extracted from this file.")

        return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_extractors_xlsx.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add pii_washer/extractors/xlsx.py pii_washer/tests/test_extractors_xlsx.py pyproject.toml
git commit -m "feat: add XLSX extractor with multi-sheet support"
```

---

### Task 10: Wire CSV and XLSX into the pipeline

**Files:**
- Modify: `pii_washer/document_loader.py`
- Modify: `pii_washer/api/config.py`
- Modify: `pii-washer-ui/src/components/tabs/InputTab.tsx`
- Modify: `pii_washer/tests/test_api.py`

- [ ] **Step 1: Register both formats**

In `pii_washer/document_loader.py`, add imports:

```python
from pii_washer.extractors.csv_ext import CsvExtractor
from pii_washer.extractors.xlsx import XlsxExtractor
```

Update `SUPPORTED_FORMATS`:

```python
SUPPORTED_FORMATS = [".txt", ".md", ".docx", ".pdf", ".csv", ".xlsx"]
```

Update `_EXTRACTOR_MAP`:

```python
_EXTRACTOR_MAP: dict[str, BaseExtractor] = {
    ".docx": DocxExtractor(),
    ".pdf": PdfExtractor(),
    ".csv": CsvExtractor(),
    ".xlsx": XlsxExtractor(),
}
```

In `pii_washer/api/config.py`:

```python
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf", ".csv", ".xlsx"}
BINARY_FORMATS = {".docx", ".pdf", ".xlsx"}
```

Note: `.csv` is text-based but we route it through the extractor for consistent table formatting. Add `.csv` to `BINARY_FORMATS` as well since the extractor handles decoding:

```python
BINARY_FORMATS = {".docx", ".pdf", ".csv", ".xlsx"}
```

In `pii-washer-ui/src/components/tabs/InputTab.tsx`, update accept:

```tsx
accept=".txt,.md,.docx,.pdf,.csv,.xlsx,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
```

Update label:

```tsx
<span className="text-muted-foreground">Upload file</span>
```

Update error message:

```tsx
return 'Unsupported file type. Supported: .txt, .md, .docx, .pdf, .csv, .xlsx';
```

- [ ] **Step 2: Write API tests**

Add to `pii_washer/tests/test_api.py`:

```python
def test_upload_csv_file(client):
    resp = client.post(
        "/api/v1/sessions/upload",
        files={"file": ("test.csv", b"Name,Email\nJohn Smith,john@example.com\n", "text/csv")},
    )
    assert resp.status_code == 201
    assert resp.json()["source_format"] == ".csv"


def test_upload_xlsx_file(client):
    import io
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Name", "Email"])
    ws.append(["John Smith", "john@example.com"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    resp = client.post(
        "/api/v1/sessions/upload",
        files={"file": ("test.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 201
    assert resp.json()["source_format"] == ".xlsx"
```

- [ ] **Step 3: Run all tests**

Run: `pytest pii_washer/tests/ -v`
Expected: All PASS

- [ ] **Step 4: Verify frontend builds**

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add pii_washer/document_loader.py pii_washer/api/config.py pii_washer/tests/test_api.py pii-washer-ui/src/components/tabs/InputTab.tsx
git commit -m "feat: wire CSV and XLSX support into upload pipeline"
```

---

## Phase 3: `.html` Support

### Task 11: Build the HTML extractor

**Files:**
- Create: `pii_washer/extractors/html.py`
- Create: `pii_washer/tests/test_extractors_html.py`

**Dependencies:** `beautifulsoup4 >= 4.12.0` — add to `pyproject.toml`.

- [ ] **Step 1: Add beautifulsoup4 dependency**

In `pyproject.toml`, add `"beautifulsoup4 >= 4.12.0"` to `dependencies`. Run: `pip install -e .`

- [ ] **Step 2: Write the failing tests**

Create `pii_washer/tests/test_extractors_html.py`:

```python
import pytest

from pii_washer.extractors.html import HtmlExtractor


@pytest.fixture
def extractor():
    return HtmlExtractor()


class TestHtmlExtractorHappyPath:
    def test_extracts_paragraphs(self, extractor):
        content = b"<html><body><p>John Smith is a customer.</p><p>His email is john@example.com.</p></body></html>"
        result = extractor.extract(content, "test.html")
        assert "John Smith" in result
        assert "john@example.com" in result

    def test_preserves_paragraph_breaks(self, extractor):
        content = b"<p>First paragraph.</p><p>Second paragraph.</p>"
        result = extractor.extract(content, "test.html")
        assert "First paragraph." in result
        assert "Second paragraph." in result
        # Should have separation between paragraphs
        assert "First paragraph.\n\nSecond paragraph." in result or "First paragraph.\n\nSecond paragraph." in result.replace("\r\n", "\n")

    def test_extracts_headings(self, extractor):
        content = b"<h1>Report Title</h1><p>Some content here.</p>"
        result = extractor.extract(content, "test.html")
        assert "Report Title" in result
        assert "Some content here." in result

    def test_extracts_lists(self, extractor):
        content = b"<ul><li>Item one</li><li>Item two</li></ul>"
        result = extractor.extract(content, "test.html")
        assert "Item one" in result
        assert "Item two" in result

    def test_extracts_tables(self, extractor):
        content = b"<table><tr><td>Name</td><td>Email</td></tr><tr><td>John</td><td>john@example.com</td></tr></table>"
        result = extractor.extract(content, "test.html")
        assert "Name" in result
        assert "john@example.com" in result
        assert "|" in result

    def test_strips_scripts_and_styles(self, extractor):
        content = b"<html><head><style>body{color:red}</style></head><body><script>alert('hi')</script><p>Visible text.</p></body></html>"
        result = extractor.extract(content, "test.html")
        assert "Visible text." in result
        assert "alert" not in result
        assert "color:red" not in result

    def test_returns_string(self, extractor):
        content = b"<p>Hello</p>"
        result = extractor.extract(content, "test.html")
        assert isinstance(result, str)


class TestHtmlExtractorEdgeCases:
    def test_empty_html_raises(self, extractor):
        with pytest.raises(ValueError, match="No text content"):
            extractor.extract(b"<html><body></body></html>", "empty.html")

    def test_empty_bytes_raises(self, extractor):
        with pytest.raises(ValueError, match="No text content"):
            extractor.extract(b"", "empty.html")

    def test_handles_br_tags(self, extractor):
        content = b"<p>Line one.<br>Line two.</p>"
        result = extractor.extract(content, "test.html")
        assert "Line one." in result
        assert "Line two." in result
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_extractors_html.py -v`
Expected: FAIL — module not found

- [ ] **Step 4: Write the HTML extractor**

Create `pii_washer/extractors/html.py`:

```python
from .base import BaseExtractor


class HtmlExtractor(BaseExtractor):
    """Extracts structured text from .html files."""

    # Block elements that should produce paragraph breaks
    _BLOCK_TAGS = {"p", "div", "section", "article", "main", "aside", "header", "footer",
                   "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "address"}
    _LIST_TAGS = {"ul", "ol"}
    _LIST_ITEM_TAG = "li"
    _TABLE_TAG = "table"

    def extract(self, content: bytes, filename: str) -> str:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise RuntimeError("beautifulsoup4 is required for .html support: pip install beautifulsoup4")

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception:
                raise ValueError("This file could not be read. It may be corrupted or in an unexpected format.")

        soup = BeautifulSoup(text, "html.parser")

        # Remove script, style, and hidden elements
        for tag in soup.find_all(["script", "style", "noscript"]):
            tag.decompose()

        # Replace <br> with newlines before extracting
        for br in soup.find_all("br"):
            br.replace_with("\n")

        parts = []

        # Process tables separately for pipe-delimited output
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append("| " + " | ".join(cells) + " |")
            if rows:
                parts.append("\n".join(rows))
            table.decompose()

        # Process lists
        for list_tag in soup.find_all(["ul", "ol"]):
            is_ordered = list_tag.name == "ol"
            items = []
            for i, li in enumerate(list_tag.find_all("li", recursive=False), 1):
                text_content = li.get_text(strip=True)
                if text_content:
                    prefix = f"{i}." if is_ordered else "-"
                    items.append(f"{prefix} {text_content}")
            if items:
                parts.append("\n".join(items))
            list_tag.decompose()

        # Process remaining block elements
        for tag in soup.find_all(self._BLOCK_TAGS):
            text_content = tag.get_text(separator="\n", strip=True)
            if text_content:
                parts.append(text_content)
            tag.decompose()

        # Capture any remaining text
        remaining = soup.get_text(separator="\n", strip=True)
        if remaining:
            parts.append(remaining)

        result = "\n\n".join(parts).strip()

        if not result:
            raise ValueError("No text content could be extracted from this file.")

        return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_extractors_html.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add pii_washer/extractors/html.py pii_washer/tests/test_extractors_html.py pyproject.toml
git commit -m "feat: add HTML extractor"
```

---

### Task 12: Wire HTML into the pipeline and finalize

**Files:**
- Modify: `pii_washer/document_loader.py`
- Modify: `pii_washer/api/config.py`
- Modify: `pii-washer-ui/src/components/tabs/InputTab.tsx`
- Modify: `pii_washer/tests/test_api.py`

- [ ] **Step 1: Register HTML format**

In `pii_washer/document_loader.py`, add import:

```python
from pii_washer.extractors.html import HtmlExtractor
```

Update `SUPPORTED_FORMATS`:

```python
SUPPORTED_FORMATS = [".txt", ".md", ".docx", ".pdf", ".csv", ".xlsx", ".html"]
```

Update `_EXTRACTOR_MAP`:

```python
_EXTRACTOR_MAP: dict[str, BaseExtractor] = {
    ".docx": DocxExtractor(),
    ".pdf": PdfExtractor(),
    ".csv": CsvExtractor(),
    ".xlsx": XlsxExtractor(),
    ".html": HtmlExtractor(),
}
```

In `pii_washer/api/config.py`:

```python
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf", ".csv", ".xlsx", ".html"}
BINARY_FORMATS = {".docx", ".pdf", ".csv", ".xlsx", ".html"}
```

In `pii-washer-ui/src/components/tabs/InputTab.tsx`, update accept:

```tsx
accept=".txt,.md,.docx,.pdf,.csv,.xlsx,.html,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/html"
```

Update error message:

```tsx
return 'Unsupported file type. Supported: .txt, .md, .docx, .pdf, .csv, .xlsx, .html';
```

- [ ] **Step 2: Write API test**

Add to `pii_washer/tests/test_api.py`:

```python
def test_upload_html_file(client):
    content = b"<html><body><p>John Smith called (555) 123-4567.</p></body></html>"
    resp = client.post(
        "/api/v1/sessions/upload",
        files={"file": ("test.html", content, "text/html")},
    )
    assert resp.status_code == 201
    assert resp.json()["source_format"] == ".html"
```

- [ ] **Step 3: Run full test suite**

Run: `pytest pii_washer/tests/ -v`
Expected: All PASS

- [ ] **Step 4: Verify frontend builds**

Run: `cd pii-washer-ui && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Run frontend tests**

Run: `cd pii-washer-ui && npm test`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add pii_washer/document_loader.py pii_washer/api/config.py pii_washer/tests/test_api.py pii-washer-ui/src/components/tabs/InputTab.tsx
git commit -m "feat: wire HTML support into upload pipeline — all formats complete"
```

---

## Task 13: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Update README**

In the "Detected PII types" section of `README.md`, update the file upload note to mention supported formats. In the "Quick start" section or near the upload description, add:

```markdown
### Supported file formats

| Format | Extensions |
|---|---|
| Plain text | .txt, .md |
| Documents | .docx, .pdf |
| Spreadsheets | .csv, .xlsx |
| Web pages | .html |

Paste text directly or upload a file. All processing happens in memory — files are never written to disk.
```

- [ ] **Step 2: Update CHANGELOG**

Add to the `[Unreleased]` section (or create it):

```markdown
## [Unreleased]

### Added

- File format support: .docx, .pdf, .csv, .xlsx, .html
- Extractor architecture in `pii_washer/extractors/` with strategy pattern
- Structure preservation: headings, paragraphs, lists, and tables maintained in extracted text
```

- [ ] **Step 3: Update roadmap**

In `docs/roadmap.md`, move "Additional file formats" from medium-term to completed:

```markdown
| Additional file formats | Added .docx, .pdf, .csv, .xlsx, .html support via extractor architecture. Structure preserved in extraction. | 2026-04-XX |
```

(Replace `XX` with the actual completion date.)

- [ ] **Step 4: Commit**

```bash
git add README.md CHANGELOG.md docs/roadmap.md
git commit -m "docs: update README, CHANGELOG, and roadmap for multi-format support"
```

- [ ] **Step 5: Push**

```bash
git push
```
