"""Custom Presidio recognizers for name detection fallback layers."""

import re
from pathlib import Path

from presidio_analyzer import Pattern, PatternRecognizer


DATA_DIR = Path(__file__).parent / "data"


class TitleNameRecognizer(PatternRecognizer):
    """Detects names preceded by titles like Mr., Dr., Judge, etc."""

    TITLES = [
        "Mr", "Mrs", "Ms", "Miss", "Dr",
        "Prof", "Professor", "Rev", "Reverend",
        "Sr", "Jr",
        "Sgt", "Sergeant", "Cpl", "Corporal", "Pvt", "Private",
        "Lt", "Lieutenant", "Capt", "Captain",
        "Maj", "Major", "Col", "Colonel", "Gen", "General",
        "Hon", "Honorable",
        "Judge", "Justice",
        "Sen", "Senator", "Rep", "Representative",
        "Gov", "Governor", "Pres", "President",
    ]

    def __init__(self):
        title_alternation = "|".join(re.escape(t) for t in self.TITLES)
        pattern_text = (
            r"\b(?:" + title_alternation + r")\.?\s+"
            r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b"
        )
        patterns = [Pattern("title_name", pattern_text, score=0.7)]
        super().__init__(
            supported_entity="PERSON",
            patterns=patterns,
            supported_language="en",
            name="TitleNameRecognizer",
        )
