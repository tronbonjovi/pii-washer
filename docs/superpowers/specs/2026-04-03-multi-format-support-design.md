# Multi-Format File Support — Design Spec

**Date:** 2026-04-03
**Status:** Approved
**Scope:** Phase 1 — add file format support to the existing tool without architecture changes

## Context

PII Washer currently accepts `.txt` and `.md` files (plus pasted text). Users frequently work with Word documents, PDFs, spreadsheets, and HTML files that contain PII. Adding format support is the highest-value remaining feature for making the tool share-ready.

This is Phase 1 work — formats are added to the existing 4-tab workflow. The broader product reframe (markdown-internal format, batch mode, CLI) is Phase 2 and not in scope here.

## Architecture: Strategy Pattern in DocumentLoader

Each format gets its own extractor module in `pii_washer/extractors/`. All extractors implement a common interface:

```python
class BaseExtractor:
    def extract(self, content: bytes, filename: str) -> str:
        """Takes raw file bytes, returns structured plain text."""
        ...
```

Extractors return a string with the document's text content, preserving structure via whitespace and newlines:
- Headings get their own lines
- Paragraphs are separated by blank lines
- Lists keep their bullet/number prefixes
- Tables become simple pipe-delimited text tables

A format-to-extractor registry in DocumentLoader maps extensions to their extractor class.

Example table output (used consistently across docx, pdf, csv, xlsx):
```
| Name       | Email              | Department |
| John Smith | john@example.com   | Sales      |
| Jane Doe   | jane@example.com   | Marketing  |
```

### DocumentLoader Changes

- `SUPPORTED_FORMATS` expands to include all new extensions
- New method: `load_bytes(content: bytes, extension: str, filename: str) -> dict` — for binary formats that can't be decoded as UTF-8 upfront
- Existing `load_file()` and `load_text()` paths stay unchanged for `.txt`, `.md`, and pasted text
- Registry maps extensions to extractor classes

### Router Changes

- Upload endpoint currently decodes all bytes to UTF-8 then passes text
- For binary formats (`.docx`, `.pdf`, `.xlsx`), passes raw bytes to `DocumentLoader.load_bytes()` instead
- Text formats (`.txt`, `.md`, `.csv`, `.html`) continue using the existing UTF-8 decode path
- Decision is based on file extension

### Config Changes

- `ALLOWED_EXTENSIONS` in `config.py` expands to include all new formats
- Frontend file input `accept` attribute expands

## Per-Format Details

### Phase 1a: `.docx` (Microsoft Word)

**Library:** `python-docx >= 1.1.0`

**Extracts:**
- Paragraphs — preserved with blank line separation
- Headings — preserved as distinct lines
- Bullet/numbered lists — preserved with `-` or `1.` prefixes
- Tables — rows with `|` dividers, readable plain text
- Headers/footers — extracted at top/bottom, labeled

**Ignores:** Images, embedded objects, comments, tracked changes, text boxes.

### Phase 1b: `.pdf`

**Library:** `pdfplumber >= 0.11.0`

**Extracts:**
- Text content page by page, with page breaks preserved
- Tables — same pipe-delimited format as docx
- Multi-column layouts — best-effort left-to-right reading order

**Ignores:** Images (including scanned/image-only PDFs), annotations, form fields.

**Known limitation:** PDF text extraction quality varies by how the PDF was created. Some PDFs produce messy output (broken words, wrong reading order). This is a known constraint of all PDF text extraction tools, not something we can fully solve. Documented in README.

### Phase 2: `.csv` and `.xlsx`

**Libraries:** `csv` (stdlib), `openpyxl >= 3.1.0`

**Extracts:**
- All cell values, row by row
- Column headers preserved as first row
- For `.xlsx`: all sheets, each labeled with sheet name

**Output:** Pipe-delimited text table format (consistent with docx/pdf table rendering).

**Ignores:** Formulas (extracts computed values only), charts, conditional formatting, macros.

### Phase 3: `.html`

**Library:** `beautifulsoup4 >= 4.12.0`

**Extracts:**
- Visible text content with structure preserved
- Headings, paragraphs, lists, tables — same readable text output as other formats
- `<br>` → newline, `<p>` → paragraph break

**Ignores:** Scripts, styles, hidden elements, metadata, comments, navigation/boilerplate.

## Frontend Changes

Minimal:
- File input `accept` attribute includes all new extensions and MIME types
- Upload zone label changes from "Upload .txt / .md" to "Upload file"
- Tooltip or help text lists supported formats
- Error messages for unsupported formats show the full list of accepted types

No other UI changes. The text area, tabs, and workflow operate on extracted text regardless of source format.

## Error Handling

Each extractor can fail in format-specific ways. All errors surface as user-friendly messages via `ValueError`, which the existing router error handling already catches:

| Scenario | Message |
|---|---|
| Image-only PDF | "This PDF appears to be image-based. Only text-based PDFs are supported." |
| Password-protected file | "This file is password-protected. Please remove the password and try again." |
| Corrupted/unreadable file | "This file could not be read. It may be corrupted or in an unexpected format." |
| Empty extraction | "No text content could be extracted from this file." |
| File too large | Existing 1MB limit applies to raw file size, checked before extraction |

## Size Limit

The 1MB limit applies to raw file size, not extracted text. A `.docx` with images could be 900KB but yield only 5KB of text — that's fine. File size is checked before extraction runs.

## Testing

Each extractor gets its own test file. Small fixture files (a few KB each) are committed to `pii_washer/tests/fixtures/`:

- **Happy path:** extract text from well-formed file, verify structure preserved
- **Edge cases:** empty file, password-protected, image-only PDF, multi-sheet xlsx
- **Integration:** upload through API endpoint, verify full workflow (upload → extract → detect → depersonalize)

Fixture files contain fake PII to enable full pipeline testing.

## Implementation Order

Each phase is independently shippable:

1. **Phase 1a — `.docx`:** Creates `pii_washer/extractors/` package, base class, docx extractor, DocumentLoader/router/config/frontend changes, tests. Establishes the full pattern.
2. **Phase 1b — `.pdf`:** PDF extractor following the pattern from 1a. Tests. Smaller diff.
3. **Phase 2 — `.csv` + `.xlsx`:** Two extractors, same pattern. Tests.
4. **Phase 3 — `.html`:** One extractor, same pattern. Tests.

Phase 1a is the biggest because it sets up the architecture. Each subsequent phase is progressively smaller.

## Dependencies Added

| Package | Version | Phase | Purpose |
|---|---|---|---|
| `python-docx` | >= 1.1.0 | 1a | Word document extraction |
| `pdfplumber` | >= 0.11.0 | 1b | PDF text extraction |
| `openpyxl` | >= 3.1.0 | 2 | Excel spreadsheet extraction |
| `beautifulsoup4` | >= 4.12.0 | 3 | HTML text extraction |

`csv` is Python stdlib — no dependency needed.

## What This Does NOT Include

- Markdown as canonical internal format (Phase 2 rewrite)
- Batch processing or CLI mode (Phase 2 rewrite)
- Producing `.md` output files (Phase 2 rewrite)
- UI reorganization or workflow changes (Phase 2 rewrite)
- OCR for image-based PDFs
- `.eml`/`.msg` email files
- `.pptx` PowerPoint files
