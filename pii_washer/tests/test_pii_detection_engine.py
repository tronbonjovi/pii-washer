import re

import pytest

from pii_washer.pii_detection_engine import PIIDetectionEngine


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
    text = "Call me at (555) 234-4567 today."
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1
    assert "555" in phones[0]["original_value"]
    assert "4567" in phones[0]["original_value"]


def test_detect_phone_dashes(engine):
    text = "My number is 555-234-4567."
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1


def test_detect_phone_international(engine):
    text = "Reach me at +1 (555) 234-4567 anytime."
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


# --- US Street Address Detection (Regex-based) ---

def test_detect_street_address_basic(engine):
    """Standard format: number + street name + street type."""
    text = "She lives at 742 Evergreen Terrace in the suburbs."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert len(addresses) >= 1
    assert any("742" in a["original_value"] and "Terrace" in a["original_value"] for a in addresses)


def test_detect_street_address_with_directional(engine):
    """Address with directional prefix."""
    text = "The office is at 100 North Main Street downtown."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert len(addresses) >= 1
    assert any("100" in a["original_value"] for a in addresses)


def test_detect_street_address_abbreviated(engine):
    """Abbreviated street type."""
    text = "Send mail to 456 Oak Ave for processing."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert len(addresses) >= 1
    assert any("456" in a["original_value"] for a in addresses)


def test_detect_street_address_multi_word(engine):
    """Multi-word street name."""
    text = "The memorial is at 1600 Pennsylvania Avenue in Washington."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert len(addresses) >= 1
    assert any("1600" in a["original_value"] for a in addresses)


def test_no_street_address_without_suffix(engine):
    """Plain number + words without a street type should NOT match."""
    text = "There were 100 participants in the study."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    # Should not detect "100 participants" as an address
    assert not any("100 participants" in a["original_value"] for a in addresses)


def test_street_address_positions_valid(engine):
    """Verify position indices correctly map back to the matched text."""
    text = "Her address is 321 Elm Road in the old district."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    for addr in addresses:
        start = addr["positions"][0]["start"]
        end = addr["positions"][0]["end"]
        assert text[start:end] == addr["original_value"]


# --- US Zip Code Detection ---

def test_detect_zip_plus_4(engine):
    """ZIP+4 format should always be detected (no context needed)."""
    text = "The parcel was sent to zip code 90210-1234 last month."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("90210-1234" in a["original_value"] for a in addresses)


def test_detect_zip_5_with_state_context(engine):
    """5-digit zip near a state abbreviation should be detected."""
    text = "Our Springfield, IL 62704 office is open Monday through Friday."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("62704" in a["original_value"] for a in addresses)


def test_detect_zip_5_with_street_context(engine):
    """5-digit zip near a street address should be detected."""
    text = "742 Evergreen Terrace, Springfield, IL 62704"
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("62704" in a["original_value"] for a in addresses)


def test_no_zip_without_context(engine):
    """5-digit number without address context should NOT be detected as zip."""
    text = "The project had 10000 downloads in its first week."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert not any("10000" in a["original_value"] for a in addresses)


def test_no_year_as_zip(engine):
    """A year in normal prose should NOT be detected as a zip code."""
    text = "The policy was enacted in 2024 after lengthy debate."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert not any("2024" in a["original_value"] for a in addresses)


def test_zip_positions_valid(engine):
    """Verify position indices correctly map back to zip code text."""
    text = "Mailing address: Springfield, IL 62704-5678"
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    zip_matches = [a for a in addresses if "62704" in a["original_value"]]
    assert len(zip_matches) >= 1
    for z in zip_matches:
        start = z["positions"][0]["start"]
        end = z["positions"][0]["end"]
        assert text[start:end] == z["original_value"]


# --- Full Address Detection (Street + City/State + Zip) ---

def test_detect_full_address_components(engine):
    """A complete US address should produce multiple ADDRESS detections covering its parts."""
    text = "Please ship to 742 Evergreen Terrace, Springfield, IL 62704 as soon as possible."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    values = " ".join(a["original_value"] for a in addresses)
    # Should catch the street address, and the zip code. NER may also catch city/state.
    assert "742" in values, "Street address should be detected"
    assert "62704" in values, "Zip code should be detected"


# --- DOB Detection (Context-Filtered) ---

def test_detect_dob_with_context(engine):
    # "born on" keyword is within 100 chars of March 5 → high confidence DOB.
    # A date far from any keyword → surfaces at 0.2 (Task 12 keywordless behavior).
    text = (
        "Patient was born on March 5, 1990. "
        "The patient was then referred to another facility. "
        "Three months later, a follow-up was scheduled for a routine checkup "
        "and the admission date was recorded as June 1, 2024."
    )
    results = engine.detect(text)
    dobs = [r for r in results if r["category"] == "DOB"]
    assert len(dobs) >= 1
    # The DOB near "born on" should be detected at > 0.2 confidence
    context_dobs = [d for d in dobs if "March" in d["original_value"]]
    assert len(context_dobs) >= 1
    assert context_dobs[0]["confidence"] > 0.2
    # June 1 is far from keywords → keywordless, surfaces at 0.2
    no_context_dobs = [d for d in dobs if "June" in d["original_value"]]
    for d in no_context_dobs:
        assert d["confidence"] == 0.2


def test_detect_dob_keyword_dob(engine):
    text = "DOB: 03/05/1990 — Admission: 06/01/2024"
    results = engine.detect(text)
    dobs = [r for r in results if r["category"] == "DOB"]
    assert len(dobs) >= 1


def test_no_dob_without_context(engine):
    # Task 12: dates without context now surface at 0.2 instead of being dropped.
    # Use a high threshold to verify they are NOT high-confidence detections.
    text = "The meeting is scheduled for January 15, 2025 at 3pm."
    results_high = engine.detect(text, confidence_threshold=0.3)
    dobs_high = [r for r in results_high if r["category"] == "DOB"]
    assert len(dobs_high) == 0, "Contextless dates should not appear at >= 0.3 confidence"
    # At default threshold they appear but at very low confidence
    results_default = engine.detect(text)
    dobs_default = [r for r in results_default if r["category"] == "DOB"]
    for d in dobs_default:
        assert d["confidence"] == 0.2


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
    text = "John Smith's email is john@example.com and his phone is (555) 234-4567."
    results = engine.detect(text)
    categories = {r["category"] for r in results}
    assert "NAME" in categories
    assert "EMAIL" in categories
    assert "PHONE" in categories


def test_detect_rich_document(engine):
    text = (
        "Dear Dr. Jane Doe,\n\n"
        "Your SSN 456-78-9012 is on file. Please contact us at support@clinic.com\n"
        "or call (555) 987-6543. Your date of birth January 15, 1985 has been verified.\n"
        "Your address is 742 Evergreen Terrace, Springfield, IL 62704.\n\n"
        "Regards,\nSpringfield Medical Center"
    )
    results = engine.detect(text)
    categories = {r["category"] for r in results}
    assert "NAME" in categories
    assert "SSN" in categories
    assert "EMAIL" in categories
    assert "PHONE" in categories
    assert "DOB" in categories
    assert "ADDRESS" in categories
    # Verify the street address was caught (not just city/state from NER)
    address_values = [r["original_value"] for r in results if r["category"] == "ADDRESS"]
    assert any("742" in v for v in address_values), "Street address should be detected"


# --- No PII ---

def test_detect_no_pii(engine):
    # Task 12: "today" and similar words may be classified as DATE_TIME at very low confidence.
    # Use a 0.3 threshold to verify no meaningful PII is found.
    text = "The weather today is sunny with a high of 75 degrees."
    results = engine.detect(text, confidence_threshold=0.3)
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
    text = "John Smith's email is john@example.com and his phone is (555) 234-4567."
    results = engine.detect(text)
    assert len(results) >= 2
    for i, det in enumerate(results, start=1):
        assert det["id"] == f"pii_{i:03d}"


def test_detection_sorted_by_position(engine):
    text = "Email: alice@test.com — Phone: (555) 222-2222 — Name: Bob Jones"
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


# =============================================================================
# Task 5: Name recognizer integration tests
# =============================================================================

def test_name_jane_doe(engine):
    """Key case from roadmap: Jane Doe detected as NAME."""
    text = "The report was filed by Jane Doe last week."
    results = engine.detect(text)
    names = [r for r in results if r["category"] == "NAME"]
    assert any("Jane" in n["original_value"] for n in names), "Jane Doe should be detected as NAME"


def test_name_title_based(engine):
    """Title-based detection: Mr. Smith."""
    text = "Please contact Mr. Smith for further assistance."
    results = engine.detect(text)
    names = [r for r in results if r["category"] == "NAME"]
    assert any("Smith" in n["original_value"] for n in names)


def test_name_dictionary_based(engine):
    """Dictionary name: Robert Chen."""
    text = "We received the invoice from Robert Chen yesterday."
    results = engine.detect(text)
    names = [r for r in results if r["category"] == "NAME"]
    assert any("Robert" in n["original_value"] for n in names)


def test_name_unusual_heuristic(engine):
    """Unusual name detected by capitalized-pair heuristic: Kazimir Volkov."""
    text = "The package was delivered to Kazimir Volkov at the office."
    results = engine.detect(text)
    names = [r for r in results if r["category"] == "NAME"]
    assert any("Kazimir" in n["original_value"] for n in names)


def test_name_no_duplicate_spans(engine):
    """No duplicate spans when NER and a custom recognizer both catch the same name."""
    text = "Robert Chen submitted the form."
    results = engine.detect(text)
    spans = [(r["positions"][0]["start"], r["positions"][0]["end"]) for r in results]
    assert len(spans) == len(set(spans)), "Duplicate spans should be removed"


# =============================================================================
# Task 6: SSN pattern hardening tests
# =============================================================================

def test_ssn_spaced(engine):
    """SSN with spaces: 219 09 9999."""
    text = "SSN: 219 09 9999"
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) >= 1
    assert "219" in ssns[0]["original_value"]


def test_ssn_dotted(engine):
    """SSN with dots: 219.09.9999."""
    text = "SSN: 219.09.9999"
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) >= 1


def test_ssn_no_separator_with_context(engine):
    """9-digit SSN without separator + context keyword → detected."""
    text = "social security 219099999 on file"
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) >= 1


def test_ssn_no_separator_without_context(engine):
    """9-digit number without SSN context → should NOT be detected."""
    text = "The order number is 219099999 and it was shipped."
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) == 0


def test_ssn_mixed_separators(engine):
    """SSN with mixed separators: 219-09.9999."""
    text = "SSN: 219-09.9999"
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) >= 1


def test_ssn_invalid_area_000(engine):
    """Area 000 is invalid — should NOT match."""
    text = "SSN: 000-12-3456"
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) == 0


def test_ssn_invalid_area_666(engine):
    """Area 666 is invalid — should NOT match."""
    text = "SSN: 666-12-3456"
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) == 0


def test_ssn_invalid_area_9xx(engine):
    """Area starting with 9 is invalid (ITIN range) — should NOT match."""
    text = "SSN: 912-34-5678"
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) == 0


def test_ssn_invalid_group_00(engine):
    """Group 00 is invalid — should NOT match."""
    text = "SSN: 219-00-9999"
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) == 0


def test_ssn_invalid_serial_0000(engine):
    """Serial 0000 is invalid — should NOT match."""
    text = "SSN: 219-09-0000"
    results = engine.detect(text)
    ssns = [r for r in results if r["category"] == "SSN"]
    assert len(ssns) == 0


def test_ssn_context_boost(engine):
    """Context keyword nearby should boost confidence."""
    text_with_context = "ssn: 219-09-9999"
    text_without_context = "number: 219-09-9999"
    results_with = engine.detect(text_with_context)
    results_without = engine.detect(text_without_context)
    ssns_with = [r for r in results_with if r["category"] == "SSN"]
    ssns_without = [r for r in results_without if r["category"] == "SSN"]
    assert len(ssns_with) >= 1
    assert len(ssns_without) >= 1
    assert ssns_with[0]["confidence"] > ssns_without[0]["confidence"]


# =============================================================================
# Task 7: Phone number pattern hardening tests
# =============================================================================

def test_phone_dots(engine):
    """Phone with dots: 512.555.1234."""
    text = "Call me at 512.555.1234."
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1
    assert "512" in phones[0]["original_value"]


def test_phone_spaces(engine):
    """Phone with spaces: 512 555 1234."""
    text = "Call me at 512 555 1234."
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1


def test_phone_no_separator_with_context(engine):
    """10-digit phone without separator + context keyword → detected."""
    text = "Call 5125551234 for support."
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1


def test_phone_no_separator_without_context(engine):
    """10-digit number without phone context → should NOT be detected."""
    text = "The ID number is 5125551234 for this record."
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) == 0


def test_phone_mixed_parens_dots(engine):
    """Mixed format: (512) 555.1234."""
    text = "Office: (512) 555.1234"
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1


def test_phone_country_code(engine):
    """Phone with country code: +1-512-555-1234."""
    text = "International: +1-512-555-1234"
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1


def test_phone_with_extension(engine):
    """Phone with extension: 512.555.1234 ext. 42."""
    text = "Office: 512.555.1234 ext. 42"
    results = engine.detect(text)
    phones = [r for r in results if r["category"] == "PHONE"]
    assert len(phones) >= 1


# =============================================================================
# Task 8: Address pattern hardening tests
# =============================================================================

def test_address_with_apartment(engine):
    """Street address with apartment suffix."""
    text = "She moved to 742 Evergreen Terrace Apt 3B last month."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("742" in a["original_value"] for a in addresses)


def test_address_with_unit_hash(engine):
    """Street address with unit/# suffix."""
    text = "Deliver to 100 Main Street # 5A please."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("100" in a["original_value"] for a in addresses)


def test_address_po_box(engine):
    """PO Box detection."""
    text = "Send mail to P.O. Box 1234 for processing."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("Box" in a["original_value"] or "1234" in a["original_value"] for a in addresses)


def test_address_po_box_post_office(engine):
    """PO Box with 'Post Office Box' format."""
    text = "Return address: Post Office Box 5678, Chicago IL 60601"
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("5678" in a["original_value"] or "Post" in a["original_value"] for a in addresses)


def test_address_highway(engine):
    """Highway/route address."""
    text = "The warehouse is at 1200 Highway 35 near the interchange."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("1200" in a["original_value"] for a in addresses)


def test_address_route(engine):
    """Route address."""
    text = "They live at 340 Route 9 in the rural area."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("340" in a["original_value"] for a in addresses)


# =============================================================================
# Task 9: Credit card pattern hardening tests
# =============================================================================

def test_ccn_spaces(engine):
    """Credit card with spaces: 4111 1111 1111 1111."""
    text = "Card number: 4111 1111 1111 1111"
    results = engine.detect(text)
    ccns = [r for r in results if r["category"] == "CCN"]
    assert len(ccns) >= 1


def test_ccn_no_separator(engine):
    """Credit card without separators: 4111111111111111."""
    text = "Card: 4111111111111111"
    results = engine.detect(text)
    ccns = [r for r in results if r["category"] == "CCN"]
    assert len(ccns) >= 1


def test_ccn_dots(engine):
    """Credit card with dots: 4111.1111.1111.1111."""
    text = "Payment: 4111.1111.1111.1111"
    results = engine.detect(text)
    ccns = [r for r in results if r["category"] == "CCN"]
    assert len(ccns) >= 1


def test_ccn_invalid_luhn_rejected(engine):
    """Invalid Luhn number should NOT be detected."""
    text = "Card: 4111 1111 1111 1112"
    results = engine.detect(text)
    ccns = [r for r in results if r["category"] == "CCN"]
    # The modified last digit breaks Luhn — should not match
    assert len(ccns) == 0


# =============================================================================
# Task 10: IP address enhancement tests
# =============================================================================

def test_ip_v4_with_port(engine):
    """IPv4 with port: 192.168.1.100:8080."""
    text = "The server is at 192.168.1.100:8080 on the LAN."
    results = engine.detect(text)
    ips = [r for r in results if r["category"] == "IP"]
    assert any("192.168.1.100" in ip["original_value"] for ip in ips)


def test_ip_v6_full(engine):
    """Full IPv6 address."""
    text = "Connect to 2001:0db8:85a3:0000:0000:8a2e:0370:7334 for the service."
    results = engine.detect(text)
    ips = [r for r in results if r["category"] == "IP"]
    assert len(ips) >= 1
    assert "2001" in ips[0]["original_value"]


def test_ip_v6_compressed(engine):
    """Compressed IPv6 address."""
    text = "IPv6 address: 2001:db8::1 is the host."
    results = engine.detect(text)
    ips = [r for r in results if r["category"] == "IP"]
    assert len(ips) >= 1


def test_ip_loopback_excluded(engine):
    """IPv6 loopback ::1 should NOT be flagged."""
    text = "The loopback address ::1 is used for local testing."
    results = engine.detect(text)
    ips = [r for r in results if r["category"] == "IP"]
    loopback = [ip for ip in ips if ip["original_value"].strip() == "::1"]
    assert len(loopback) == 0


def test_ip_link_local_excluded(engine):
    """IPv6 link-local fe80:: should NOT be flagged."""
    text = "Link-local address fe80::1 is assigned automatically."
    results = engine.detect(text)
    ips = [r for r in results if r["category"] == "IP"]
    link_local = [ip for ip in ips if ip["original_value"].lower().startswith("fe80::")]
    assert len(link_local) == 0


# =============================================================================
# Task 11: Email enhancement tests
# =============================================================================

def test_email_plus_addressing(engine):
    """Plus addressing should already work via Presidio."""
    text = "Send to john+filter@example.com please."
    results = engine.detect(text)
    emails = [r for r in results if r["category"] == "EMAIL"]
    assert len(emails) >= 1


def test_email_subdomain(engine):
    """Subdomain email should work via Presidio."""
    text = "My work email is alice@mail.company.org"
    results = engine.detect(text)
    emails = [r for r in results if r["category"] == "EMAIL"]
    assert len(emails) >= 1


def test_email_obfuscated_at_brackets(engine):
    """Obfuscated [at] email detected."""
    text = "Contact me at john.smith[at]example.com for help."
    results = engine.detect(text)
    emails = [r for r in results if r["category"] == "EMAIL"]
    assert len(emails) >= 1
    assert "john.smith" in emails[0]["original_value"]


def test_email_obfuscated_at_parens(engine):
    """Obfuscated (at) email detected."""
    text = "Reach out to alice(at)company.org for info."
    results = engine.detect(text)
    emails = [r for r in results if r["category"] == "EMAIL"]
    assert len(emails) >= 1


def test_email_obfuscated_dot(engine):
    """Obfuscated [dot] TLD detected."""
    text = "Email bob@example[dot]com for pricing."
    results = engine.detect(text)
    emails = [r for r in results if r["category"] == "EMAIL"]
    assert len(emails) >= 1


# =============================================================================
# Task 12: Context filter loosening tests
# =============================================================================

def test_dob_keyword_dob_dotted(engine):
    """d.o.b keyword triggers DOB detection."""
    text = "d.o.b: 03/15/1985"
    results = engine.detect(text)
    dobs = [r for r in results if r["category"] == "DOB"]
    assert len(dobs) >= 1


def test_dob_keyword_born_on(engine):
    """'born on' triggers DOB detection."""
    text = "She was born on April 22, 1990."
    results = engine.detect(text)
    dobs = [r for r in results if r["category"] == "DOB"]
    assert len(dobs) >= 1


def test_dob_keyword_birth_year(engine):
    """'birth year' triggers DOB detection."""
    text = "Birth year: 1978"
    results = engine.detect(text)
    dobs = [r for r in results if r["category"] == "DOB"]
    assert len(dobs) >= 1


def test_dob_keywordless_low_confidence(engine):
    """Date without context keyword surfaces at confidence 0.2."""
    text = "The conference will be held on September 14, 2026 in Seattle."
    results = engine.detect(text)
    dobs = [r for r in results if r["category"] == "DOB"]
    # If detected, must be at 0.2
    for d in dobs:
        assert d["confidence"] == 0.2


def test_zip_city_context(engine):
    """City name triggers zip code detection."""
    text = "Shipment heading to Chicago 60601 warehouse."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("60601" in a["original_value"] for a in addresses)


def test_zip_keyword_context(engine):
    """'zip code' keyword triggers zip detection."""
    text = "Please enter your zip code: 90210"
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert any("90210" in a["original_value"] for a in addresses)


def test_zip_no_city_substring_match(engine):
    """City name substring in a medical term should NOT trigger ZIP detection.

    'corona' is in the city list but 'coronary' contains it as a substring.
    The word-boundary fix ensures 'coronary artery disease' does not count
    as city context and a bare 5-digit number is not flagged as a ZIP.
    """
    text = "Patient has coronary artery disease. Refer to case 85001."
    results = engine.detect(text)
    addresses = [r for r in results if r["category"] == "ADDRESS"]
    assert not any("85001" in a["original_value"] for a in addresses), (
        "85001 should NOT be detected as a ZIP — 'coronary' is not the city 'corona'"
    )


def test_url_reddit_user(engine):
    """Reddit user URL detected."""
    text = "My Reddit is https://reddit.com/user/johndoe"
    results = engine.detect(text)
    urls = [r for r in results if r["category"] == "URL"]
    assert len(urls) >= 1


def test_url_tiktok(engine):
    """TikTok profile URL detected."""
    text = "Follow me on https://tiktok.com/@myhandle"
    results = engine.detect(text)
    urls = [r for r in results if r["category"] == "URL"]
    assert len(urls) >= 1


def test_url_profile_path_heuristic(engine):
    """Generic /user/ path heuristic detected."""
    text = "See profile at https://example.com/user/janedoe"
    results = engine.detect(text)
    urls = [r for r in results if r["category"] == "URL"]
    assert len(urls) >= 1


def test_url_profile_path_not_settings(engine):
    """Settings URL should NOT trigger profile heuristic."""
    text = "Go to https://example.com/user/settings to update preferences."
    results = engine.detect(text)
    urls = [r for r in results if r["category"] == "URL"]
    # /user/settings should be excluded
    settings_urls = [u for u in urls if "settings" in u["original_value"]]
    assert len(settings_urls) == 0


# =============================================================================
# Task 13: Default threshold tests
# =============================================================================

def test_default_threshold_is_0_2(engine):
    """Default confidence threshold is 0.2."""
    from pii_washer.pii_detection_engine import PIIDetectionEngine
    assert PIIDetectionEngine.DEFAULT_CONFIDENCE_THRESHOLD == 0.2


def test_detect_signature_default_is_0_2(engine):
    """detect() default threshold is 0.2 — lower threshold finds >= as many results."""
    text = "Contact john@example.com for details."
    results_02 = engine.detect(text, confidence_threshold=0.2)
    results_03 = engine.detect(text, confidence_threshold=0.3)
    assert len(results_02) >= len(results_03)


# =============================================================================
# Task 14: Integration tests — new format variants
# =============================================================================

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
        assert len(results) >= 6  # name, email, phone, SSN(s), address, zip


# =============================================================================
# Task 14: False positive tests
# =============================================================================

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
        assert not any("Goldman Sachs" in n["original_value"] for n in names)
        assert not any("Morgan Stanley" in n["original_value"] for n in names)

    def test_month_day_not_name(self, engine):
        """Month + day name pair should not be detected as a person name."""
        text = "The event is on Saturday January at the conference center."
        results = engine.detect(text, confidence_threshold=0.2)
        names = [r for r in results if r["category"] == "NAME"]
        assert not any("Saturday January" in n["original_value"] for n in names)
