import csv
import io

from pii_washer.extractors.base import BaseExtractor


class CsvExtractor(BaseExtractor):
    """Extract plain text from .csv files as pipe-delimited rows.

    Each CSV row is converted to pipe-delimited format:
    "| cell1 | cell2 | ... |"

    Empty rows are skipped. The header row is preserved as-is.
    """

    def extract(self, content: bytes, filename: str) -> str:
        """Extract structured plain text from .csv bytes.

        Args:
            content: Raw bytes of the .csv file.
            filename: Original filename, used in error messages.

        Returns:
            Pipe-delimited rows joined with newlines.

        Raises:
            ValueError: If the file contains no rows.
        """
        # Decode with UTF-8, fallback to latin-1
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        reader = csv.reader(io.StringIO(text))

        parts: list[str] = []
        for row in reader:
            # Skip entirely empty rows
            if not any(cell.strip() for cell in row):
                continue
            parts.append("| " + " | ".join(row) + " |")

        if not parts:
            raise ValueError(
                f"No text content found in '{filename}'."
            )

        return "\n".join(parts)
