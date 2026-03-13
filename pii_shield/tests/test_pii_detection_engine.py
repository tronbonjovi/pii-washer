import re

import pytest

from pii_shield.pii_detection_engine import PIIDetectionEngine


@pytest.fixture(scope="module")
def engine():
    """Initialize engine once for all tests in this module."""
    try:
        return PIIDetectionEngine("en_core_web_lg")
    except OSError:
        return PIIDetectionEngine("en_core_web_sm")


# --- Email Detection ---

def test_detect_email(engine):
    text = "Contact me at john.smith@example.com for details."
    results = engine.detect(text)
    emails = [r for r in results if r["category"] == "EMAIL"]
    assert len(emails) == 1
    assert emails[0]["original_value"] == "john.smith@example.com"
    start = emails[0]["positions"][0]["start"]
    end = emails[0]["positions"][0]["end"]
    assert text[start:end] == "john.smith@example.com"
    assert emails[0]["confidence"] > 0.0


def test_detect_multiple_emails(engine):
    text = "Email alice@example.com or bob@company.org for info."
    results = engine.detect(text)
    emails = [r for r in results if r["category"] == "EMAIL"]
    assert len(emails) >= 2


# --- Phone Number Detection ---

def test_detect_phone_parentheses(engine):
    text = "Call me at (555) 123-4567 today."
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1
    assert "555" in phones[0]["original_value"]
    assert "4567" in phones[0]["original_value"]


def test_detect_phone_dashes(engine):
    text = "My number is 555-123-4567."
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1


def test_detect_phone_international(engine):
    text = "Reach me at +1 (555) 123-4567 anytime."
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1


# --- SSN Detection ---

def test_detect_ssn(engine):
    text = "My SSN is 219-09-9999."
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) >= 1
    assert "219-09-9999" in ssns[0]["original_value"]


# --- Credit Card Detection ---

def test_detect_credit_card(engine):
    text = "Card number: 4111-1111-1111-1111"
    results = engine.detect(text)
    ccns = [r for r in results if r["category"] == "CCN"]
    assert len(ccns) >= 1


# --- IP Address Detection ---

def test_detect_ip_address(engine):
    text = "Server IP is 192.168.1.100 on the local network."
    results = engine.detect(text)
    ips = [r for r in results if r["category"] == "IP"]
    assert len(ips) >= 1
    assert "192.168.1.100" in ips[0]["original_value"]


# --- Name Detection (NER-based) ---

def test_detect_person_name(engine):
    text = "The application was submitted by John Smith on Monday."
    results = engine.detect(text)
    names = [r for r in results if r["category"] == "NAME"]
    assert len(names) >= 1
    assert any("John" in n["original_value"] for n in names)


def test_detect_multiple_names(engine):
    text = "Meeting attendees: Dr. Sarah Johnson and Professor Michael Williams discussed the proposal."
    results = engine.detect(text)
    names = [r for r in results if r["category"] == "NAME"]
    assert len(names) >= 2


# --- Location / Address Detection (NER-based) ---

def test_detect_location(engine):
    text = "She lives in Springfield, Illinois and works in Chicago."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert len(addresses) >= 1


# --- DOB Detection (Context-Filtered) ---

def test_detect_dob_with_context(engine):
    text = (
        "Patient was born on March 5, 1990. "
        "The patient was then referred to another facility and admitted on June 1, 2024."
    )
    results = engine.detect(text)
    dobs = [r for r in results if r["category"] == "DOB"]
    assert len(dobs) >= 1
    # The DOB near "born on" should be detected
    # The June 1 date should NOT be detected as DOB (no context keyword nearby)
    for dob in dobs:
        assert "June" not in dob["original_value"]


def test_detect_dob_keyword_dob(engine):
    text = "DOB: 03/05/1990 — Admission: 06/01/2024"
    results = engine.detect(text)
    dobs = [r for r in results if r["category"] == "DOB"]
    assert len(dobs) >= 1


def test_no_dob_without_context(engine):
    text = "The meeting is scheduled for January 15, 2025 at 3pm."
    results = engine.detect(text)
    dobs = [r for r in results if r["category"] == "DOB"]
    assert len(dobs) == 0


# --- URL Detection (PII-Filtered) ---

def test_detect_pii_url_linkedin(engine):
    text = "My profile: https://linkedin.com/in/johnsmith"
    results = engine.detect(text)
    urls = [r for r in results if r["category"] == "URL"]
    assert len(urls) >= 1


def test_detect_pii_url_github(engine):
    text = "Check my work at https://github.com/jsmith"
    results = engine.detect(text)
    urls = [r for r in results if r["category"] == "URL"]
    assert len(urls) >= 1


def test_no_generic_url(engine):
    text = "Visit https://www.google.com for more information."
    results = engine.detect(text)
    urls = [r for r in results if r["category"] == "URL"]
    assert len(urls) == 0


# --- Combined / Multi-Type Detection ---

def test_detect_mixed_pii(engine):
    text = "John Smith's email is john@example.com and his phone is (555) 123-4567."
    results = engine.detect(text)
    categories = {r["category"] for r in results}
    assert "NAME" in categories
    assert "EMAIL" in categories
    assert "PHONE" in categories


def test_detect_rich_document(engine):
    text = (
        "Dear Dr. Jane Doe,\n\n"
        "Your SSN 456-78-9012 is on file. Please contact us at support@clinic.com\n"
        "or call (555) 987-6543. Your date of birth January 15, 1985 has been verified.\n\n"
        "Regards,\nSpringfield Medical Center"
    )
    results = engine.detect(text)
    categories = {r["category"] for r in results}
    assert "NAME" in categories
    assert "SSN" in categories
    assert "EMAIL" in categories
    assert "PHONE" in categories
    assert "DOB" in categories


# --- No PII ---

def test_detect_no_pii(engine):
    text = "The weather today is sunny with a high of 75 degrees."
    results = engine.detect(text)
    assert results == []


# --- Output Structure ---

def test_detection_structure(engine):
    text = "Contact john@example.com for details."
    results = engine.detect(text)
    assert len(results) >= 1
    for det in results:
        assert set(det.keys()) == {"id", "category", "original_value", "positions", "confidence"}
        assert isinstance(det["id"], str)
        assert re.match(r"^pii_\d{3}$", det["id"])
        assert det["category"] in PIIDetectionEngine.VALID_CATEGORIES
        assert isinstance(det["original_value"], str) and len(det["original_value"]) > 0
        assert isinstance(det["positions"], list) and len(det["positions"]) >= 1
        for pos in det["positions"]:
            assert "start" in pos and "end" in pos
            assert isinstance(pos["start"], int)
            assert isinstance(pos["end"], int)
        assert isinstance(det["confidence"], float)
        assert 0.0 <= det["confidence"] <= 1.0
        assert "placeholder" not in det
        assert "status" not in det


def test_detection_ids_sequential(engine):
    text = "John Smith's email is john@example.com and his phone is (555) 123-4567."
    results = engine.detect(text)
    assert len(results) >= 2
    for i, det in enumerate(results, start=1):
        assert det["id"] == f"pii_{i:03d}"


def test_detection_sorted_by_position(engine):
    text = "Email: alice@test.com — Phone: (555) 111-2222 — Name: Bob Jones"
    results = engine.detect(text)
    starts = [r["positions"][0]["start"] for r in results]
    assert starts == sorted(starts)


def test_positions_match_original_value(engine):
    text = "My name is John Smith and my email is john@example.com."
    results = engine.detect(text)
    for det in results:
        start = det["positions"][0]["start"]
        end = det["positions"][0]["end"]
        assert text[start:end] == det["original_value"]


# --- Confidence Threshold ---

def test_confidence_threshold_default(engine):
    text = "Contact john@example.com for details."
    results = engine.detect(text)
    assert len(results) >= 1


def test_confidence_threshold_high(engine):
    text = "Contact john@example.com for details."
    results = engine.detect(text, confidence_threshold=0.99)
    for det in results:
        assert det["confidence"] >= 0.99


def test_confidence_threshold_zero(engine):
    text = "Contact john@example.com for details."
    results_zero = engine.detect(text, confidence_threshold=0.0)
    results_default = engine.detect(text, confidence_threshold=0.3)
    assert len(results_zero) >= len(results_default)


# --- Validation Errors ---

def test_detect_empty_text(engine):
    with pytest.raises(ValueError, match="cannot be empty"):
        engine.detect("")


def test_detect_invalid_threshold(engine):
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        engine.detect("test", confidence_threshold=1.5)
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        engine.detect("test", confidence_threshold=-0.1)


# --- Utility Methods ---

def test_get_supported_categories(engine):
    categories = engine.get_supported_categories()
    expected = ["NAME", "ADDRESS", "PHONE", "EMAIL", "SSN", "DOB", "CCN", "IP", "URL"]
    for cat in expected:
        assert cat in categories


def test_get_entity_mapping(engine):
    mapping = engine.get_entity_mapping()
    assert isinstance(mapping, dict)
    for value in mapping.values():
        assert value in PIIDetectionEngine.VALID_CATEGORIES
    assert "PERSON" in mapping
    assert "EMAIL_ADDRESS" in mapping
    assert "PHONE_NUMBER" in mapping


# --- Deduplication ---

def test_no_duplicate_exact_spans(engine):
    text = "John Smith's email is john@example.com and SSN is 123-45-6789."
    results = engine.detect(text)
    spans = [(r["positions"][0]["start"], r["positions"][0]["end"]) for r in results]
    assert len(spans) == len(set(spans))


# --- Integration Readiness ---

def test_output_compatible_with_session_storage(engine):
    text = "Contact john@example.com for details."
    results = engine.detect(text)
    assert len(results) >= 1
    for det in results:
        enriched = {**det, "placeholder": "[Test_1]", "status": "pending"}
        required_keys = {"id", "category", "original_value", "placeholder", "status", "positions", "confidence"}
        assert required_keys == set(enriched.keys())
