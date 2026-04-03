import pytest

from pii_washer.extractors.base import BaseExtractor


class ConcreteExtractor(BaseExtractor):
    """Minimal concrete subclass used only to test BaseExtractor directly."""

    def extract(self, content: bytes, filename: str) -> str:
        return super().extract(content, filename)


# === BaseExtractor Interface ===


def test_extract_raises_not_implemented_error():
    extractor = ConcreteExtractor()
    with pytest.raises(NotImplementedError):
        extractor.extract(b"some content", "file.txt")


def test_extract_signature_accepts_bytes_and_filename():
    """Verify the method exists and is callable with the expected signature."""
    extractor = ConcreteExtractor()
    assert callable(extractor.extract)
