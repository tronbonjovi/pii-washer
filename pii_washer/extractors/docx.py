import io

from pii_washer.extractors.base import BaseExtractor

# Style name prefixes that map to list formatting.
_BULLET_STYLES = {"List Bullet", "List Bullet 2", "List Bullet 3"}
_NUMBER_STYLES = {"List Number", "List Number 2", "List Number 3"}


class DocxExtractor(BaseExtractor):
    """Extract plain text from .docx files, preserving document structure.

    Structure is represented via whitespace conventions:
    - Paragraphs and headings are separated by blank lines.
    - Bullet items are prefixed with "- ".
    - Numbered items are prefixed with "N. " (counter resets per document).
    - Table rows are pipe-delimited: "| cell1 | cell2 | ... |"
    """

    def extract(self, content: bytes, filename: str) -> str:
        """Extract structured plain text from .docx bytes.

        Args:
            content: Raw bytes of the .docx file.
            filename: Original filename, used in error messages.

        Returns:
            Structured plain text joined with blank lines between elements.

        Raises:
            ValueError: If the file cannot be parsed or contains no text.
        """
        try:
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph
        except ImportError as exc:
            raise RuntimeError(
                "python-docx is required to read .docx files. "
                "Install it with: pip install python-docx"
            ) from exc

        try:
            doc = Document(io.BytesIO(content))
        except Exception as exc:
            raise ValueError(
                f"'{filename}' could not be read as a .docx file: {exc}"
            ) from exc

        parts: list[str] = []
        number_counter = 0

        for child in doc.element.body:
            tag = child.tag.split("}")[-1]

            if tag == "p":
                para = Paragraph(child, doc)
                text = para.text.strip()
                if not text:
                    continue

                style_name = para.style.name if para.style else ""

                if style_name in _BULLET_STYLES:
                    parts.append(f"- {text}")
                elif style_name in _NUMBER_STYLES:
                    number_counter += 1
                    parts.append(f"{number_counter}. {text}")
                else:
                    # Headings (e.g. "Heading 1") and regular paragraphs both
                    # land here — they're treated as plain text blocks, which
                    # is appropriate since we're producing input for PII scanning.
                    parts.append(text)

            elif tag == "tbl":
                table = Table(child, doc)
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    parts.append("| " + " | ".join(cells) + " |")

            # sectPr and other structural tags are intentionally ignored.

        if not parts:
            raise ValueError(
                f"No text content found in '{filename}'."
            )

        return "\n\n".join(parts)
