class BaseExtractor:
    """Abstract base class for all format extractors.

    Each extractor converts raw file bytes into plain text, preserving
    document structure via whitespace conventions (blank lines between
    paragraphs, prefixes for lists, pipe-delimited tables).
    """

    def extract(self, content: bytes, filename: str) -> str:
        """Extract plain text from file bytes.

        Args:
            content: Raw bytes of the file.
            filename: Original filename, used for error messages and
                      format hints where needed.

        Returns:
            Structured plain text suitable for PII scanning.

        Raises:
            NotImplementedError: Subclasses must implement this method.
            ValueError: If the file cannot be parsed or contains no text.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement extract()"
        )
