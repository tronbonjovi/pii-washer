"""Tests for PII Shield — Component 4: Text Substitution Engine."""

import copy

import pytest

from pii_shield.text_substitution_engine import TextSubstitutionEngine


def make_detection(original_value, placeholder, positions, status="confirmed", **kwargs):
    """Create a detection dict for testing."""
    d = {
        "id": kwargs.get("id", "pii_001"),
        "category": kwargs.get("category", "NAME"),
        "original_value": original_value,
        "placeholder": placeholder,
        "status": status,
        "positions": positions,
        "confidence": kwargs.get("confidence", 0.85),
    }
    return d


# ---------------------------------------------------------------------------
# Depersonalize — Basic
# ---------------------------------------------------------------------------

class TestDepersonalizeBasic:

    def test_depersonalize_single_replacement(self):
        engine = TextSubstitutionEngine()
        text = "My name is John Smith and I live here."
        detections = [make_detection("John Smith", "[Person_1]", [{"start": 11, "end": 21}])]
        result = engine.depersonalize(text, detections)
        assert result == "My name is [Person_1] and I live here."

    def test_depersonalize_multiple_replacements(self):
        engine = TextSubstitutionEngine()
        text = "Contact John Smith at john@example.com or (555) 123-4567."
        detections = [
            make_detection("John Smith", "[Person_1]", [{"start": 8, "end": 18}]),
            make_detection("john@example.com", "[Email_1]", [{"start": 22, "end": 38}], category="EMAIL"),
            make_detection("(555) 123-4567", "[Phone_1]", [{"start": 42, "end": 56}], category="PHONE"),
        ]
        result = engine.depersonalize(text, detections)
        assert "[Person_1]" in result
        assert "[Email_1]" in result
        assert "[Phone_1]" in result
        assert "John Smith" not in result
        assert "john@example.com" not in result
        assert "(555) 123-4567" not in result

    def test_depersonalize_same_value_multiple_positions(self):
        engine = TextSubstitutionEngine()
        text = "John Smith filed the report. Later, John Smith was contacted."
        detections = [
            make_detection("John Smith", "[Person_1]", [{"start": 0, "end": 10}, {"start": 36, "end": 46}]),
        ]
        result = engine.depersonalize(text, detections)
        assert "John Smith" not in result
        assert result.count("[Person_1]") == 2

    def test_depersonalize_preserves_surrounding_text(self):
        engine = TextSubstitutionEngine()
        text = "Hello, John Smith! How are you today?"
        detections = [make_detection("John Smith", "[Person_1]", [{"start": 7, "end": 17}])]
        result = engine.depersonalize(text, detections)
        assert result == "Hello, [Person_1]! How are you today?"


# ---------------------------------------------------------------------------
# Depersonalize — Status Filtering
# ---------------------------------------------------------------------------

class TestDepersonalizeStatusFiltering:

    def test_depersonalize_only_confirmed(self):
        engine = TextSubstitutionEngine()
        text = "John Smith and Jane Doe went to Springfield."
        detections = [
            make_detection("John Smith", "[Person_1]", [{"start": 0, "end": 10}], status="confirmed"),
            make_detection("Jane Doe", "[Person_2]", [{"start": 15, "end": 23}], status="rejected"),
            make_detection("Springfield", "[Address_1]", [{"start": 32, "end": 43}], status="pending", category="ADDRESS"),
        ]
        result = engine.depersonalize(text, detections)
        assert "John Smith" not in result
        assert "Jane Doe" in result
        assert "Springfield" in result

    def test_depersonalize_no_status_field(self):
        engine = TextSubstitutionEngine()
        text = "John Smith lives here."
        det = {
            "id": "pii_001",
            "category": "NAME",
            "original_value": "John Smith",
            "placeholder": "[Person_1]",
            "positions": [{"start": 0, "end": 10}],
            "confidence": 0.85,
        }
        result = engine.depersonalize(text, [det])
        assert "John Smith" not in result
        assert "[Person_1]" in result

    def test_depersonalize_all_rejected(self):
        engine = TextSubstitutionEngine()
        text = "John Smith and Jane Doe."
        detections = [
            make_detection("John Smith", "[Person_1]", [{"start": 0, "end": 10}], status="rejected"),
            make_detection("Jane Doe", "[Person_2]", [{"start": 15, "end": 23}], status="rejected"),
        ]
        result = engine.depersonalize(text, detections)
        assert result == text


# ---------------------------------------------------------------------------
# Depersonalize — Empty/Edge Cases
# ---------------------------------------------------------------------------

class TestDepersonalizeEdgeCases:

    def test_depersonalize_empty_detections(self):
        engine = TextSubstitutionEngine()
        result = engine.depersonalize("No PII here.", [])
        assert result == "No PII here."

    def test_depersonalize_empty_text_raises(self):
        engine = TextSubstitutionEngine()
        with pytest.raises(ValueError, match="cannot be empty"):
            engine.depersonalize("", [make_detection("John", "[Person_1]", [{"start": 0, "end": 4}])])

    def test_depersonalize_not_a_list_raises(self):
        engine = TextSubstitutionEngine()
        with pytest.raises(TypeError, match="Expected a list"):
            engine.depersonalize("text", "not a list")

    def test_depersonalize_missing_field_raises(self):
        engine = TextSubstitutionEngine()
        det = {"original_value": "John", "positions": [{"start": 0, "end": 4}]}
        with pytest.raises(ValueError, match="missing required field"):
            engine.depersonalize("John is here.", [det])


# ---------------------------------------------------------------------------
# Depersonalize — Position Ordering
# ---------------------------------------------------------------------------

class TestDepersonalizePositionOrdering:

    def test_depersonalize_right_to_left(self):
        engine = TextSubstitutionEngine()
        text = "A B C"
        detections = [
            make_detection("A", "[Person_1]", [{"start": 0, "end": 1}]),
            make_detection("B", "[Person_2]", [{"start": 2, "end": 3}]),
            make_detection("C", "[Person_3]", [{"start": 4, "end": 5}]),
        ]
        result = engine.depersonalize(text, detections)
        assert "[Person_1]" in result
        assert "[Person_2]" in result
        assert "[Person_3]" in result
        assert "A" not in result.replace("[Person_1]", "").replace("[Person_2]", "").replace("[Person_3]", "").replace("ddress", "")

    def test_depersonalize_different_length_replacements(self):
        engine = TextSubstitutionEngine()
        text = "Hi Jo, meet Bob today."
        detections = [
            make_detection("Jo", "[Person_1]", [{"start": 3, "end": 5}]),
            make_detection("Bob", "[Person_2]", [{"start": 12, "end": 15}]),
        ]
        result = engine.depersonalize(text, detections)
        assert result == "Hi [Person_1], meet [Person_2] today."


# ---------------------------------------------------------------------------
# Depersonalize — Overlap Defense
# ---------------------------------------------------------------------------

class TestDepersonalizeOverlap:

    def test_depersonalize_overlapping_positions_skipped(self):
        engine = TextSubstitutionEngine()
        text = "John Smith is here."
        detections = [
            make_detection("John Smith", "[Person_1]", [{"start": 0, "end": 10}]),
            make_detection("John", "[Person_2]", [{"start": 0, "end": 4}]),
        ]
        result = engine.depersonalize(text, detections)
        assert "[Person_1]" in result
        assert "[Person_2]" not in result
        assert "John" not in result.replace("[Person_1]", "")


# ---------------------------------------------------------------------------
# Repersonalize — Basic
# ---------------------------------------------------------------------------

class TestRepersonalizeBasic:

    def test_repersonalize_single_replacement(self):
        engine = TextSubstitutionEngine()
        text = "Dear [Person_1], your application is approved."
        detections = [make_detection("John Smith", "[Person_1]", [])]
        result = engine.repersonalize(text, detections)
        assert result["text"] == "Dear John Smith, your application is approved."
        assert "[Person_1]" in result["matched"]
        assert result["unmatched_from_map"] == []

    def test_repersonalize_multiple_replacements(self):
        engine = TextSubstitutionEngine()
        text = "[Person_1] can be reached at [Email_1] or [Phone_1]."
        detections = [
            make_detection("John Smith", "[Person_1]", []),
            make_detection("john@example.com", "[Email_1]", [], category="EMAIL"),
            make_detection("(555) 123-4567", "[Phone_1]", [], category="PHONE"),
        ]
        result = engine.repersonalize(text, detections)
        assert "John Smith" in result["text"]
        assert "john@example.com" in result["text"]
        assert "(555) 123-4567" in result["text"]
        assert len(result["matched"]) == 3

    def test_repersonalize_same_placeholder_multiple_occurrences(self):
        engine = TextSubstitutionEngine()
        text = "[Person_1] filed the report. Later, [Person_1] was contacted."
        detections = [make_detection("John Smith", "[Person_1]", [])]
        result = engine.repersonalize(text, detections)
        assert result["text"].count("John Smith") == 2
        assert "[Person_1]" not in result["text"]


# ---------------------------------------------------------------------------
# Repersonalize — Unmatched Placeholders
# ---------------------------------------------------------------------------

class TestRepersonalizeUnmatched:

    def test_repersonalize_unmatched_from_map(self):
        engine = TextSubstitutionEngine()
        text = "[Person_1] sent a message."
        detections = [
            make_detection("John Smith", "[Person_1]", []),
            make_detection("123 Main St", "[Address_1]", [], category="ADDRESS"),
        ]
        result = engine.repersonalize(text, detections)
        assert "[Person_1]" in result["matched"]
        assert "[Address_1]" in result["unmatched_from_map"]

    def test_repersonalize_unknown_in_text(self):
        engine = TextSubstitutionEngine()
        text = "[Person_1] met with [Person_5] today."
        detections = [make_detection("John Smith", "[Person_1]", [])]
        result = engine.repersonalize(text, detections)
        assert "John Smith" in result["text"]
        assert "[Person_5]" in result["unknown_in_text"]
        assert "[Person_5]" in result["text"]

    def test_repersonalize_all_unmatched(self):
        engine = TextSubstitutionEngine()
        text = "The weather is nice today."
        detections = [
            make_detection("John Smith", "[Person_1]", []),
            make_detection("Jane Doe", "[Person_2]", []),
        ]
        result = engine.repersonalize(text, detections)
        assert result["matched"] == []
        assert "[Person_1]" in result["unmatched_from_map"]
        assert "[Person_2]" in result["unmatched_from_map"]


# ---------------------------------------------------------------------------
# Repersonalize — Match Summary
# ---------------------------------------------------------------------------

class TestRepersonalizeMatchSummary:

    def test_repersonalize_summary_all_matched(self):
        engine = TextSubstitutionEngine()
        text = "[Person_1] at [Email_1] and [Phone_1]."
        detections = [
            make_detection("John Smith", "[Person_1]", []),
            make_detection("john@example.com", "[Email_1]", [], category="EMAIL"),
            make_detection("555-1234", "[Phone_1]", [], category="PHONE"),
        ]
        result = engine.repersonalize(text, detections)
        assert "3/3" in result["match_summary"]
        assert "matched" in result["match_summary"]

    def test_repersonalize_summary_some_unmatched(self):
        engine = TextSubstitutionEngine()
        text = "[Person_1] is here."
        detections = [
            make_detection("John Smith", "[Person_1]", []),
            make_detection("Jane Doe", "[Person_2]", []),
        ]
        result = engine.repersonalize(text, detections)
        assert "1/2" in result["match_summary"]
        assert "[Person_2]" in result["match_summary"]

    def test_repersonalize_summary_empty_map(self):
        engine = TextSubstitutionEngine()
        text = "Hello world."
        result = engine.repersonalize(text, [])
        assert "No placeholders to match" in result["match_summary"]


# ---------------------------------------------------------------------------
# Repersonalize — Status Filtering
# ---------------------------------------------------------------------------

class TestRepersonalizeStatusFiltering:

    def test_repersonalize_only_confirmed(self):
        engine = TextSubstitutionEngine()
        text = "[Person_1] and [Person_2] were present."
        detections = [
            make_detection("John Smith", "[Person_1]", [], status="confirmed"),
            make_detection("Jane Doe", "[Person_2]", [], status="rejected"),
        ]
        result = engine.repersonalize(text, detections)
        assert "John Smith" in result["text"]
        assert "[Person_2]" in result["text"]
        assert "[Person_2]" in result["unknown_in_text"]


# ---------------------------------------------------------------------------
# Repersonalize — Replacement Order
# ---------------------------------------------------------------------------

class TestRepersonalizeReplacementOrder:

    def test_repersonalize_longest_placeholder_first(self):
        engine = TextSubstitutionEngine()
        text = "Talk to [Person_1] and [Person_10] today."
        detections = [
            make_detection("Alice", "[Person_1]", []),
            make_detection("Bob", "[Person_10]", []),
        ]
        result = engine.repersonalize(text, detections)
        assert "Alice" in result["text"]
        assert "Bob" in result["text"]
        assert "[Person_1]" not in result["text"]
        assert "[Person_10]" not in result["text"]


# ---------------------------------------------------------------------------
# Repersonalize — Empty/Edge Cases
# ---------------------------------------------------------------------------

class TestRepersonalizeEdgeCases:

    def test_repersonalize_empty_detections(self):
        engine = TextSubstitutionEngine()
        result = engine.repersonalize("Hello world.", [])
        assert result["text"] == "Hello world."
        assert result["matched"] == []
        assert result["unmatched_from_map"] == []

    def test_repersonalize_empty_text_raises(self):
        engine = TextSubstitutionEngine()
        with pytest.raises(ValueError, match="cannot be empty"):
            engine.repersonalize("", [make_detection("John", "[Person_1]", [])])

    def test_repersonalize_not_a_list_raises(self):
        engine = TextSubstitutionEngine()
        with pytest.raises(TypeError, match="Expected a list"):
            engine.repersonalize("text", "not a list")

    def test_repersonalize_missing_field_raises(self):
        engine = TextSubstitutionEngine()
        det = {"placeholder": "[Person_1]"}
        with pytest.raises(ValueError, match="missing required field"):
            engine.repersonalize("[Person_1] is here.", [det])


# ---------------------------------------------------------------------------
# Build Replacement Map
# ---------------------------------------------------------------------------

class TestBuildReplacementMap:

    def test_build_map_depersonalize(self):
        engine = TextSubstitutionEngine()
        detections = [
            make_detection("John Smith", "[Person_1]", []),
            make_detection("john@example.com", "[Email_1]", [], category="EMAIL"),
        ]
        result = engine.build_replacement_map(detections, "depersonalize")
        assert result == {"John Smith": "[Person_1]", "john@example.com": "[Email_1]"}

    def test_build_map_repersonalize(self):
        engine = TextSubstitutionEngine()
        detections = [
            make_detection("John Smith", "[Person_1]", []),
            make_detection("john@example.com", "[Email_1]", [], category="EMAIL"),
        ]
        result = engine.build_replacement_map(detections, "repersonalize")
        assert result == {"[Person_1]": "John Smith", "[Email_1]": "john@example.com"}

    def test_build_map_filters_by_status(self):
        engine = TextSubstitutionEngine()
        detections = [
            make_detection("John Smith", "[Person_1]", [], status="confirmed"),
            make_detection("Jane Doe", "[Person_2]", [], status="rejected"),
        ]
        result = engine.build_replacement_map(detections, "depersonalize")
        assert "John Smith" in result
        assert "Jane Doe" not in result

    def test_build_map_no_status_includes_all(self):
        engine = TextSubstitutionEngine()
        det1 = {"original_value": "John Smith", "placeholder": "[Person_1]", "positions": []}
        det2 = {"original_value": "Jane Doe", "placeholder": "[Person_2]", "positions": []}
        result = engine.build_replacement_map([det1, det2], "depersonalize")
        assert len(result) == 2

    def test_build_map_invalid_direction(self):
        engine = TextSubstitutionEngine()
        detections = [make_detection("John", "[Person_1]", [])]
        with pytest.raises(ValueError, match="Invalid direction"):
            engine.build_replacement_map(detections, "sideways")


# ---------------------------------------------------------------------------
# Round-Trip Integration
# ---------------------------------------------------------------------------

class TestRoundTrip:

    def test_full_round_trip(self):
        engine = TextSubstitutionEngine()
        text = "John Smith's email is john@example.com. Contact John Smith for details."
        detections = [
            make_detection("John Smith", "[Person_1]", [{"start": 0, "end": 10}, {"start": 48, "end": 58}]),
            make_detection("john@example.com", "[Email_1]", [{"start": 22, "end": 38}], category="EMAIL"),
        ]

        depersonalized = engine.depersonalize(text, detections)
        assert depersonalized == "[Person_1]'s email is [Email_1]. Contact [Person_1] for details."

        llm_response = "Dear [Person_1], I've updated your email [Email_1] in our system. Thank you, [Person_1]."
        result = engine.repersonalize(llm_response, detections)
        assert result["text"] == "Dear John Smith, I've updated your email john@example.com in our system. Thank you, John Smith."
        assert len(result["matched"]) == 2
        assert result["unmatched_from_map"] == []

    def test_round_trip_with_unmatched(self):
        engine = TextSubstitutionEngine()
        text = "John Smith lives at 123 Main St."
        detections = [
            make_detection("John Smith", "[Person_1]", [{"start": 0, "end": 10}]),
            make_detection("123 Main St", "[Address_1]", [{"start": 20, "end": 31}], category="ADDRESS"),
        ]

        depersonalized = engine.depersonalize(text, detections)
        assert "[Person_1]" in depersonalized
        assert "[Address_1]" in depersonalized

        llm_response = "Hello [Person_1], your request has been processed."
        result = engine.repersonalize(llm_response, detections)
        assert "[Person_1]" in result["matched"]
        assert "[Address_1]" in result["unmatched_from_map"]


# ---------------------------------------------------------------------------
# No Mutation of Input
# ---------------------------------------------------------------------------

class TestNoMutation:

    def test_depersonalize_input_not_mutated(self):
        engine = TextSubstitutionEngine()
        detections = [make_detection("John Smith", "[Person_1]", [{"start": 0, "end": 10}])]
        original = copy.deepcopy(detections)
        engine.depersonalize("John Smith is here.", detections)
        assert detections == original

    def test_repersonalize_input_not_mutated(self):
        engine = TextSubstitutionEngine()
        detections = [make_detection("John Smith", "[Person_1]", [])]
        original = copy.deepcopy(detections)
        engine.repersonalize("[Person_1] is here.", detections)
        assert detections == original


# ---------------------------------------------------------------------------
# Integration Readiness
# ---------------------------------------------------------------------------

class TestIntegrationReadiness:

    def test_depersonalize_output_is_string(self):
        engine = TextSubstitutionEngine()
        result = engine.depersonalize("John Smith", [
            make_detection("John Smith", "[Person_1]", [{"start": 0, "end": 10}]),
        ])
        assert isinstance(result, str)

    def test_repersonalize_output_structure(self):
        engine = TextSubstitutionEngine()
        result = engine.repersonalize("[Person_1] is here.", [
            make_detection("John Smith", "[Person_1]", []),
        ])
        assert isinstance(result, dict)
        expected_keys = {"text", "matched", "unmatched_from_map", "unknown_in_text", "match_summary"}
        assert set(result.keys()) == expected_keys
        assert isinstance(result["text"], str)
        assert isinstance(result["matched"], list)
        assert isinstance(result["unmatched_from_map"], list)
        assert isinstance(result["unknown_in_text"], list)
        assert isinstance(result["match_summary"], str)
