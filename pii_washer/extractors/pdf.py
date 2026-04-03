import io

from pii_washer.extractors.base import BaseExtractor


class PdfExtractor(BaseExtractor):
    """Extract plain text from .pdf files, preserving table structure.

    Tables are extracted first per page as pipe-delimited rows, then
    remaining page text is appended. Pages are separated by blank lines.
    """

    def extract(self, content: bytes, filename: str) -> str:
        """Extract structured plain text from .pdf bytes.

        Args:
            content: Raw bytes of the .pdf file.
            filename: Original filename, used in error messages.

        Returns:
            Structured plain text joined with blank lines between pages.

        Raises:
            RuntimeError: If pdfplumber is not installed.
            ValueError: If the file cannot be parsed or contains no text.
        """
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError(
                "pdfplumber is required to read .pdf files. "
                "Install it with: pip install pdfplumber"
            ) from exc

        try:
            pdf = pdfplumber.open(io.BytesIO(content))
        except Exception as exc:
            raise ValueError(
                f"'{filename}' could not be read as a .pdf file: {exc}"
            ) from exc

        try:
            page_texts: list[str] = []

            for page in pdf.pages:
                parts: list[str] = []

                # Extract tables first, then collect the bounding boxes they
                # occupied so we can skip that text when extracting plain text.
                tables = page.extract_tables()
                table_bboxes = [t.bbox for t in page.find_tables()] if tables else []

                for table in tables:
                    for row in table:
                        cells = [cell.strip() if cell else "" for cell in row]
                        parts.append("| " + " | ".join(cells) + " |")

                # Extract remaining text, excluding table regions.
                if table_bboxes:
                    # Crop away each table's bounding box, then extract text
                    # from what remains.
                    remaining = page
                    for bbox in table_bboxes:
                        # pdfplumber bboxes are (x0, top, x1, bottom)
                        # We carve out everything except the table strip by
                        # extracting text from the full page without the table
                        # cells — simplest approach is to extract words outside
                        # all table bboxes.
                        pass
                    # Simpler: extract all words not inside any table bbox
                    words = page.extract_words()
                    non_table_words = [
                        w["text"] for w in words
                        if not any(
                            _word_in_bbox(w, bbox) for bbox in table_bboxes
                        )
                    ]
                    if non_table_words:
                        parts.append(" ".join(non_table_words))
                else:
                    text = page.extract_text()
                    if text:
                        parts.append(text.strip())

                if parts:
                    page_texts.append("\n\n".join(parts))

        finally:
            pdf.close()

        if not page_texts:
            raise ValueError(
                f"No text content found in '{filename}'."
            )

        return "\n\n".join(page_texts)


def _word_in_bbox(word: dict, bbox: tuple) -> bool:
    """Return True if the word's midpoint falls inside the given bounding box.

    pdfplumber word dicts have x0, top, x1, bottom keys.
    bbox is (x0, top, x1, bottom).
    """
    x0, top, x1, bottom = bbox
    wx_mid = (word["x0"] + word["x1"]) / 2
    wy_mid = (word["top"] + word["bottom"]) / 2
    return x0 <= wx_mid <= x1 and top <= wy_mid <= bottom
