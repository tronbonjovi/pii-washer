import os

from pii_washer.extractors.base import BaseExtractor
from pii_washer.extractors.csv_ext import CsvExtractor
from pii_washer.extractors.docx import DocxExtractor
from pii_washer.extractors.html import HtmlExtractor
from pii_washer.extractors.pdf import PdfExtractor
from pii_washer.extractors.xlsx import XlsxExtractor


class DocumentLoader:
    SUPPORTED_FORMATS = [".txt", ".md", ".docx", ".pdf", ".csv", ".xlsx", ".html"]
    MAX_FILE_SIZE = 1_048_576  # 1 MB in bytes

    # Binary formats that go through the extractor registry instead of
    # the UTF-8 text path.
    _TEXT_FORMATS = {".txt", ".md"}
    _EXTRACTOR_MAP: dict[str, BaseExtractor] = {
        ".docx": DocxExtractor(),
        ".pdf": PdfExtractor(),
        ".csv": CsvExtractor(),
        ".xlsx": XlsxExtractor(),
        ".html": HtmlExtractor(),
    }

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

        # 4. Binary formats go through the extractor registry
        if ext_lower in self._EXTRACTOR_MAP:
            with open(filepath, "rb") as f:
                content = f.read()
            basename = os.path.basename(filepath)
            return self.load_bytes(content, ext_lower, basename)

        # 5. Read text formats with encoding fallback
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

    def load_bytes(self, content: bytes, extension: str, filename: str) -> dict:
        """Extract text from raw bytes using the extractor registry.

        Used for binary formats (e.g. .docx) uploaded via the API or loaded
        from disk. The caller is responsible for size validation when needed.

        Args:
            content:   Raw bytes of the file.
            extension: Lowercase file extension including the dot (e.g. ".docx").
            filename:  Original filename, used in error messages and metadata.

        Returns:
            dict with keys: text, source_format, filename.

        Raises:
            ValueError: If the extension is unsupported, or extraction yields
                        no text.
        """
        ext_lower = extension.lower()
        extractor = self._EXTRACTOR_MAP.get(ext_lower)
        if extractor is None:
            raise ValueError(f"Unsupported file format: {extension}")

        raw_text = extractor.extract(content, filename)
        text = self._normalize(raw_text, strip_bom=False)

        if not text:
            raise ValueError("No text content found in file")

        return {
            "text": text,
            "source_format": ext_lower,
            "filename": filename,
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
