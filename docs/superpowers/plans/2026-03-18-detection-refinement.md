# Detection Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve PII detection coverage by hardening regex patterns, adding name detection fallback layers, and loosening context filters — philosophy is "catch more, review more."

**Architecture:** All changes stay within the existing Presidio recognizer framework. New recognizers register in `PIIDetectionEngine.__init__()`. One new module (`name_recognizer.py`) houses custom `EntityRecognizer` subclasses for name detection. Data files (name dictionary, city list, exclusion list) load at init time.

**Tech Stack:** Python 3.13, Microsoft Presidio, spaCy `en_core_web_lg`, pytest

**Spec:** `docs/superpowers/specs/2026-03-18-detection-refinement-design.md`

---

### Task 1: Create data files

**Files:**
- Create: `pii_washer/data/common_first_names.json`
- Create: `pii_washer/data/us_cities_top200.json`
- Create: `pii_washer/data/capitalized_word_exclusions.json`

These are pure data with no code dependencies — create them first so all subsequent tasks can import them.

- [ ] **Step 1: Create `pii_washer/data/` directory**

Run: `mkdir -p pii_washer/data`

- [ ] **Step 2: Create `common_first_names.json`**

US Census-derived list of ~1000 most common first names. All lowercase for case-insensitive lookup. Include both male and female names. Example structure:

```json
["james", "mary", "robert", "patricia", "john", "jennifer", "michael", "linda", ...]
```

Source the list from US Census Bureau's most common first names data. Include approximately 500 male + 500 female names.

- [ ] **Step 3: Create `us_cities_top200.json`**

Top 200 US cities by population. Lowercase for case-insensitive lookup.

```json
["new york", "los angeles", "chicago", "houston", "phoenix", ...]
```

- [ ] **Step 4: Create `capitalized_word_exclusions.json`**

Exclusion list for the capitalized word pair heuristic. Organized by category for maintainability.

```json
{
  "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
  "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
  "us_states": ["Alabama", "Alaska", "Arizona", ...],
  "org_suffixes": ["Inc", "LLC", "Corp", "Ltd", "Co", "Foundation", "Association", "Institute", "University", "College", "Hospital", "Center", "Group", "Partners", "International", "National", "Federal", "Global"],
  "countries": ["United States", "United Kingdom", "New Zealand", "South Africa", "North Korea", "South Korea", "Saudi Arabia", "Costa Rica", "Puerto Rico", "Sri Lanka", "El Salvador", "Sierra Leone"],
  "languages": ["American English", "British English", "Mandarin Chinese"],
  "common_phrases": ["Dear Sir", "Dear Madam", "Best Regards", "Kind Regards", "Yours Truly", "Thank You", "Happy Birthday", "Happy New", "Merry Christmas", "Good Morning", "Good Afternoon", "Good Evening", "High School", "Middle School", "Supreme Court", "White House", "Wall Street", "Main Street", "Central Park", "World War", "Civil War"]
}
```

The lookup code will flatten all values into a single set at load time.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/data/
git commit -m "feat: add data files for detection refinement"
```

---

### Task 2: Title-based name recognizer (spec 1a)

**Files:**
- Create: `pii_washer/name_recognizer.py`
- Create: `pii_washer/tests/test_name_recognizer.py`

- [ ] **Step 1: Write failing tests for title-based name detection**

Create `pii_washer/tests/test_name_recognizer.py`:

```python
import pytest
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from pii_washer.name_recognizer import TitleNameRecognizer


@pytest.fixture(scope="module")
def title_recognizer():
    return TitleNameRecognizer()


@pytest.fixture(scope="module")
def analyzer(title_recognizer):
    """Minimal analyzer with just the title recognizer for isolated testing."""
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
    })
    engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=engine, supported_languages=["en"])
    analyzer.registry.add_recognizer(title_recognizer)
    return analyzer


class TestTitleNameRecognizer:
    def test_mr_lastname(self, analyzer):
        results = analyzer.analyze("Please contact Mr. Smith regarding the matter.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        assert any("Smith" in "Please contact Mr. Smith regarding the matter."[r.start:r.end] for r in persons)

    def test_dr_full_name(self, analyzer):
        results = analyzer.analyze("Dr. Jane Doe will see you now.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        texts = ["Dr. Jane Doe will see you now."[r.start:r.end] for r in persons]
        assert any("Jane" in t and "Doe" in t for t in texts)

    def test_professor_name(self, analyzer):
        results = analyzer.analyze("Professor Michael Williams teaches physics.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        texts = ["Professor Michael Williams teaches physics."[r.start:r.end] for r in persons]
        assert any("Williams" in t for t in texts)

    def test_judge_name(self, analyzer):
        results = analyzer.analyze("The case was heard by Judge Patricia Chen.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        texts = ["The case was heard by Judge Patricia Chen."[r.start:r.end] for r in persons]
        assert any("Chen" in t for t in texts)

    def test_title_without_period(self, analyzer):
        results = analyzer.analyze("Mr Smith called yesterday.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        assert any("Smith" in "Mr Smith called yesterday."[r.start:r.end] for r in persons)

    def test_three_word_name(self, analyzer):
        results = analyzer.analyze("Mrs. Mary Jane Watson arrived.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        texts = ["Mrs. Mary Jane Watson arrived."[r.start:r.end] for r in persons]
        assert any("Watson" in t for t in texts)

    def test_military_title(self, analyzer):
        results = analyzer.analyze("Sgt. Robert Johnson reported for duty.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        assert any("Johnson" in "Sgt. Robert Johnson reported for duty."[r.start:r.end] for r in persons)

    def test_confidence_is_0_7(self, title_recognizer):
        """Title recognizer should produce confidence of 0.7."""
        # Just verify the score attribute on the recognizer patterns
        for pattern in title_recognizer.patterns:
            assert pattern.score == 0.7

    def test_no_match_without_title(self, analyzer):
        """Should not produce results for names without titles (that's NER's job)."""
        text = "John Smith went to the store."
        results = analyzer.analyze(text, language="en", entities=["PERSON"])
        # Filter to only title recognizer results (score == 0.7)
        title_results = [r for r in results if r.score == 0.7]
        assert len(title_results) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_name_recognizer.py -v`
Expected: ImportError — `name_recognizer` module doesn't exist yet.

- [ ] **Step 3: Implement `TitleNameRecognizer`**

Create `pii_washer/name_recognizer.py`:

```python
"""Custom Presidio recognizers for name detection fallback layers."""

import json
import re
from pathlib import Path

from presidio_analyzer import Pattern, PatternRecognizer, EntityRecognizer, RecognizerResult


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_name_recognizer.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/name_recognizer.py pii_washer/tests/test_name_recognizer.py
git commit -m "feat: add title-based name recognizer"
```

---

### Task 3: Dictionary-based name recognizer (spec 1b)

**Files:**
- Modify: `pii_washer/name_recognizer.py`
- Modify: `pii_washer/tests/test_name_recognizer.py`

- [ ] **Step 1: Write failing tests for dictionary name detection**

Append to `pii_washer/tests/test_name_recognizer.py`:

```python
from pii_washer.name_recognizer import DictionaryNameRecognizer


@pytest.fixture(scope="module")
def dict_recognizer():
    return DictionaryNameRecognizer()


class TestDictionaryNameRecognizer:
    def test_common_first_last(self, dict_recognizer):
        text = "Jane Doe submitted the application."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        assert any("Jane" in text[r.start:r.end] for r in results)

    def test_case_insensitive_lookup(self, dict_recognizer):
        text = "JAMES Wilson was present."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        # "james" is in dictionary; "JAMES" + "Wilson" should match
        assert any("JAMES" in text[r.start:r.end] for r in results)

    def test_first_name_with_two_surnames(self, dict_recognizer):
        text = "Mary Jane Watson was there."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        assert len(results) >= 1

    def test_no_match_non_name(self, dict_recognizer):
        text = "The table was large and wooden."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        assert len(results) == 0

    def test_no_match_first_name_alone(self, dict_recognizer):
        """A first name without a capitalized surname should not match."""
        text = "James went to the store."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        # "James" + "went" (lowercase) should NOT match
        assert len(results) == 0

    def test_confidence_is_0_4(self, dict_recognizer):
        text = "Robert Smith attended the meeting."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        for r in results:
            assert r.score == 0.4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_name_recognizer.py::TestDictionaryNameRecognizer -v`
Expected: ImportError — `DictionaryNameRecognizer` doesn't exist yet.

- [ ] **Step 3: Implement `DictionaryNameRecognizer`**

Add to `pii_washer/name_recognizer.py`:

```python
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
        # Find all word tokens with their positions
        tokens = list(re.finditer(r"\b[A-Za-z]+\b", text))

        for i, token in enumerate(tokens):
            word = token.group()
            # Check if this token is a known first name (case-insensitive)
            if word.lower() not in self._first_names:
                continue
            # Must be capitalized in the text
            if not word[0].isupper():
                continue

            # Look at next 1-2 tokens for capitalized words (surname)
            name_end = token.end()
            found_surname = False
            for j in range(1, 3):  # up to 2 more words
                if i + j >= len(tokens):
                    break
                next_token = tokens[i + j]
                next_word = next_token.group()
                # Must be adjacent (only whitespace between)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_name_recognizer.py::TestDictionaryNameRecognizer -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/name_recognizer.py pii_washer/tests/test_name_recognizer.py
git commit -m "feat: add dictionary-based name recognizer"
```

---

### Task 4: Capitalized word pair heuristic recognizer (spec 1c)

**Files:**
- Modify: `pii_washer/name_recognizer.py`
- Modify: `pii_washer/tests/test_name_recognizer.py`

- [ ] **Step 1: Write failing tests**

Append to `pii_washer/tests/test_name_recognizer.py`:

```python
from pii_washer.name_recognizer import CapitalizedPairRecognizer


@pytest.fixture(scope="module")
def cap_recognizer():
    return CapitalizedPairRecognizer()


class TestCapitalizedPairRecognizer:
    def test_mid_sentence_pair(self, cap_recognizer):
        text = "The defendant, Marcus Chen, pleaded not guilty."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert any("Marcus" in t and "Chen" in t for t in texts)

    def test_no_match_sentence_start(self, cap_recognizer):
        text = "Big Apple is a nickname for New York."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        # "Big Apple" starts the sentence — should be filtered
        texts = [text[r.start:r.end] for r in results]
        assert not any("Big Apple" in t for t in texts)

    def test_no_match_after_period(self, cap_recognizer):
        text = "Done. Good Morning everyone."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("Good Morning" in t for t in texts)

    def test_no_match_after_colon(self, cap_recognizer):
        text = "Subject: Big News today."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("Big News" in t for t in texts)

    def test_no_match_after_bullet(self, cap_recognizer):
        text = "Items:\n- Red Widget is on sale."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("Red Widget" in t for t in texts)

    def test_no_match_month_names(self, cap_recognizer):
        text = "She visited in January February was cold."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("January February" in t for t in texts)

    def test_no_match_org_suffix(self, cap_recognizer):
        text = "She works at Acme Corp downtown."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("Acme Corp" in t for t in texts)

    def test_no_match_state_name(self, cap_recognizer):
        text = "They drove through New Mexico last summer."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("New Mexico" in t for t in texts)

    def test_after_comma_mid_sentence(self, cap_recognizer):
        text = "The award went to the director, Steven Park, for his work."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert any("Steven" in t and "Park" in t for t in texts)

    def test_confidence_is_0_3(self, cap_recognizer):
        text = "The director, Marcus Chen, spoke."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        for r in results:
            assert r.score == 0.3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_name_recognizer.py::TestCapitalizedPairRecognizer -v`
Expected: ImportError.

- [ ] **Step 3: Implement `CapitalizedPairRecognizer`**

Add to `pii_washer/name_recognizer.py`:

```python
class CapitalizedPairRecognizer(EntityRecognizer):
    """Detects potential names from adjacent capitalized word pairs not at sentence starts."""

    CONFIDENCE = 0.3

    # Characters/patterns that indicate the start of a new sentence or clause
    _SENTENCE_START_PATTERN = re.compile(
        r"(?:"
        r"^"                    # start of text
        r"|[.!?]\s+"           # after sentence-ending punctuation
        r"|:\s+"               # after colon
        r"|\n\s*[-*\u2022]\s+" # after bullet markers
        r"|\n\s*\d+\.\s+"     # after numbered list markers
        r"|\n\s*>"             # after quote markers
        r"|\n\s*"              # after newline (general)
        r"|\t"                 # after tab
        r")"
    )

    def __init__(self):
        super().__init__(
            supported_entities=["PERSON"],
            supported_language="en",
            name="CapitalizedPairRecognizer",
        )
        exclusions_path = DATA_DIR / "capitalized_word_exclusions.json"
        with open(exclusions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Separate single-word and multi-word exclusions
        # Single-word: only exclude if the ENTIRE match is one excluded word (not applicable for pairs)
        # Multi-word: exclude if the full matched phrase matches an exclusion
        self._multiword_exclusions = set()
        self._singleword_exclusions = set()
        for category_values in data.values():
            for value in category_values:
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
        # Look at the text before this position
        before = text[:start]
        # Check if any sentence-start pattern ends right at this position
        # We check the last ~10 chars for efficiency
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
        # Find sequences of 2-3 adjacent capitalized words
        pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b")

        for match in pattern.finditer(text):
            start = match.start()
            matched_text = match.group()

            # Filter: skip sentence starts
            if self._is_sentence_start(text, start):
                continue

            # Filter: skip if the full phrase matches a multi-word exclusion
            if matched_text.lower() in self._multiword_exclusions:
                continue

            # Filter: skip if ALL words in the match are single-word exclusions
            # (e.g., "January February" — both are month names)
            # But "May Chen" passes because "Chen" is not excluded
            words = matched_text.split()
            if all(w.lower() in self._singleword_exclusions for w in words):
                continue

            results.append(RecognizerResult(
                entity_type="PERSON",
                start=start,
                end=match.end(),
                score=self.CONFIDENCE,
            ))

        return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_name_recognizer.py::TestCapitalizedPairRecognizer -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/name_recognizer.py pii_washer/tests/test_name_recognizer.py
git commit -m "feat: add capitalized word pair heuristic recognizer"
```

---

### Task 5: Register name recognizers in detection engine

**Files:**
- Modify: `pii_washer/pii_detection_engine.py`
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write failing integration tests**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
# --- Name Detection Fallback ---

class TestNameFallback:
    def test_title_name_detected(self, engine):
        text = "Please contact Mr. Smith about the delivery."
        results = engine.detect(text, confidence_threshold=0.2)
        names = [r for r in results if r["category"] == "NAME"]
        assert any("Smith" in n["original_value"] for n in names)

    def test_jane_doe_detected(self, engine):
        """The exact case from the roadmap — Jane Doe should be caught."""
        text = "The report was filed by Jane Doe on Tuesday."
        results = engine.detect(text, confidence_threshold=0.2)
        names = [r for r in results if r["category"] == "NAME"]
        assert any("Jane" in n["original_value"] for n in names)

    def test_dictionary_name_detected(self, engine):
        text = "We spoke with Robert Chen about the contract."
        results = engine.detect(text, confidence_threshold=0.2)
        names = [r for r in results if r["category"] == "NAME"]
        assert any("Robert" in n["original_value"] or "Chen" in n["original_value"] for n in names)

    def test_capitalized_pair_detected(self, engine):
        text = "The award was given to the director, Kazimir Volkov, for his work."
        results = engine.detect(text, confidence_threshold=0.2)
        names = [r for r in results if r["category"] == "NAME"]
        assert any("Kazimir" in n["original_value"] or "Volkov" in n["original_value"] for n in names)

    def test_no_duplicate_with_ner(self, engine):
        """If NER catches a name, fallback shouldn't create a duplicate."""
        text = "The application was submitted by John Smith on Monday."
        results = engine.detect(text, confidence_threshold=0.2)
        names = [r for r in results if r["category"] == "NAME"]
        # There should be at most one NAME detection for John Smith
        john_detections = [n for n in names if "John" in n["original_value"]]
        assert len(john_detections) <= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestNameFallback -v`
Expected: FAIL — "Jane Doe" and others not detected yet.

- [ ] **Step 3: Register name recognizers in `__init__`**

Modify `pii_washer/pii_detection_engine.py`:

1. Add import at top:
   ```python
   from pii_washer.name_recognizer import (
       TitleNameRecognizer,
       DictionaryNameRecognizer,
       CapitalizedPairRecognizer,
   )
   ```

2. Add after the zip_recognizer registration in `__init__`:
   ```python
   # Name detection fallback layers
   self._analyzer.registry.add_recognizer(TitleNameRecognizer())
   self._analyzer.registry.add_recognizer(DictionaryNameRecognizer())
   self._analyzer.registry.add_recognizer(CapitalizedPairRecognizer())
   ```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestNameFallback -v`
Expected: All pass.

Run: `pytest pii_washer/tests/test_pii_detection_engine.py -v`
Expected: All existing tests still pass (no regressions).

- [ ] **Step 5: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "feat: register name fallback recognizers in detection engine"
```

---

### Task 6: SSN pattern hardening (spec section 2)

**Files:**
- Modify: `pii_washer/pii_detection_engine.py`
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write failing tests for new SSN formats**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
# --- SSN Pattern Hardening ---

class TestSSNHardening:
    def test_ssn_spaces(self, engine):
        text = "SSN: 219 09 9999"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert any("219" in s["original_value"] and "9999" in s["original_value"] for s in ssns)

    def test_ssn_dots(self, engine):
        text = "SSN: 219.09.9999"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert any("219" in s["original_value"] for s in ssns)

    def test_ssn_no_separator_with_context(self, engine):
        text = "Social Security Number: 219099999"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert any("219099999" in s["original_value"] for s in ssns)

    def test_ssn_no_separator_without_context(self, engine):
        """9-digit number without SSN keywords should NOT be flagged."""
        text = "Order number: 219099999"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert len(ssns) == 0

    def test_ssn_mixed_separators(self, engine):
        text = "SSN is 219 09-9999"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert len(ssns) >= 1

    def test_ssn_invalid_area_000(self, engine):
        text = "SSN: 000-12-3456"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert len(ssns) == 0

    def test_ssn_invalid_area_666(self, engine):
        text = "SSN: 666-12-3456"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert len(ssns) == 0

    def test_ssn_invalid_area_9xx(self, engine):
        text = "SSN: 900-12-3456"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert len(ssns) == 0

    def test_ssn_invalid_group_00(self, engine):
        text = "SSN: 219-00-3456"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert len(ssns) == 0

    def test_ssn_invalid_serial_0000(self, engine):
        text = "SSN: 219-09-0000"
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert len(ssns) == 0

    def test_ssn_context_boost(self, engine):
        """SSN with context keywords should have higher confidence."""
        text_with_context = "SSN: 219-09-9999"
        text_without = "Number: 219-09-9999"
        results_with = engine.detect(text_with_context, confidence_threshold=0.2)
        results_without = engine.detect(text_without, confidence_threshold=0.2)
        ssns_with = [r for r in results_with if r["category"] == "SSN"]
        ssns_without = [r for r in results_without if r["category"] == "SSN"]
        if ssns_with and ssns_without:
            assert ssns_with[0]["confidence"] >= ssns_without[0]["confidence"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestSSNHardening -v`
Expected: FAIL — new formats not recognized.

- [ ] **Step 3: Implement custom SSN recognizer**

In `pii_washer/pii_detection_engine.py`:

1. Add a custom SSN recognizer class (or add as a method that builds patterns). The key implementation details:
   - Create a custom `EntityRecognizer` subclass that:
     - Matches SSN patterns: dashed, spaced, dotted, mixed separator (`\d{3}[\s.\-]\d{2}[\s.\-]\d{4}`), and no-separator (`\d{9}`)
     - Validates SSA rules (area not 000/666/9xx, group not 00, serial not 0000)
     - For no-separator format, requires SSN context keywords within 100 chars
     - Applies context boost (+0.2, capped at 1.0) when SSN keywords nearby
   - Register it in `__init__` and remove the built-in `US_SSN` from the supported entities if needed (or let dedup handle overlap)
   - Add `SSN_CONTEXT_KEYWORDS = ["ssn", "social security", "social sec", "ss#", "ss #"]` to class constants
   - Add `SSN_CONTEXT_WINDOW = 100` to class constants

2. Update `ENTITY_MAPPING` if the custom recognizer uses a different entity type name, or keep it producing `US_SSN`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestSSNHardening -v`
Expected: All pass.

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::test_detect_ssn -v`
Expected: Existing SSN test still passes.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "feat: harden SSN detection with multiple formats and validation"
```

---

### Task 7: Phone number pattern hardening (spec section 3)

**Files:**
- Modify: `pii_washer/pii_detection_engine.py`
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write failing tests for new phone formats**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
# --- Phone Pattern Hardening ---

class TestPhoneHardening:
    def test_phone_dots(self, engine):
        text = "Call me at 555.867.5309 today."
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        assert len(phones) >= 1

    def test_phone_spaces(self, engine):
        text = "My number is 555 867 5309."
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        assert len(phones) >= 1

    def test_phone_no_separator_with_context(self, engine):
        text = "Phone: 5558675309"
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        assert any("5558675309" in p["original_value"] for p in phones)

    def test_phone_no_separator_without_context(self, engine):
        """10-digit number without phone keywords should NOT be flagged."""
        text = "ISBN: 5558675309"
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        assert len(phones) == 0

    def test_phone_mixed_separators(self, engine):
        text = "Call (555) 867.5309 please."
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        assert len(phones) >= 1

    def test_phone_country_code_dot(self, engine):
        text = "Reach me at +1.555.867.5309 anytime."
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        assert len(phones) >= 1

    def test_phone_extension(self, engine):
        text = "Office: 555-867-5309 ext 1234"
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        assert len(phones) >= 1

    def test_phone_extension_x(self, engine):
        text = "Dial 555-867-5309 x42 for support."
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        assert len(phones) >= 1

    def test_phone_invalid_area_code(self, engine):
        """Area code starting with 0 or 1 is invalid for US phone numbers."""
        text = "Call 055-867-5309 for info."
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        # Our custom patterns require first digit 2-9; Presidio built-in may still match
        # This is a best-effort check — the important thing is our patterns don't add false positives
        custom_phones = [p for p in phones if p["confidence"] < 0.8]  # our patterns have lower confidence
        assert len(custom_phones) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestPhoneHardening -v`
Expected: FAIL — new formats not recognized.

- [ ] **Step 3: Implement custom phone recognizer**

Add a custom phone `EntityRecognizer` to `pii_washer/pii_detection_engine.py` (or a `PatternRecognizer` with multiple patterns):

Key patterns to add:
- Dots: `[2-9]\d{2}\.[2-9]\d{2}\.\d{4}`
- Spaces: `[2-9]\d{2}\s[2-9]\d{2}\s\d{4}`
- No separators (context required): `[2-9]\d{2}[2-9]\d{2}\d{4}`
- Mixed: `\(?[2-9]\d{2}\)?[\s.\-][2-9]\d{2}[\s.\-]\d{4}`
- Country code variations: `(?:\+?1[\s.\-])?` prefix on all patterns
- Extension: `(?:\s*(?:ext|x|extension)\.?\s*\d{1,5})?` suffix

Add `PHONE_CONTEXT_KEYWORDS = ["call", "phone", "tel", "cell", "mobile", "fax", "contact", "dial", "reach"]` and `PHONE_CONTEXT_WINDOW = 100`.

Register in `__init__()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestPhoneHardening -v`
Expected: All pass.

Run existing phone tests: `pytest pii_washer/tests/test_pii_detection_engine.py -k "phone" -v`
Expected: All pass (no regressions).

- [ ] **Step 5: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "feat: harden phone detection with multiple formats and validation"
```

---

### Task 8: Address pattern hardening (spec section 4)

**Files:**
- Modify: `pii_washer/pii_detection_engine.py`
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write failing tests**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
# --- Address Pattern Hardening ---

class TestAddressHardening:
    def test_address_with_apartment(self, engine):
        text = "She lives at 123 Main St Apt 4B in the city."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("123" in a["original_value"] for a in addresses)

    def test_address_with_unit_hash(self, engine):
        text = "Send it to 456 Oak Ave #12 please."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("456" in a["original_value"] for a in addresses)

    def test_po_box_standard(self, engine):
        text = "Mail to P.O. Box 1234 for processing."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("Box" in a["original_value"] or "1234" in a["original_value"] for a in addresses)

    def test_po_box_no_periods(self, engine):
        text = "Send to PO Box 567 right away."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("Box" in a["original_value"] or "567" in a["original_value"] for a in addresses)

    def test_po_box_abbreviated(self, engine):
        text = "Address: POB 890"
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("890" in a["original_value"] for a in addresses)

    def test_highway_address(self, engine):
        text = "The store is at 123 Highway 101 North."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("123" in a["original_value"] for a in addresses)

    def test_route_address(self, engine):
        text = "Located at 456 Route 66 West."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("456" in a["original_value"] for a in addresses)

    def test_street_misspelling(self, engine):
        text = "He lives at 789 Oak Steet in the suburbs."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("789" in a["original_value"] for a in addresses)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestAddressHardening -v`
Expected: FAIL.

- [ ] **Step 3: Implement address pattern updates**

In `pii_washer/pii_detection_engine.py`:

1. Extend `US_STREET_TYPES` to include: `"Highway", "Hwy", "Route", "Rte"` (Highway/Hwy already there — add Route/Rte).

2. Add `US_STREET_MISSPELLINGS` list:
   ```python
   US_STREET_MISSPELLINGS = ["Steet", "Stret", "Avnue", "Aveneue", "Bulevard", "Bouelvard"]
   ```

3. Create an extended street pattern that includes the apartment/suite/unit suffix:
   ```python
   _apt_suffix = r"(?:\s+(?:Apt|Suite|Ste|Unit|#)\s*\w+)?"
   ```

4. Add a new `US_PO_BOX` pattern recognizer:
   ```python
   PO_BOX_PATTERN = r"\b(?:P\.?O\.?\s*Box|POB|Post\s+Office\s+Box)\s+\d+\b"
   ```

5. Add misspelling pattern as a separate lower-confidence pattern.

6. Add `"US_PO_BOX": "ADDRESS"` to `ENTITY_MAPPING`.

7. Register updated street and new PO Box recognizers in `__init__()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestAddressHardening -v`
Expected: All pass.

Run: `pytest pii_washer/tests/test_pii_detection_engine.py -k "address or street" -v`
Expected: All existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "feat: harden address detection with apt/PO Box/highway/misspellings"
```

---

### Task 9: Credit card pattern hardening (spec section 5)

**Files:**
- Modify: `pii_washer/pii_detection_engine.py`
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write failing tests**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
# --- Credit Card Pattern Hardening ---

class TestCCNHardening:
    def test_ccn_spaces(self, engine):
        text = "Card: 4111 1111 1111 1111"
        results = engine.detect(text, confidence_threshold=0.2)
        ccns = [r for r in results if r["category"] == "CCN"]
        assert len(ccns) >= 1

    def test_ccn_no_separator(self, engine):
        text = "Card: 4111111111111111"
        results = engine.detect(text, confidence_threshold=0.2)
        ccns = [r for r in results if r["category"] == "CCN"]
        assert len(ccns) >= 1

    def test_ccn_dots(self, engine):
        text = "Card: 4111.1111.1111.1111"
        results = engine.detect(text, confidence_threshold=0.2)
        ccns = [r for r in results if r["category"] == "CCN"]
        assert len(ccns) >= 1

    def test_ccn_invalid_luhn(self, engine):
        """A 16-digit number that fails Luhn should NOT be detected."""
        text = "Number: 1234567890123456"
        results = engine.detect(text, confidence_threshold=0.2)
        ccns = [r for r in results if r["category"] == "CCN"]
        assert len(ccns) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestCCNHardening -v`
Expected: FAIL — new formats not recognized.

- [ ] **Step 3: Implement custom CCN recognizer**

In `pii_washer/pii_detection_engine.py`:

Create a custom `EntityRecognizer` that:
1. Matches 16-digit card numbers with spaces, dots, dashes, or no separators
2. Strips separators and runs Luhn validation
3. Assigns confidence based on separator type (dashed/spaced: 0.75, no separator: 0.5, dots: 0.6)

```python
def _luhn_check(number_str: str) -> bool:
    digits = [int(d) for d in number_str]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0
```

Register in `__init__()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestCCNHardening -v`
Expected: All pass.

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::test_detect_credit_card -v`
Expected: Existing test still passes.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "feat: harden credit card detection with multiple formats and Luhn validation"
```

---

### Task 10: IP address enhancement (spec section 6)

**Files:**
- Modify: `pii_washer/pii_detection_engine.py`
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write failing tests**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
# --- IP Address Enhancement ---

class TestIPHardening:
    def test_ipv4_with_port(self, engine):
        text = "Server at 192.168.1.100:8080 is running."
        results = engine.detect(text, confidence_threshold=0.2)
        ips = [r for r in results if r["category"] == "IP"]
        assert any("192.168.1.100" in i["original_value"] for i in ips)

    def test_ipv6_full(self, engine):
        text = "IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        results = engine.detect(text, confidence_threshold=0.2)
        ips = [r for r in results if r["category"] == "IP"]
        assert len(ips) >= 1

    def test_ipv6_compressed(self, engine):
        text = "Server: 2001:db8::8a2e:370:7334"
        results = engine.detect(text, confidence_threshold=0.2)
        ips = [r for r in results if r["category"] == "IP"]
        assert len(ips) >= 1

    def test_ipv6_loopback_excluded(self, engine):
        text = "Localhost is ::1 on this machine."
        results = engine.detect(text, confidence_threshold=0.2)
        ips = [r for r in results if r["category"] == "IP"]
        assert not any("::1" == i["original_value"] for i in ips)

    def test_ipv6_link_local_excluded(self, engine):
        text = "Link-local: fe80::1"
        results = engine.detect(text, confidence_threshold=0.2)
        ips = [r for r in results if r["category"] == "IP"]
        assert not any(i["original_value"].startswith("fe80::") for i in ips)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestIPHardening -v`
Expected: FAIL.

- [ ] **Step 3: Implement IPv6 recognizer and IPv4+port handling**

Add a custom `EntityRecognizer` for IPv6 that:
1. Matches full IPv6 addresses (8 groups of 4 hex digits separated by colons)
2. Matches compressed IPv6 (with `::`)
3. Excludes loopback (`::1`) and link-local (`fe80::`)
4. For IPv4 with port, extend the existing detection or add a pattern that captures `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}`

Add post-detection filtering in `detect()` for IPv6 loopback/link-local exclusions (similar to how DOB and URL filtering works).

Register in `__init__()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestIPHardening -v`
Expected: All pass.

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::test_detect_ip_address -v`
Expected: Existing test still passes.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "feat: add IPv6 detection and IPv4+port handling"
```

---

### Task 11: Email enhancement (spec section 7)

**Files:**
- Modify: `pii_washer/pii_detection_engine.py`
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write failing tests**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
# --- Email Enhancement ---

class TestEmailHardening:
    def test_email_plus_addressing(self, engine):
        text = "Send to user+newsletter@gmail.com for updates."
        results = engine.detect(text, confidence_threshold=0.2)
        emails = [r for r in results if r["category"] == "EMAIL"]
        assert len(emails) >= 1

    def test_email_subdomain(self, engine):
        text = "Contact admin@mail.company.com for help."
        results = engine.detect(text, confidence_threshold=0.2)
        emails = [r for r in results if r["category"] == "EMAIL"]
        assert len(emails) >= 1

    def test_email_obfuscated_at(self, engine):
        text = "Reach me at john [at] example.com anytime."
        results = engine.detect(text, confidence_threshold=0.2)
        emails = [r for r in results if r["category"] == "EMAIL"]
        assert len(emails) >= 1

    def test_email_obfuscated_at_parens(self, engine):
        text = "Contact john(at)example.com for info."
        results = engine.detect(text, confidence_threshold=0.2)
        emails = [r for r in results if r["category"] == "EMAIL"]
        assert len(emails) >= 1

    def test_email_obfuscated_dot(self, engine):
        text = "Email: john@example [dot] com"
        results = engine.detect(text, confidence_threshold=0.2)
        emails = [r for r in results if r["category"] == "EMAIL"]
        assert len(emails) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestEmailHardening -v`
Expected: FAIL — obfuscated emails not recognized.

- [ ] **Step 3: Implement obfuscated email recognizer**

Add a `PatternRecognizer` with patterns for:
- `\b[a-zA-Z0-9._%+-]+\s*[\[\(]at[\]\)]\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b` (obfuscated @)
- `\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\s*[\[\(]dot[\]\)]\s*[a-zA-Z]{2,}\b` (obfuscated .)
- `\b[a-zA-Z0-9._%+-]+\s*[\[\(]at[\]\)]\s*[a-zA-Z0-9.-]+\s*[\[\(]dot[\]\)]\s*[a-zA-Z]{2,}\b` (both obfuscated)

Confidence: 0.5 for obfuscated patterns.
Entity type: `EMAIL_ADDRESS` (maps to `EMAIL`).

Note: Plus addressing and subdomain emails should already work with Presidio's built-in `EmailRecognizer`. Verify first — if they do, only add the obfuscated patterns.

Register in `__init__()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestEmailHardening -v`
Expected: All pass.

Run: `pytest pii_washer/tests/test_pii_detection_engine.py -k "email" -v`
Expected: All existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "feat: add obfuscated email detection"
```

---

### Task 12: Context filter loosening (spec section 8)

**Files:**
- Modify: `pii_washer/pii_detection_engine.py`
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write failing tests**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
# --- Context Filter Loosening ---

class TestContextFilters:
    # DOB expanded keywords
    def test_dob_keyword_d_o_b(self, engine):
        text = "d.o.b: 03/15/1990 is the patient record."
        results = engine.detect(text, confidence_threshold=0.2)
        dobs = [r for r in results if r["category"] == "DOB"]
        assert len(dobs) >= 1

    def test_dob_keyword_birth_year(self, engine):
        text = "Birth year: 1990. Admission: 2024."
        results = engine.detect(text, confidence_threshold=0.2)
        dobs = [r for r in results if r["category"] == "DOB"]
        assert any("1990" in d["original_value"] for d in dobs)

    def test_dob_wider_context_window(self, engine):
        """DOB keyword 80 chars before the date (was outside old 50-char window)."""
        text = "The patient's date of birth is recorded as follows in the system records: March 5, 1990."
        results = engine.detect(text, confidence_threshold=0.2)
        dobs = [r for r in results if r["category"] == "DOB"]
        assert len(dobs) >= 1

    # DOB keywordless detection (very low confidence)
    def test_dob_keywordless_mm_dd_yyyy(self, engine):
        """Date without keywords should still be detected at very low confidence."""
        text = "The document was signed on 03/15/1990 by the parties."
        results = engine.detect(text, confidence_threshold=0.2)
        dobs = [r for r in results if r["category"] == "DOB"]
        assert len(dobs) >= 1
        assert all(d["confidence"] <= 0.3 for d in dobs)  # low confidence

    def test_dob_keywordless_month_dd_yyyy(self, engine):
        text = "The event occurred on March 15, 1990 at the venue."
        results = engine.detect(text, confidence_threshold=0.2)
        dobs = [r for r in results if r["category"] == "DOB"]
        assert len(dobs) >= 1

    # ZIP expanded context
    def test_zip_with_city_context(self, engine):
        text = "Houston 77001 is the destination."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("77001" in a["original_value"] for a in addresses)

    def test_zip_with_keyword_context(self, engine):
        text = "Zip code: 90210"
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("90210" in a["original_value"] for a in addresses)

    def test_zip_with_postal_keyword(self, engine):
        text = "Postal code 62704 for Springfield."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert any("62704" in a["original_value"] for a in addresses)

    # URL expanded platforms
    def test_url_reddit(self, engine):
        text = "Profile: https://reddit.com/user/johndoe"
        results = engine.detect(text, confidence_threshold=0.2)
        urls = [r for r in results if r["category"] == "URL"]
        assert len(urls) >= 1

    def test_url_tiktok(self, engine):
        text = "Follow me: https://tiktok.com/@johndoe"
        results = engine.detect(text, confidence_threshold=0.2)
        urls = [r for r in results if r["category"] == "URL"]
        assert len(urls) >= 1

    def test_url_profile_path_heuristic(self, engine):
        text = "See https://example.com/profile/johndoe123 for details."
        results = engine.detect(text, confidence_threshold=0.2)
        urls = [r for r in results if r["category"] == "URL"]
        assert len(urls) >= 1

    def test_url_profile_path_not_settings(self, engine):
        """Profile path followed by 'settings' should NOT match."""
        text = "Go to https://example.com/user/settings to update."
        results = engine.detect(text, confidence_threshold=0.2)
        urls = [r for r in results if r["category"] == "URL"]
        # Should not flag this as PII — "settings" is not a username
        assert len(urls) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestContextFilters -v`
Expected: FAIL.

- [ ] **Step 3: Update context filters**

In `pii_washer/pii_detection_engine.py`:

1. **DOB changes:**
   - Expand `DOB_CONTEXT_KEYWORDS`: add `"d.o.b"`, `"b."`, `"born on"`, `"birth year"` (note: `"age"`, `"dob"`, and `"date of birth"` are already in the existing list and cover `"age:"`, `"DOB:"`, `"Date of Birth:"` via substring matching)
   - Change `DOB_CONTEXT_WINDOW` from 50 to 100
   - Add keywordless date detection: modify the DOB filtering logic so dates in MM/DD/YYYY, Month DD YYYY, and MM-DD-YYYY formats pass through at confidence 0.2 even when `_has_dob_context()` returns False. Instead of `continue` on no context, set `confidence = 0.2` for those matches. This surfaces speculative date matches for user review.

2. **ZIP changes:**
   - Change `ZIP_CONTEXT_WINDOW` from 100 to 150
   - Load `us_cities_top200.json` at init time into `self._us_cities`
   - Add `ZIP_CONTEXT_KEYWORDS = ["zip", "zip code", "postal", "postal code"]`
   - Update `_has_zip_context()` to also check city names and ZIP keywords

3. **URL changes:**
   - Expand `PII_URL_PATTERNS` with new platforms:
     ```python
     "reddit.com/user/", "reddit.com/u/",
     "tiktok.com/@",
     "medium.com/@",
     "youtube.com/@", "youtube.com/channel/",
     "pinterest.com/",
     "tumblr.com/",
     "mastodon.social/@",
     "threads.net/@",
     "bsky.app/profile/",
     "stackoverflow.com/users/",
     "gitlab.com/",
     "bitbucket.org/",
     ```
   - Add profile path heuristic to `_is_pii_url()`:
     ```python
     PROFILE_PATH_PATTERNS = ["/user/", "/u/", "/profile/", "/~", "/people/", "/@"]
     NON_USERNAME_WORDS = ["settings", "update", "edit", "delete", "admin", "login", "signup", "search", "help", "about", "new", "create"]
     ```
     Check if URL contains a profile path pattern followed by what looks like a username (not a non-username word).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestContextFilters -v`
Expected: All pass.

Run: `pytest pii_washer/tests/test_pii_detection_engine.py -k "dob or zip or url" -v`
Expected: All existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "feat: loosen context filters for DOB, ZIP, and URL detection"
```

---

### Task 13: Lower default confidence threshold

**Files:**
- Modify: `pii_washer/pii_detection_engine.py`
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write test for new default threshold**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
def test_default_threshold_is_0_2():
    assert PIIDetectionEngine.DEFAULT_CONFIDENCE_THRESHOLD == 0.2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::test_default_threshold_is_0_2 -v`
Expected: FAIL — currently 0.3.

- [ ] **Step 3: Update the constant and `detect()` default**

In `pii_washer/pii_detection_engine.py`:

1. Change `DEFAULT_CONFIDENCE_THRESHOLD = 0.3` to `DEFAULT_CONFIDENCE_THRESHOLD = 0.2`
2. Update the `detect()` method signature: `confidence_threshold: float = 0.2`

- [ ] **Step 4: Run full test suite**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py -v`
Expected: All pass. Some existing tests may need adjustment if the lower threshold now surfaces additional detections — update assertions if needed (e.g., `len(results) >= 1` style assertions should be fine, but exact count assertions may need updating).

Also run: `pytest pii_washer/tests/ -v`
Expected: Full suite passes. Check `test_session_manager.py` and other integration tests that might call `detect()` with the default threshold.

- [ ] **Step 5: Commit**

```bash
git add pii_washer/pii_detection_engine.py pii_washer/tests/test_pii_detection_engine.py
git commit -m "feat: lower default confidence threshold from 0.3 to 0.2"
```

---

### Task 14: Integration tests and false positive tests

**Files:**
- Modify: `pii_washer/tests/test_pii_detection_engine.py`

- [ ] **Step 1: Write integration and false positive tests**

Add to `pii_washer/tests/test_pii_detection_engine.py`:

```python
# --- Integration Tests ---

class TestDetectionIntegration:
    def test_document_with_new_formats(self, engine):
        """Document using several new format variants."""
        text = (
            "Patient: Jane Doe\n"
            "SSN: 219 09 9999\n"
            "Phone: 555.867.5309\n"
            "Email: jane(at)example.com\n"
            "Address: P.O. Box 1234, Houston 77001\n"
            "DOB: d.o.b 03/15/1990\n"
            "Card: 4111 1111 1111 1111\n"
            "Profile: https://reddit.com/user/janedoe\n"
        )
        results = engine.detect(text, confidence_threshold=0.2)
        categories = {r["category"] for r in results}
        assert "NAME" in categories, "Jane Doe should be detected"
        assert "SSN" in categories, "Spaced SSN should be detected"
        assert "PHONE" in categories, "Dotted phone should be detected"
        assert "EMAIL" in categories, "Obfuscated email should be detected"
        assert "ADDRESS" in categories, "PO Box should be detected"
        assert "DOB" in categories, "DOB with d.o.b keyword should be detected"
        assert "CCN" in categories, "Spaced card number should be detected"
        assert "URL" in categories, "Reddit profile should be detected"

    def test_mixed_old_and_new_formats(self, engine):
        """Document mixing original formats with new ones."""
        text = (
            "Contact Mr. John Smith at john@example.com or 555.867.5309.\n"
            "SSN: 219-09-9999 (also written as 219 09 9999).\n"
            "Lives at 742 Evergreen Terrace, Springfield, IL 62704.\n"
            "Also check P.O. Box 500.\n"
        )
        results = engine.detect(text, confidence_threshold=0.2)
        assert len(results) >= 6  # At minimum: name, email, phone, SSN, address, zip


# --- False Positive Tests ---

class TestFalsePositives:
    def test_nine_digit_order_number(self, engine):
        """9-digit number without SSN context should not be flagged as SSN."""
        text = "Your order number is 123456789. Thank you for shopping."
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert len(ssns) == 0

    def test_ten_digit_isbn(self, engine):
        """10-digit ISBN should not be flagged as phone."""
        text = "ISBN: 0471958697 is the book identifier."
        results = engine.detect(text, confidence_threshold=0.2)
        phones = [r for r in results if r["category"] == "PHONE"]
        assert len(phones) == 0

    def test_year_not_zip(self, engine):
        """A year in prose should not be a zip code."""
        text = "The company was founded in 2024 by the board."
        results = engine.detect(text, confidence_threshold=0.2)
        addresses = [r for r in results if r["category"] == "ADDRESS"]
        assert not any("2024" in a["original_value"] for a in addresses)

    def test_financial_numbers_not_ssn(self, engine):
        """Financial report numbers shouldn't trigger SSN detection."""
        text = "Revenue was 458923100 dollars in Q3. Expenses were 312847000 dollars."
        results = engine.detect(text, confidence_threshold=0.2)
        ssns = [r for r in results if r["category"] == "SSN"]
        assert len(ssns) == 0

    def test_company_name_not_person(self, engine):
        """Known organization patterns should not be flagged as names by our heuristic."""
        text = "She works at Goldman Sachs and previously at Morgan Stanley."
        results = engine.detect(text, confidence_threshold=0.2)
        names = [r for r in results if r["category"] == "NAME"]
        # Our capitalized pair heuristic should not flag these — NER may classify as ORG
        assert not any("Goldman Sachs" in n["original_value"] for n in names)
        assert not any("Morgan Stanley" in n["original_value"] for n in names)

    def test_month_day_not_name(self, engine):
        """Month + day name pair should not be detected as a person name."""
        text = "The event is on Saturday January at the conference center."
        results = engine.detect(text, confidence_threshold=0.2)
        names = [r for r in results if r["category"] == "NAME"]
        assert not any("Saturday January" in n["original_value"] for n in names)
```

- [ ] **Step 2: Run tests**

Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestDetectionIntegration -v`
Run: `pytest pii_washer/tests/test_pii_detection_engine.py::TestFalsePositives -v`
Expected: All pass.

- [ ] **Step 3: Fix any failing tests**

If any fail, adjust the detection logic or test expectations. The false positive tests are critical — if they fail, the detection is too aggressive and needs tightening.

- [ ] **Step 4: Commit**

```bash
git add pii_washer/tests/test_pii_detection_engine.py
git commit -m "test: add integration and false positive tests for detection refinement"
```

---

### Task 15: Full regression test run and cleanup

**Files:**
- All modified files

- [ ] **Step 1: Run the full test suite**

Run: `pytest pii_washer/tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Run the full test suite with the new threshold**

Run: `pytest pii_washer/tests/ -v --tb=long`
Look for any tests that broke due to the lower threshold surfacing new detections. Fix assertion counts or filter logic as needed.

- [ ] **Step 3: Run informal performance benchmark**

Time the detection engine on a multi-paragraph sample before and after changes. Target: no more than 2x slowdown. Use the rich document from the existing test as a sample:

```python
import time
from pii_washer.pii_detection_engine import PIIDetectionEngine

engine = PIIDetectionEngine()
text = "Dear Dr. Jane Doe,\n\nYour SSN 456-78-9012 is on file. Please contact us at support@clinic.com\nor call (555) 987-6543. Your date of birth January 15, 1985 has been verified.\nYour address is 742 Evergreen Terrace, Springfield, IL 62704.\n\nRegards,\nSpringfield Medical Center"

start = time.perf_counter()
for _ in range(10):
    engine.detect(text, confidence_threshold=0.2)
elapsed = (time.perf_counter() - start) / 10
print(f"Average detection time: {elapsed:.3f}s")
```

Run this before and after changes and compare. If > 2x slower, investigate which recognizer is the bottleneck.

- [ ] **Step 4: Check for any linting issues**

Run: `python -m py_compile pii_washer/pii_detection_engine.py && python -m py_compile pii_washer/name_recognizer.py`
Expected: No syntax errors.

- [ ] **Step 5: Commit any fixes**

```bash
git add -u
git commit -m "fix: address regression test failures from detection refinement"
```

(Skip this step if no fixes were needed.)

---

### Task 16: Update roadmap

**Files:**
- Modify: `archive/pii-washer-roadmap.md`

- [ ] **Step 1: Update the roadmap entry**

Change "Detection refinement" status from `TBD — needs brainstorm session` to `Complete — shipped [date]`.

- [ ] **Step 2: Commit**

```bash
git add archive/pii-washer-roadmap.md
git commit -m "docs: mark detection refinement as complete on roadmap"
```
