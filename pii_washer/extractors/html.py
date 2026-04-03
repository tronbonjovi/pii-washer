from pii_washer.extractors.base import BaseExtractor


class HtmlExtractor(BaseExtractor):
    """Extract plain text from .html files, preserving document structure.

    - Scripts, styles, and noscript blocks are removed.
    - Tables become pipe-delimited rows: "| cell1 | cell2 | ... |"
    - Unordered lists become "- item" entries.
    - Ordered lists become "1. item" entries.
    - Block elements (p, div, h1-h6, etc.) become separated paragraphs.
    - <br> tags are converted to newlines.
    - All blocks are joined with double newlines.
    """

    # Tags whose entire subtree (tag + content) should be removed.
    _STRIP_TAGS = {"script", "style", "noscript"}

    # Block-level tags whose text content becomes a paragraph.
    _BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
                   "article", "section", "header", "footer", "main",
                   "blockquote", "pre", "address", "figure", "figcaption"}

    def extract(self, content: bytes, filename: str) -> str:
        """Extract structured plain text from .html bytes.

        Args:
            content: Raw bytes of the HTML file.
            filename: Original filename, used in error messages.

        Returns:
            Structured plain text with paragraphs separated by blank lines,
            lists prefixed, and tables pipe-delimited.

        Raises:
            RuntimeError: If beautifulsoup4 is not installed.
            ValueError: If the file contains no visible text content.
        """
        try:
            from bs4 import BeautifulSoup, Tag
        except ImportError as exc:
            raise RuntimeError(
                "beautifulsoup4 is required to read .html files. "
                "Install it with: pip install beautifulsoup4"
            ) from exc

        # Decode bytes — UTF-8 with latin-1 fallback.
        try:
            html_text = content.decode("utf-8")
        except UnicodeDecodeError:
            html_text = content.decode("latin-1")

        soup = BeautifulSoup(html_text, "html.parser")

        # 1. Remove script, style, noscript and their content entirely.
        for tag_name in self._STRIP_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # 2. Replace <br> with newline strings before extracting text.
        for br in soup.find_all("br"):
            br.replace_with("\n")

        parts: list[str] = []

        # 3. Extract tables as pipe-delimited rows.
        for table in soup.find_all("table"):
            rows_output: list[str] = []
            for row in table.find_all("tr"):
                cells = [cell.get_text(separator=" ").strip() for cell in row.find_all(["th", "td"])]
                if any(cells):
                    rows_output.append("| " + " | ".join(cells) + " |")
            if rows_output:
                parts.append("\n".join(rows_output))
            table.decompose()

        # 4. Extract lists (ul → "- item", ol → "1. item").
        for ul in soup.find_all("ul"):
            items = [f"- {li.get_text(separator=' ').strip()}" for li in ul.find_all("li")]
            if items:
                parts.append("\n".join(items))
            ul.decompose()

        for ol in soup.find_all("ol"):
            items = [
                f"{i + 1}. {li.get_text(separator=' ').strip()}"
                for i, li in enumerate(ol.find_all("li"))
            ]
            if items:
                parts.append("\n".join(items))
            ol.decompose()

        # 5. Extract block-level elements as paragraphs.
        for tag_name in self._BLOCK_TAGS:
            for tag in soup.find_all(tag_name):
                text = tag.get_text(separator="\n").strip()
                if text:
                    parts.append(text)
                tag.decompose()

        # 6. Capture any remaining text (inline elements, bare text nodes).
        remaining = soup.get_text(separator="\n").strip()
        if remaining:
            parts.append(remaining)

        # 7. Join blocks with double newlines; strip individual blocks.
        result = "\n\n".join(p.strip() for p in parts if p.strip())

        if not result:
            raise ValueError(
                f"No text content found in '{filename}'."
            )

        return result
