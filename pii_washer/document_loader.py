import os


class DocumentLoader:
    SUPPORTED_FORMATS = [".txt", ".md"]
    MAX_FILE_SIZE = 1_048_576  # 1 MB in bytes

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

        # 4. Read with encoding fallback
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="latin-1") as f:
                content = f.read()

        # 5. Check for null bytes (binary detection)
        if "\x00" in content:
            raise ValueError("File appears to be binary, not text")

        # 6. Normalize
        text = self._normalize(content, strip_bom=True)

        # 7. Check non-empty
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
