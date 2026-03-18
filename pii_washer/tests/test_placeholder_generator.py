"""Tests for Pii Washer Component 3: Placeholder Generator."""

import copy

import pytest

from pii_washer.placeholder_generator import PlaceholderGenerator


def make_detection(id, category, value, start, end, confidence=0.85):
    """Create a detection dict matching Component 2's output format."""
    return {
        "id": id,
        "category": category,
        "original_value": value,
        "positions": [{"start": start, "end": end}],
        "confidence": confidence,
    }


# --- Single Detection ---


class TestSingleDetection:
    def test_single_detection(self):
        gen = PlaceholderGenerator()
        detections = [make_detection("pii_001", "NAME", "John Smith", 10, 20)]
        result = gen.assign_placeholders(detections)

        assert len(result) == 1
        assert result[0]["placeholder"] == "[Person_1]"
        assert result[0]["id"] == "pii_001"
        assert result[0]["original_value"] == "John Smith"
        assert result[0]["category"] == "NAME"
        assert result[0]["confidence"] == 0.85
        assert result[0]["positions"] == [{"start": 10, "end": 20}]

    def test_single_email(self):
        gen = PlaceholderGenerator()
        detections = [make_detection("pii_001", "EMAIL", "john@example.com", 5, 21)]
        result = gen.assign_placeholders(detections)

        assert result[0]["placeholder"] == "[Email_1]"


# --- Multiple Detections — Different Categories ---


class TestDifferentCategories:
    def test_different_categories(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 0, 10),
            make_detection("pii_002", "EMAIL", "john@example.com", 30, 46),
            make_detection("pii_003", "PHONE", "(555) 123-4567", 60, 74),
        ]
        result = gen.assign_placeholders(detections)

        assert len(result) == 3
        assert result[0]["placeholder"] == "[Person_1]"
        assert result[1]["placeholder"] == "[Email_1]"
        assert result[2]["placeholder"] == "[Phone_1]"

    def test_all_categories(self):
        gen = PlaceholderGenerator()
        categories_and_prefixes = [
            ("NAME", "Person"),
            ("ADDRESS", "Address"),
            ("PHONE", "Phone"),
            ("EMAIL", "Email"),
            ("SSN", "SSN"),
            ("DOB", "DOB"),
            ("CCN", "CCN"),
            ("IP", "IP"),
            ("URL", "URL"),
        ]
        detections = [
            make_detection(f"pii_{i+1:03d}", cat, f"value_{cat}", i * 20, i * 20 + 10)
            for i, (cat, _) in enumerate(categories_and_prefixes)
        ]
        result = gen.assign_placeholders(detections)

        assert len(result) == 9
        for i, (cat, prefix) in enumerate(categories_and_prefixes):
            assert result[i]["placeholder"] == f"[{prefix}_1]"


# --- Multiple Values in Same Category ---


class TestMultipleValuesInCategory:
    def test_multiple_names(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 0, 10),
            make_detection("pii_002", "NAME", "Jane Doe", 50, 58),
        ]
        result = gen.assign_placeholders(detections)

        assert result[0]["original_value"] == "John Smith"
        assert result[0]["placeholder"] == "[Person_1]"
        assert result[1]["original_value"] == "Jane Doe"
        assert result[1]["placeholder"] == "[Person_2]"

    def test_numbering_by_first_occurrence(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "Jane Doe", 10, 18),
            make_detection("pii_002", "NAME", "John Smith", 50, 60),
        ]
        result = gen.assign_placeholders(detections)

        assert result[0]["original_value"] == "Jane Doe"
        assert result[0]["placeholder"] == "[Person_1]"
        assert result[1]["original_value"] == "John Smith"
        assert result[1]["placeholder"] == "[Person_2]"


# --- Deduplication / Consolidation ---


class TestDeduplication:
    def test_duplicate_value_same_placeholder(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 5, 15),
            make_detection("pii_002", "NAME", "John Smith", 100, 110),
            make_detection("pii_003", "NAME", "John Smith", 200, 210),
        ]
        result = gen.assign_placeholders(detections)

        assert len(result) == 1
        assert result[0]["placeholder"] == "[Person_1]"
        assert len(result[0]["positions"]) == 3

    def test_duplicate_positions_sorted(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 200, 210),
            make_detection("pii_002", "NAME", "John Smith", 5, 15),
            make_detection("pii_003", "NAME", "John Smith", 100, 110),
        ]
        result = gen.assign_placeholders(detections)

        positions = result[0]["positions"]
        assert positions == [
            {"start": 5, "end": 15},
            {"start": 100, "end": 110},
            {"start": 200, "end": 210},
        ]

    def test_duplicate_keeps_highest_confidence(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 5, 15, confidence=0.7),
            make_detection("pii_002", "NAME", "John Smith", 100, 110, confidence=0.95),
        ]
        result = gen.assign_placeholders(detections)

        assert result[0]["confidence"] == 0.95

    def test_duplicate_keeps_first_occurrence_value(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 5, 15),
            make_detection("pii_002", "NAME", "john smith", 100, 110),
        ]
        result = gen.assign_placeholders(detections)

        assert result[0]["original_value"] == "John Smith"


# --- Case-Insensitive Matching ---


class TestCaseInsensitive:
    def test_case_insensitive_dedup(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 5, 15),
            make_detection("pii_002", "NAME", "JOHN SMITH", 100, 110),
        ]
        result = gen.assign_placeholders(detections)

        assert len(result) == 1
        assert result[0]["placeholder"] == "[Person_1]"
        assert len(result[0]["positions"]) == 2

    def test_case_insensitive_different_categories_not_merged(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "ADDRESS", "Springfield", 5, 16),
            make_detection("pii_002", "ADDRESS", "springfield", 80, 91),
            make_detection("pii_003", "NAME", "Springfield", 200, 211),
        ]
        result = gen.assign_placeholders(detections)

        assert len(result) == 2

        address_entry = next(r for r in result if r["category"] == "ADDRESS")
        name_entry = next(r for r in result if r["category"] == "NAME")

        assert len(address_entry["positions"]) == 2
        assert len(name_entry["positions"]) == 1


# --- ID Reassignment ---


class TestIdReassignment:
    def test_ids_reassigned_sequentially(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_005", "NAME", "Alice", 0, 5),
            make_detection("pii_001", "EMAIL", "a@b.com", 10, 17),
            make_detection("pii_003", "PHONE", "555-1234", 20, 28),
        ]
        result = gen.assign_placeholders(detections)

        assert result[0]["id"] == "pii_001"
        assert result[1]["id"] == "pii_002"
        assert result[2]["id"] == "pii_003"

    def test_ids_format(self):
        gen = PlaceholderGenerator()
        categories = ["NAME", "ADDRESS", "PHONE", "EMAIL", "SSN", "DOB",
                       "CCN", "IP", "URL", "NAME", "ADDRESS", "PHONE"]
        detections = [
            make_detection(f"pii_{i+1:03d}", cat, f"unique_val_{i}", i * 20, i * 20 + 10)
            for i, cat in enumerate(categories)
        ]
        result = gen.assign_placeholders(detections)

        assert len(result) == 12
        for i, entry in enumerate(result, start=1):
            assert entry["id"] == f"pii_{i:03d}"


# --- Output Ordering ---


class TestOutputOrdering:
    def test_output_sorted_by_first_position(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "EMAIL", "a@b.com", 100, 107),
            make_detection("pii_002", "NAME", "John", 5, 9),
            make_detection("pii_003", "PHONE", "555-1234", 50, 58),
        ]
        result = gen.assign_placeholders(detections)

        assert result[0]["category"] == "NAME"
        assert result[1]["category"] == "PHONE"
        assert result[2]["category"] == "EMAIL"


# --- No Mutation of Input ---


class TestNoMutation:
    def test_input_not_mutated(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 5, 15),
            make_detection("pii_002", "EMAIL", "john@example.com", 30, 46),
        ]
        original = copy.deepcopy(detections)
        gen.assign_placeholders(detections)

        assert detections == original


# --- generate_placeholder Method ---


class TestGeneratePlaceholder:
    def test_generate_placeholder_name(self):
        gen = PlaceholderGenerator()
        assert gen.generate_placeholder("NAME", 1) == "[Person_1]"
        assert gen.generate_placeholder("NAME", 3) == "[Person_3]"

    def test_generate_placeholder_email(self):
        gen = PlaceholderGenerator()
        assert gen.generate_placeholder("EMAIL", 1) == "[Email_1]"

    def test_generate_placeholder_all_categories(self):
        gen = PlaceholderGenerator()
        expected = {
            "NAME": "Person", "ADDRESS": "Address", "PHONE": "Phone",
            "EMAIL": "Email", "SSN": "SSN", "DOB": "DOB",
            "CCN": "CCN", "IP": "IP", "URL": "URL",
        }
        for category, prefix in expected.items():
            assert gen.generate_placeholder(category, 1) == f"[{prefix}_1]"

    def test_generate_placeholder_invalid_category(self):
        gen = PlaceholderGenerator()
        with pytest.raises(ValueError, match="Unknown category"):
            gen.generate_placeholder("INVALID", 1)

    def test_generate_placeholder_invalid_counter(self):
        gen = PlaceholderGenerator()
        with pytest.raises(ValueError, match="positive integer"):
            gen.generate_placeholder("NAME", 0)
        with pytest.raises(ValueError, match="positive integer"):
            gen.generate_placeholder("NAME", -1)


# --- get_category_prefix_map Method ---


class TestGetCategoryPrefixMap:
    def test_get_category_prefix_map(self):
        gen = PlaceholderGenerator()
        prefix_map = gen.get_category_prefix_map()

        assert len(prefix_map) == 9
        assert prefix_map["NAME"] == "Person"
        assert prefix_map["EMAIL"] == "Email"
        assert all(k in PlaceholderGenerator.VALID_CATEGORIES for k in prefix_map)


# --- Validation Errors ---


class TestValidationErrors:
    def test_empty_detections_list(self):
        gen = PlaceholderGenerator()
        with pytest.raises(ValueError, match="cannot be empty"):
            gen.assign_placeholders([])

    def test_not_a_list(self):
        gen = PlaceholderGenerator()
        with pytest.raises(TypeError, match="Expected a list"):
            gen.assign_placeholders("not a list")
        with pytest.raises(TypeError, match="Expected a list"):
            gen.assign_placeholders(None)

    def test_detection_missing_field(self):
        gen = PlaceholderGenerator()
        bad_detection = {
            "id": "pii_001",
            "original_value": "John Smith",
            "positions": [{"start": 0, "end": 10}],
            "confidence": 0.85,
            # missing "category"
        }
        with pytest.raises(ValueError, match="missing required field"):
            gen.assign_placeholders([bad_detection])

    def test_detection_invalid_category(self):
        gen = PlaceholderGenerator()
        detections = [make_detection("pii_001", "BANANA", "value", 0, 5)]
        with pytest.raises(ValueError, match="Unknown category"):
            gen.assign_placeholders(detections)


# --- Integration Readiness ---


class TestIntegrationReadiness:
    def test_output_compatible_with_session_model(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 5, 15),
            make_detection("pii_002", "EMAIL", "john@example.com", 30, 46),
        ]
        result = gen.assign_placeholders(detections)

        expected_keys = {"id", "category", "original_value", "placeholder", "positions", "confidence"}
        for entry in result:
            assert set(entry.keys()) == expected_keys
            assert "status" not in entry

    def test_output_from_component_2_format(self):
        gen = PlaceholderGenerator()
        # Exactly what Component 2 would produce: no placeholder, no status, single position
        detections = [
            {
                "id": "pii_001",
                "category": "NAME",
                "original_value": "John Smith",
                "positions": [{"start": 0, "end": 10}],
                "confidence": 0.85,
            },
            {
                "id": "pii_002",
                "category": "EMAIL",
                "original_value": "john@example.com",
                "positions": [{"start": 25, "end": 41}],
                "confidence": 0.95,
            },
        ]
        result = gen.assign_placeholders(detections)

        assert all("placeholder" in entry for entry in result)


# --- Realistic Scenario ---


class TestRealisticScenario:
    def test_realistic_document(self):
        gen = PlaceholderGenerator()
        detections = [
            make_detection("pii_001", "NAME", "John Smith", 5, 15),
            make_detection("pii_002", "EMAIL", "john@example.com", 40, 58),
            make_detection("pii_003", "PHONE", "(555) 123-4567", 70, 85),
            make_detection("pii_004", "NAME", "John Smith", 120, 130),
            make_detection("pii_005", "NAME", "Jane Doe", 150, 158),
            make_detection("pii_006", "EMAIL", "john@example.com", 250, 268),
            make_detection("pii_007", "NAME", "John Smith", 300, 310),
        ]
        result = gen.assign_placeholders(detections)

        assert len(result) == 4

        # John Smith — first unique value at position 5
        john = result[0]
        assert john["original_value"] == "John Smith"
        assert john["placeholder"] == "[Person_1]"
        assert len(john["positions"]) == 3

        # john@example.com — first at position 40
        email = result[1]
        assert email["original_value"] == "john@example.com"
        assert email["placeholder"] == "[Email_1]"
        assert len(email["positions"]) == 2

        # Phone — position 70
        phone = result[2]
        assert phone["original_value"] == "(555) 123-4567"
        assert phone["placeholder"] == "[Phone_1]"
        assert len(phone["positions"]) == 1

        # Jane Doe — position 150, second unique NAME
        jane = result[3]
        assert jane["original_value"] == "Jane Doe"
        assert jane["placeholder"] == "[Person_2]"
        assert len(jane["positions"]) == 1
