"""Custom Presidio recognizers for name detection fallback layers."""

import json
import re
from pathlib import Path

from presidio_analyzer import Pattern, PatternRecognizer
from presidio_analyzer import EntityRecognizer, RecognizerResult


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


class DictionaryNameRecognizer(EntityRecognizer):
    """Detects names by matching common first names adjacent to capitalized words."""

    CONFIDENCE = 0.4

    def __init__(self):
        super().__init__(
            supported_entities=["PERSON"],
            supported_language="en",
            name="DictionaryNameRecognizer",
        )
        names_path = DATA_DIR / "common_first_names.json"
        with open(names_path, "r", encoding="utf-8") as f:
            self._first_names = set(json.load(f))

    def load(self):
        """Required by EntityRecognizer interface. No-op — data loaded in __init__."""
        pass

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=0):
        results = []
        tokens = list(re.finditer(r"\b[A-Za-z]+\b", text))

        for i, token in enumerate(tokens):
            word = token.group()
            if word.lower() not in self._first_names:
                continue
            if not word[0].isupper():
                continue

            name_end = token.end()
            found_surname = False
            for j in range(1, 3):  # up to 2 more words
                if i + j >= len(tokens):
                    break
                next_token = tokens[i + j]
                next_word = next_token.group()
                gap = text[name_end:next_token.start()]
                if gap.strip() != "":
                    break
                if not next_word[0].isupper() or not next_word[1:].islower():
                    break
                name_end = next_token.end()
                found_surname = True

            if found_surname:
                results.append(RecognizerResult(
                    entity_type="PERSON",
                    start=token.start(),
                    end=name_end,
                    score=self.CONFIDENCE,
                ))

        return results
