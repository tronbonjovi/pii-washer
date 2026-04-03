"""Integration tests — full API stack with real Presidio detection engine.

These tests exercise the complete HTTP -> FastAPI -> SessionManager -> PIIDetectionEngine
pipeline. They require the spaCy en_core_web_lg model and are slower than unit tests.

Run with: pytest pii_washer/tests/test_api_integration.py -v
Skip in CI without spaCy: pytest -m "not integration"
"""

import pytest
from fastapi.testclient import TestClient

# Skip entire module if spaCy model not available
try:
    from pii_washer.pii_detection_engine import PIIDetectionEngine
    _engine = PIIDetectionEngine()  # will fail if model not installed
    HAS_SPACY_MODEL = True
except Exception:
    HAS_SPACY_MODEL = False

pytestmark = [
    pytest.mark.skipif(not HAS_SPACY_MODEL, reason="spaCy en_core_web_lg model not installed"),
    pytest.mark.integration,
]

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

SAMPLE_TEXT = "Contact John Smith at john@example.com or call (555) 123-4567."
PII_VALUES = ["John Smith", "john@example.com", "(555) 123-4567"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """TestClient backed by a real SessionManager with real PIIDetectionEngine."""
    from pii_washer.api.main import create_app
    from pii_washer.session_manager import SessionManager

    engine = PIIDetectionEngine()
    manager = SessionManager(detection_engine=engine)
    app = create_app(session_manager=manager)
    with TestClient(app) as c:
        yield c


def _run_through_depersonalization(client, text=SAMPLE_TEXT):
    """Helper: create session, analyze, confirm all, depersonalize.

    Returns (session_id, depersonalized_text).
    """
    r = client.post("/api/v1/sessions", json={"text": text})
    assert r.status_code == 201
    session_id = r.json()["session_id"]

    r = client.post(f"/api/v1/sessions/{session_id}/analyze")
    assert r.status_code == 200

    r = client.post(f"/api/v1/sessions/{session_id}/detections/confirm-all")
    assert r.status_code == 200

    r = client.post(f"/api/v1/sessions/{session_id}/depersonalize")
    assert r.status_code == 200
    depersonalized_text = r.json()["depersonalized_text"]

    return session_id, depersonalized_text


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFullWorkflowWithRealDetection:
    """Complete happy-path workflow using the real Presidio+spaCy engine."""

    def test_full_workflow_with_real_detection(self, client):
        # 1. Create session
        r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        assert r.status_code == 201
        session_id = r.json()["session_id"]

        # 2. Analyze — expect real detections
        r = client.post(f"/api/v1/sessions/{session_id}/analyze")
        assert r.status_code == 200
        detections = r.json()["detections"]
        assert len(detections) > 0, "Real engine should detect PII in sample text"

        # Verify at least a PERSON/NAME and EMAIL were found
        categories = {d["category"] for d in detections}
        assert "NAME" in categories or "PERSON" in categories, (
            f"Expected NAME or PERSON in categories, got {categories}"
        )
        assert "EMAIL" in categories, f"Expected EMAIL in categories, got {categories}"

        # 3. Confirm all detections
        r = client.post(f"/api/v1/sessions/{session_id}/detections/confirm-all")
        assert r.status_code == 200
        assert r.json()["confirmed_count"] > 0

        # 4. Depersonalize
        r = client.post(f"/api/v1/sessions/{session_id}/depersonalize")
        assert r.status_code == 200
        depersonalized_text = r.json()["depersonalized_text"]
        assert depersonalized_text != SAMPLE_TEXT

        # 5. Load response (use depersonalized text as the "AI response")
        r = client.post(
            f"/api/v1/sessions/{session_id}/response",
            json={"text": depersonalized_text},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "awaiting_response"

        # 6. Repersonalize
        r = client.post(f"/api/v1/sessions/{session_id}/repersonalize")
        assert r.status_code == 200
        repersonalized_text = r.json()["repersonalized_text"]
        assert "match_summary" in r.json()

        # Verify PII is restored
        assert "John Smith" in repersonalized_text
        assert "john@example.com" in repersonalized_text


class TestAnalyzeDetectsKnownPiiTypes:
    """Verify real Presidio detects expected PII categories."""

    def test_analyze_detects_known_pii_types(self, client):
        r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        session_id = r.json()["session_id"]

        r = client.post(f"/api/v1/sessions/{session_id}/analyze")
        assert r.status_code == 200
        detections = r.json()["detections"]

        categories = {d["category"] for d in detections}

        # Don't assert exact counts — model output can vary.
        # Just confirm the major categories are present.
        assert "NAME" in categories or "PERSON" in categories, (
            f"Expected a name detection, got categories: {categories}"
        )
        assert "EMAIL" in categories, (
            f"Expected an email detection, got categories: {categories}"
        )


class TestDepersonalizedTextContainsNoRawPii:
    """After depersonalization, original PII strings must not appear."""

    def test_depersonalized_text_contains_no_raw_pii(self, client):
        _, depersonalized_text = _run_through_depersonalization(client)

        for pii_value in PII_VALUES:
            assert pii_value not in depersonalized_text, (
                f"PII value '{pii_value}' should not appear in depersonalized text: "
                f"{depersonalized_text!r}"
            )

        # Depersonalized text should contain placeholder tokens
        assert "[" in depersonalized_text and "]" in depersonalized_text, (
            "Depersonalized text should contain placeholder tokens"
        )


class TestRepersonalizedTextRestoresPii:
    """After the full round-trip, original PII values must be restored."""

    def test_repersonalized_text_restores_pii(self, client):
        session_id, depersonalized_text = _run_through_depersonalization(client)

        # Load the depersonalized text as the "AI response"
        r = client.post(
            f"/api/v1/sessions/{session_id}/response",
            json={"text": depersonalized_text},
        )
        assert r.status_code == 200

        # Repersonalize
        r = client.post(f"/api/v1/sessions/{session_id}/repersonalize")
        assert r.status_code == 200
        repersonalized_text = r.json()["repersonalized_text"]

        # Original PII values should be back
        assert "John Smith" in repersonalized_text, (
            f"'John Smith' not found in repersonalized text: {repersonalized_text!r}"
        )
        assert "john@example.com" in repersonalized_text, (
            f"'john@example.com' not found in repersonalized text: {repersonalized_text!r}"
        )
