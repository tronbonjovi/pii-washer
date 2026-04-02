"""Integration tests for the PII Washer FastAPI wrapper (B2)."""

import io

import pytest
from fastapi.testclient import TestClient

from pii_washer.session_manager import SessionManager

# ---------------------------------------------------------------------------
# Mock Detection Engine (same pattern as test_session_manager.py)
# ---------------------------------------------------------------------------

class MockDetectionEngine:
    """Lightweight mock that returns predictable detections without spaCy."""

    def detect(self, text, confidence_threshold=0.3, language="en"):
        detections = []
        counter = 1
        test_patterns = [
            ("John Smith", "NAME"),
            ("Jane Doe", "NAME"),
            ("john@example.com", "EMAIL"),
            ("(555) 123-4567", "PHONE"),
            ("219-09-9999", "SSN"),
            ("Springfield", "ADDRESS"),
        ]
        for value, category in test_patterns:
            start = 0
            while True:
                pos = text.find(value, start)
                if pos == -1:
                    break
                detections.append({
                    "id": f"pii_{counter:03d}",
                    "category": category,
                    "original_value": value,
                    "positions": [{"start": pos, "end": pos + len(value)}],
                    "confidence": 0.85,
                })
                counter += 1
                start = pos + len(value)
        return detections

    def get_supported_categories(self):
        return ["NAME", "ADDRESS", "PHONE", "EMAIL", "SSN", "DOB", "CCN", "IP", "URL"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TEXT = "My name is John Smith and my email is john@example.com."
RESPONSE_TEXT = "Hello [Person_1], your email [Email_1] has been noted."


@pytest.fixture
def client():
    """TestClient backed by a fresh in-memory SessionManager with mock engine."""
    from pii_washer.api.main import create_app
    manager = SessionManager(detection_engine=MockDetectionEngine())
    app = create_app(session_manager=manager)
    with TestClient(app) as c:
        yield c


def _create_analyzed_session(client):
    """Helper: create and analyze a session, return (session_id, detection_id)."""
    r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
    session_id = r.json()["session_id"]
    r2 = client.post(f"/api/v1/sessions/{session_id}/analyze")
    detections = r2.json()["detections"]
    detection_id = detections[0]["id"] if detections else None
    return session_id, detection_id


# ---------------------------------------------------------------------------
# 1. Happy path — full workflow
# ---------------------------------------------------------------------------

class TestFullWorkflow:
    def test_end_to_end_workflow(self, client):
        # 1. Create session
        r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        assert r.status_code == 201
        session_id = r.json()["session_id"]

        # 2. Analyze
        r = client.post(f"/api/v1/sessions/{session_id}/analyze")
        assert r.status_code == 200
        detections = r.json()["detections"]
        assert len(detections) > 0

        # 3. Confirm one detection
        det_id = detections[0]["id"]
        r = client.patch(
            f"/api/v1/sessions/{session_id}/detections/{det_id}",
            json={"status": "confirmed"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

        # 4. Confirm all remaining
        r = client.post(f"/api/v1/sessions/{session_id}/detections/confirm-all")
        assert r.status_code == 200
        assert r.json()["confirmed_count"] >= 0

        # 5. Depersonalize
        r = client.post(f"/api/v1/sessions/{session_id}/depersonalize")
        assert r.status_code == 200
        body = r.json()
        assert "depersonalized_text" in body
        assert body["confirmed_count"] > 0

        # 6. Load response
        deperso_text = body["depersonalized_text"]
        r = client.post(
            f"/api/v1/sessions/{session_id}/response",
            json={"text": deperso_text},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "awaiting_response"

        # 7. Repersonalize
        r = client.post(f"/api/v1/sessions/{session_id}/repersonalize")
        assert r.status_code == 200
        body = r.json()
        assert "repersonalized_text" in body
        assert "match_summary" in body

        # 8. Verify PII is restored
        repersonalized = body["repersonalized_text"]
        assert "John Smith" in repersonalized or "john@example.com" in repersonalized


# ---------------------------------------------------------------------------
# 2. Session CRUD
# ---------------------------------------------------------------------------

class TestSessionCRUD:
    def test_create_from_text_returns_201(self, client):
        r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        assert r.status_code == 201
        body = r.json()
        assert "session_id" in body
        assert body["status"] == "user_input"
        assert body["source_format"] == "paste"
        assert body["source_filename"] is None
        assert body["original_text"] == SAMPLE_TEXT

    def test_create_from_file_upload_returns_201(self, client):
        content = b"Hello, my name is John Smith."
        r = client.post(
            "/api/v1/sessions/upload",
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        )
        assert r.status_code == 201
        body = r.json()
        assert "session_id" in body
        assert body["source_format"] == ".txt"
        assert body["source_filename"] == "test.txt"

    def test_list_sessions_returns_200(self, client):
        client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        r = client.get("/api/v1/sessions")
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        item = items[0]
        assert "session_id" in item
        assert "status" in item
        assert "detection_count" in item

    def test_get_session_by_id_returns_full_data(self, client):
        r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        session_id = r.json()["session_id"]
        r2 = client.get(f"/api/v1/sessions/{session_id}")
        assert r2.status_code == 200
        body = r2.json()
        assert body["session_id"] == session_id
        assert body["original_text"] == SAMPLE_TEXT
        assert "pii_detections" in body

    def test_get_session_status(self, client):
        r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        session_id = r.json()["session_id"]
        r2 = client.get(f"/api/v1/sessions/{session_id}/status")
        assert r2.status_code == 200
        body = r2.json()
        assert body["session_id"] == session_id
        assert "detection_count" in body
        assert "can_analyze" in body

    def test_delete_session_returns_204_then_404(self, client):
        r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        session_id = r.json()["session_id"]
        r2 = client.delete(f"/api/v1/sessions/{session_id}")
        assert r2.status_code == 204
        r3 = client.get(f"/api/v1/sessions/{session_id}")
        assert r3.status_code == 404


# ---------------------------------------------------------------------------
# 3. File upload validation
# ---------------------------------------------------------------------------

class TestFileUpload:
    def test_upload_txt_succeeds(self, client):
        content = b"Contact John Smith at john@example.com"
        r = client.post(
            "/api/v1/sessions/upload",
            files={"file": ("doc.txt", io.BytesIO(content), "text/plain")},
        )
        assert r.status_code == 201

    def test_upload_md_succeeds(self, client):
        content = b"# Note\nCall (555) 123-4567 to reach John Smith."
        r = client.post(
            "/api/v1/sessions/upload",
            files={"file": ("notes.md", io.BytesIO(content), "text/markdown")},
        )
        assert r.status_code == 201

    def test_upload_unsupported_extension_returns_422(self, client):
        content = b"print('hello')"
        r = client.post(
            "/api/v1/sessions/upload",
            files={"file": ("script.py", io.BytesIO(content), "text/plain")},
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "UNSUPPORTED_FORMAT"

    def test_upload_metadata_persists_on_subsequent_reads(self, client):
        """Bug #1: source_format and source_filename must survive past the initial response."""
        content = b"Hello, my name is John Smith."
        r = client.post(
            "/api/v1/sessions/upload",
            files={"file": ("report.txt", io.BytesIO(content), "text/plain")},
        )
        assert r.status_code == 201
        session_id = r.json()["session_id"]

        r2 = client.get(f"/api/v1/sessions/{session_id}")
        assert r2.status_code == 200
        body = r2.json()
        assert body["source_format"] == ".txt", f"Expected '.txt', got '{body['source_format']}'"
        assert body["source_filename"] == "report.txt", f"Expected 'report.txt', got '{body['source_filename']}'"

    def test_upload_exceeding_size_limit_returns_413(self, client):
        large_content = b"A" * (1_048_576 + 1)
        r = client.post(
            "/api/v1/sessions/upload",
            files={"file": ("big.txt", io.BytesIO(large_content), "text/plain")},
        )
        assert r.status_code == 413
        assert r.json()["error"]["code"] == "FILE_TOO_LARGE"


# ---------------------------------------------------------------------------
# 4. Detection management
# ---------------------------------------------------------------------------

class TestDetectionManagement:
    def test_confirm_detection_changes_status(self, client):
        session_id, det_id = _create_analyzed_session(client)
        r = client.patch(
            f"/api/v1/sessions/{session_id}/detections/{det_id}",
            json={"status": "confirmed"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"
        assert r.json()["id"] == det_id

    def test_reject_detection_changes_status(self, client):
        session_id, det_id = _create_analyzed_session(client)
        r = client.patch(
            f"/api/v1/sessions/{session_id}/detections/{det_id}",
            json={"status": "rejected"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_edit_placeholder(self, client):
        session_id, det_id = _create_analyzed_session(client)
        r = client.patch(
            f"/api/v1/sessions/{session_id}/detections/{det_id}/placeholder",
            json={"placeholder": "[My_Client]"},
        )
        assert r.status_code == 200
        assert r.json()["placeholder"] == "[My_Client]"

    def test_confirm_all_returns_count(self, client):
        session_id, _ = _create_analyzed_session(client)
        r = client.post(f"/api/v1/sessions/{session_id}/detections/confirm-all")
        assert r.status_code == 200
        assert "confirmed_count" in r.json()
        assert r.json()["confirmed_count"] >= 0

    def test_manual_add_detection(self, client):
        text = "Contact Dr. Martinez about the referral."
        r = client.post("/api/v1/sessions", json={"text": text})
        session_id = r.json()["session_id"]
        client.post(f"/api/v1/sessions/{session_id}/analyze")

        r2 = client.post(
            f"/api/v1/sessions/{session_id}/detections",
            json={"text_value": "Dr. Martinez", "category": "NAME"},
        )
        assert r2.status_code == 201
        body = r2.json()
        assert body["original_value"] == "Dr. Martinez"
        assert body["category"] == "NAME"
        assert body["source"] == "manual"
        assert body["occurrences_found"] >= 1
        assert len(body["positions"]) >= 1


# ---------------------------------------------------------------------------
# 5. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_get_nonexistent_session_returns_404(self, client):
        r = client.get("/api/v1/sessions/nonexistent")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "NOT_FOUND"

    def test_analyze_wrong_state_returns_409(self, client):
        session_id, _ = _create_analyzed_session(client)
        # Already in 'analyzed' state — cannot analyze again
        r = client.post(f"/api/v1/sessions/{session_id}/analyze")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "INVALID_STATE"

    def test_depersonalize_no_confirmed_returns_422(self, client):
        session_id, _ = _create_analyzed_session(client)
        # No detections confirmed
        r = client.post(f"/api/v1/sessions/{session_id}/depersonalize")
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_update_detection_invalid_status_returns_422(self, client):
        session_id, det_id = _create_analyzed_session(client)
        r = client.patch(
            f"/api/v1/sessions/{session_id}/detections/{det_id}",
            json={"status": "not_a_real_status"},
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_update_missing_detection_returns_404(self, client):
        session_id, _ = _create_analyzed_session(client)
        r = client.patch(
            f"/api/v1/sessions/{session_id}/detections/pii_999",
            json={"status": "confirmed"},
        )
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "NOT_FOUND"

    def test_manual_add_invalid_category_returns_422(self, client):
        session_id, _ = _create_analyzed_session(client)
        r = client.post(
            f"/api/v1/sessions/{session_id}/detections",
            json={"text_value": "Something", "category": "INVALID_CATEGORY"},
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_manual_add_duplicate_returns_409(self, client):
        session_id, _ = _create_analyzed_session(client)
        # "John Smith" is already detected as NAME by the mock engine
        r = client.post(
            f"/api/v1/sessions/{session_id}/detections",
            json={"text_value": "John Smith", "category": "NAME"},
        )
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "DUPLICATE_DETECTION"

    def test_manual_add_text_not_found_returns_422(self, client):
        session_id, _ = _create_analyzed_session(client)
        r = client.post(
            f"/api/v1/sessions/{session_id}/detections",
            json={"text_value": "Completely Absent Text XYZ123", "category": "NAME"},
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "TEXT_NOT_FOUND"

    def test_import_invalid_json_returns_422(self, client):
        r = client.post(
            "/api/v1/sessions/import",
            json={"session_data": "not valid json {{{"},
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# 6. Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_returns_200(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "engine_available" in body
        assert "version" in body

    def test_health_engine_available_with_mock(self, client):
        r = client.get("/api/v1/health")
        assert r.json()["engine_available"] is True

    def test_health_engine_unavailable_when_no_engine(self):
        from pii_washer.api.main import create_app
        manager = SessionManager(detection_engine=None)
        app = create_app(session_manager=manager)
        with TestClient(app) as c:
            r = c.get("/api/v1/health")
            assert r.status_code == 200
            assert r.json()["engine_available"] is False


# ---------------------------------------------------------------------------
# 7. Session lifecycle cleanup
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_session(self, client):
        client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        r = client.post("/api/v1/sessions/reset")
        assert r.status_code == 200
        assert r.json()["deleted_count"] >= 1

    def test_reset_when_empty(self, client):
        r = client.post("/api/v1/sessions/reset")
        assert r.status_code == 200
        assert r.json()["deleted_count"] == 0


# ---------------------------------------------------------------------------
# 8. Export / import round-trip
# ---------------------------------------------------------------------------

class TestExportImport:
    def test_export_import_round_trip(self, client):
        # Create and analyze
        r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        session_id = r.json()["session_id"]
        client.post(f"/api/v1/sessions/{session_id}/analyze")

        # Confirm first detection
        r2 = client.get(f"/api/v1/sessions/{session_id}")
        detections = r2.json()["pii_detections"]
        if detections:
            det_id = detections[0]["id"]
            client.patch(
                f"/api/v1/sessions/{session_id}/detections/{det_id}",
                json={"status": "confirmed"},
            )

        # Export
        r3 = client.get(f"/api/v1/sessions/{session_id}/export")
        assert r3.status_code == 200
        exported_json = r3.text

        # Delete original
        client.delete(f"/api/v1/sessions/{session_id}")
        r_gone = client.get(f"/api/v1/sessions/{session_id}")
        assert r_gone.status_code == 404

        # Import
        r4 = client.post(
            "/api/v1/sessions/import",
            json={"session_data": exported_json},
        )
        assert r4.status_code == 201
        imported_id = r4.json()["session_id"]
        assert imported_id == session_id

        # Verify detections and statuses are restored
        r5 = client.get(f"/api/v1/sessions/{imported_id}")
        assert r5.status_code == 200
        restored = r5.json()
        assert restored["original_text"] == SAMPLE_TEXT
        if detections:
            restored_dets = restored["pii_detections"]
            assert any(d["status"] == "confirmed" for d in restored_dets)
