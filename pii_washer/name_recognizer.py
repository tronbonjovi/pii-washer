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

        # Load multi-word exclusions (shared with CapitalizedPairRecognizer) so
        # that known company/phrase pairs like "Morgan Stanley" are not flagged.
        exclusions_path = DATA_DIR / "capitalized_word_exclusions.json"
        with open(exclusions_path, "r", encoding="utf-8") as f:
            excl_data = json.load(f)
        self._multiword_exclusions: set[str] = set()
        for category, values in excl_data.items():
            for value in values:
                if len(value.split()) > 1:
                    self._multiword_exclusions.add(value.lower())

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
                if "\n" in gap:
                    break
                if gap.strip() != "":
                    break
                if not next_word[0].isupper() or not next_word[1:].islower():
                    break
                name_end = next_token.end()
                found_surname = True

            if found_surname:
                matched_text = text[token.start():name_end]
                if matched_text.lower() in self._multiword_exclusions:
                    continue
                results.append(RecognizerResult(
                    entity_type="PERSON",
                    start=token.start(),
                    end=name_end,
                    score=self.CONFIDENCE,
                ))

        return results


class CapitalizedPairRecognizer(EntityRecognizer):
    """Detects potential names from adjacent capitalized word pairs not at sentence starts."""

    CONFIDENCE = 0.3

    def __init__(self):
        super().__init__(
            supported_entities=["PERSON"],
            supported_language="en",
            name="CapitalizedPairRecognizer",
        )
        exclusions_path = DATA_DIR / "capitalized_word_exclusions.json"
        with open(exclusions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Org suffixes disqualify any match containing them (even one word)
        self._org_suffixes = {v.lower() for v in data.get("org_suffixes", [])}
        # Multi-word exclusions filter if the full phrase matches
        self._multiword_exclusions = set()
        # Single-word exclusions filter only if ALL words in the match are excluded
        self._singleword_exclusions = set()
        for category, values in data.items():
            if category == "org_suffixes":
                continue
            for value in values:
                words = value.split()
                if len(words) == 1:
                    self._singleword_exclusions.add(value.lower())
                else:
                    self._multiword_exclusions.add(value.lower())

    def load(self):
        pass

    def _is_sentence_start(self, text, start):
        """Check if position `start` is at the beginning of a sentence/clause."""
        if start == 0:
            return True
        before = text[:start]
        window = before[max(0, len(before) - 10):]
        if re.search(r"[.!?]\s+$", window):
            return True
        if re.search(r":\s+$", window):
            return True
        if re.search(r"\n\s*[-*\u2022]\s+$", window):
            return True
        if re.search(r"\n\s*\d+\.\s+$", window):
            return True
        if re.search(r"\n\s*>\s*$", window):
            return True
        if re.search(r"\n\s*$", window):
            return True
        if re.search(r"\t$", window):
            return True
        return False

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=0):
        results = []
        # [^\S\n]+ matches whitespace except newlines — prevents spans bleeding across lines
        pattern = re.compile(r"\b([A-Z][a-z]+(?:[^\S\n]+[A-Z][a-z]+){1,2})\b")

        # Precompute bracket/paren regions to skip enclosed text (UI labels, etc.)
        bracket_regions = [
            (m.start(), m.end())
            for m in re.finditer(r"[\[(][^)\]]*[\])]", text)
        ]

        for match in pattern.finditer(text):
            start = match.start()
            matched_text = match.group()

            # Filter: skip sentence starts
            if self._is_sentence_start(text, start):
                continue

            # Filter: skip matches inside brackets or parentheses
            if any(bs <= start and match.end() <= be for bs, be in bracket_regions):
                continue

            # Filter: skip if the full phrase matches a multi-word exclusion
            if matched_text.lower() in self._multiword_exclusions:
                continue

            words = matched_text.split()

            # Filter: skip if ANY word is an org suffix (e.g., "Acme Corp")
            if any(w.lower() in self._org_suffixes for w in words):
                continue

            # Filter: skip if ALL words in the match are single-word exclusions
            # (e.g., "January February" — both are month names)
            # But "May Chen" passes because "Chen" is not excluded
            if all(w.lower() in self._singleword_exclusions for w in words):
                continue

            results.append(RecognizerResult(
                entity_type="PERSON",
                start=start,
                end=match.end(),
                score=self.CONFIDENCE,
            ))

        return results
