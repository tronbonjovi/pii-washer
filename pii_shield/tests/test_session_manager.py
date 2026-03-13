"""Tests for PII Shield Component 5: Session Manager."""

import pytest

from pii_shield.session_manager import SessionManager


# ---------------------------------------------------------------------------
# Mock Detection Engine
# ---------------------------------------------------------------------------

class MockDetectionEngine:
    """A lightweight mock that returns predictable detections without spaCy."""

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

    def get_entity_mapping(self):
        return {"PERSON": "NAME", "EMAIL_ADDRESS": "EMAIL"}


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

SAMPLE_TEXT = "My name is John Smith and my email is john@example.com."
SAMPLE_TEXT_MULTI = "John Smith emailed john@example.com. Call (555) 123-4567 to reach John Smith."


@pytest.fixture
def manager():
    """Create a SessionManager with a mock detection engine."""
    return SessionManager(detection_engine=MockDetectionEngine())


# ---------------------------------------------------------------------------
# Session Creation
# ---------------------------------------------------------------------------

class TestSessionCreation:
    def test_load_text(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        assert isinstance(sid, str)
        session = manager.get_session(sid)
        assert session["original_text"] == SAMPLE_TEXT
        assert session["status"] == "user_input"
        assert session["source_format"] == "paste"
        assert session["source_filename"] is None

    def test_load_file(self, manager, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello from a file.")
        sid = manager.load_file(str(f))
        assert isinstance(sid, str)
        session = manager.get_session(sid)
        assert session["source_format"] == ".txt"
        assert session["source_filename"] == "test.txt"

    def test_load_text_empty_raises(self, manager):
        with pytest.raises(ValueError):
            manager.load_text("")

    def test_load_file_invalid_format_raises(self, manager, tmp_path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"fake docx")
        with pytest.raises(ValueError):
            manager.load_file(str(f))


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class TestAnalysis:
    def test_analyze(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        assert isinstance(detections, list)
        categories = [d["category"] for d in detections]
        assert "NAME" in categories
        assert "EMAIL" in categories
        for d in detections:
            assert "placeholder" in d
            assert d["status"] == "pending"
        session = manager.get_session(sid)
        assert session["status"] == "analyzed"

    def test_analyze_stores_detections(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        session = manager.get_session(sid)
        assert len(session["pii_detections"]) > 0
        for d in session["pii_detections"]:
            for key in ("id", "category", "original_value", "placeholder", "status", "positions", "confidence"):
                assert key in d

    def test_analyze_no_pii(self, manager):
        sid = manager.load_text("The weather is sunny today.")
        detections = manager.analyze(sid)
        assert detections == []
        session = manager.get_session(sid)
        assert session["status"] == "analyzed"
        assert session["pii_detections"] == []

    def test_analyze_wrong_state(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        with pytest.raises(ValueError, match="expected 'user_input'"):
            manager.analyze(sid)

    def test_analyze_without_engine(self):
        mgr = SessionManager(detection_engine=None)
        sid = mgr.load_text(SAMPLE_TEXT)
        with pytest.raises(RuntimeError, match="not available"):
            mgr.analyze(sid)


# ---------------------------------------------------------------------------
# Detection Review — Status Updates
# ---------------------------------------------------------------------------

class TestDetectionStatusUpdates:
    def test_update_detection_status_confirm(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        det_id = detections[0]["id"]
        result = manager.update_detection_status(sid, det_id, "confirmed")
        assert result["status"] == "confirmed"
        session = manager.get_session(sid)
        stored = next(d for d in session["pii_detections"] if d["id"] == det_id)
        assert stored["status"] == "confirmed"

    def test_update_detection_status_reject(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        det_id = detections[0]["id"]
        result = manager.update_detection_status(sid, det_id, "rejected")
        assert result["status"] == "rejected"

    def test_update_detection_status_back_to_pending(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        det_id = detections[0]["id"]
        manager.update_detection_status(sid, det_id, "confirmed")
        result = manager.update_detection_status(sid, det_id, "pending")
        assert result["status"] == "pending"

    def test_update_detection_invalid_status(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        det_id = detections[0]["id"]
        with pytest.raises(ValueError, match="Invalid detection status"):
            manager.update_detection_status(sid, det_id, "banana")

    def test_update_detection_not_found(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        with pytest.raises(ValueError, match="Detection not found"):
            manager.update_detection_status(sid, "pii_999", "confirmed")

    def test_update_detection_wrong_session_state(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        with pytest.raises(ValueError, match="expected 'analyzed'"):
            manager.update_detection_status(sid, "pii_001", "confirmed")


# ---------------------------------------------------------------------------
# Detection Review — Confirm All
# ---------------------------------------------------------------------------

class TestConfirmAll:
    def test_confirm_all(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        count = manager.confirm_all_detections(sid)
        assert count > 0
        session = manager.get_session(sid)
        for d in session["pii_detections"]:
            assert d["status"] == "confirmed"

    def test_confirm_all_preserves_rejected(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        rejected_id = detections[0]["id"]
        manager.update_detection_status(sid, rejected_id, "rejected")
        manager.confirm_all_detections(sid)
        session = manager.get_session(sid)
        rejected = next(d for d in session["pii_detections"] if d["id"] == rejected_id)
        assert rejected["status"] == "rejected"
        others = [d for d in session["pii_detections"] if d["id"] != rejected_id]
        for d in others:
            assert d["status"] == "confirmed"

    def test_confirm_all_returns_count(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        det_id = detections[0]["id"]
        manager.update_detection_status(sid, det_id, "confirmed")
        count = manager.confirm_all_detections(sid)
        # count should be total detections minus the one already confirmed
        assert count == len(detections) - 1


# ---------------------------------------------------------------------------
# Detection Review — Edit Placeholder
# ---------------------------------------------------------------------------

class TestEditPlaceholder:
    def test_edit_placeholder(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        det_id = detections[0]["id"]
        result = manager.edit_detection_placeholder(sid, det_id, "[My_Client]")
        assert result["placeholder"] == "[My_Client]"
        session = manager.get_session(sid)
        stored = next(d for d in session["pii_detections"] if d["id"] == det_id)
        assert stored["placeholder"] == "[My_Client]"

    def test_edit_placeholder_empty_raises(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        det_id = detections[0]["id"]
        with pytest.raises(ValueError, match="cannot be empty"):
            manager.edit_detection_placeholder(sid, det_id, "")

    def test_edit_placeholder_detection_not_found(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        with pytest.raises(ValueError, match="Detection not found"):
            manager.edit_detection_placeholder(sid, "pii_999", "[Test]")


# ---------------------------------------------------------------------------
# Depersonalization
# ---------------------------------------------------------------------------

class TestDepersonalization:
    def test_apply_depersonalization(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        manager.confirm_all_detections(sid)
        result = manager.apply_depersonalization(sid)
        assert isinstance(result, str)
        assert "John Smith" not in result
        assert "john@example.com" not in result
        assert "[" in result and "]" in result  # contains a placeholder
        session = manager.get_session(sid)
        assert session["status"] == "depersonalized"
        assert session["depersonalized_text"] is not None

    def test_depersonalize_no_confirmed_raises(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        with pytest.raises(ValueError, match="no confirmed detections"):
            manager.apply_depersonalization(sid)

    def test_depersonalize_partial_confirmation(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        # Find NAME and EMAIL detections
        name_det = next(d for d in detections if d["category"] == "NAME")
        email_det = next(d for d in detections if d["category"] == "EMAIL")
        manager.update_detection_status(sid, name_det["id"], "confirmed")
        manager.update_detection_status(sid, email_det["id"], "rejected")
        result = manager.apply_depersonalization(sid)
        # Confirmed PII should be replaced
        assert "John Smith" not in result
        # Rejected PII should remain
        assert "john@example.com" in result

    def test_depersonalize_wrong_state(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        with pytest.raises(ValueError, match="expected 'analyzed'"):
            manager.apply_depersonalization(sid)

    def test_get_depersonalized_text(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        manager.confirm_all_detections(sid)
        deperso = manager.apply_depersonalization(sid)
        retrieved = manager.get_depersonalized_text(sid)
        assert retrieved == deperso

    def test_get_depersonalized_text_before_depersonalization(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        with pytest.raises(ValueError, match="not been depersonalized"):
            manager.get_depersonalized_text(sid)


# ---------------------------------------------------------------------------
# Response Loading
# ---------------------------------------------------------------------------

class TestResponseLoading:
    def test_load_response_text(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        manager.confirm_all_detections(sid)
        manager.apply_depersonalization(sid)
        result = manager.load_response_text(sid, "Dear [Person_1], your request is approved.")
        assert isinstance(result, str)
        session = manager.get_session(sid)
        assert session["response_text"] is not None
        assert session["status"] == "awaiting_response"

    def test_load_response_file(self, manager, tmp_path):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        manager.confirm_all_detections(sid)
        manager.apply_depersonalization(sid)
        f = tmp_path / "response.txt"
        f.write_text("Dear [Person_1], approved.")
        result = manager.load_response_file(sid, str(f))
        assert isinstance(result, str)
        session = manager.get_session(sid)
        assert session["status"] == "awaiting_response"

    def test_load_response_wrong_state(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        with pytest.raises(ValueError, match="expected 'depersonalized'"):
            manager.load_response_text(sid, "Some response")


# ---------------------------------------------------------------------------
# Repersonalization
# ---------------------------------------------------------------------------

class TestRepersonalization:
    def test_apply_repersonalization(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        manager.confirm_all_detections(sid)
        deperso = manager.apply_depersonalization(sid)
        response = f"Dear colleague, here is my response: {deperso}"
        manager.load_response_text(sid, response)
        result = manager.apply_repersonalization(sid)
        assert "John Smith" in result["text"]
        assert "john@example.com" in result["text"]
        assert len(result["matched"]) > 0
        assert "matched" in result["match_summary"]
        session = manager.get_session(sid)
        assert session["status"] == "repersonalized"
        assert session["repersonalized_text"] is not None

    def test_repersonalize_wrong_state(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        manager.confirm_all_detections(sid)
        manager.apply_depersonalization(sid)
        with pytest.raises(ValueError, match="expected 'awaiting_response'"):
            manager.apply_repersonalization(sid)

    def test_repersonalize_with_unmatched(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        manager.confirm_all_detections(sid)
        manager.apply_depersonalization(sid)
        # Response that only uses some placeholders — no email placeholder used
        manager.load_response_text(sid, "Hello there, no placeholders here.")
        result = manager.apply_repersonalization(sid)
        assert len(result["unmatched_from_map"]) > 0
        session = manager.get_session(sid)
        assert len(session["unmatched_placeholders"]) > 0


# ---------------------------------------------------------------------------
# Session Management (Delegated)
# ---------------------------------------------------------------------------

class TestSessionManagement:
    def test_list_sessions(self, manager):
        manager.load_text("First session.")
        manager.load_text("Second session.")
        sessions = manager.list_sessions()
        assert len(sessions) == 2

    def test_delete_session(self, manager):
        sid = manager.load_text("Delete me.")
        manager.delete_session(sid)
        assert manager.list_sessions() == []
        with pytest.raises(KeyError):
            manager.get_session(sid)

    def test_clear_all_sessions(self, manager):
        manager.load_text("One.")
        manager.load_text("Two.")
        manager.load_text("Three.")
        count = manager.clear_all_sessions()
        assert count == 3
        assert manager.list_sessions() == []

    def test_export_import_session(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        exported = manager.export_session(sid)
        manager.delete_session(sid)
        new_sid = manager.import_session(exported)
        session = manager.get_session(new_sid)
        assert session["original_text"] == SAMPLE_TEXT
        assert session["status"] == "analyzed"


# ---------------------------------------------------------------------------
# Session Status
# ---------------------------------------------------------------------------

class TestSessionStatus:
    def test_get_session_status_initial(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        status = manager.get_session_status(sid)
        assert status["status"] == "user_input"
        assert status["can_analyze"] is True
        assert status["can_edit_detections"] is False
        assert status["can_depersonalize"] is False
        assert status["detection_count"] == 0

    def test_get_session_status_after_analyze(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        status = manager.get_session_status(sid)
        assert status["status"] == "analyzed"
        assert status["can_analyze"] is False
        assert status["can_edit_detections"] is True
        assert status["can_depersonalize"] is False  # no confirmed yet
        assert status["detection_count"] > 0
        assert status["pending_count"] == status["detection_count"]

    def test_get_session_status_after_confirm(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        detections = manager.analyze(sid)
        det_id = detections[0]["id"]
        manager.update_detection_status(sid, det_id, "confirmed")
        status = manager.get_session_status(sid)
        assert status["can_depersonalize"] is True
        assert status["confirmed_count"] >= 1

    def test_get_session_status_after_depersonalize(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        manager.confirm_all_detections(sid)
        manager.apply_depersonalization(sid)
        status = manager.get_session_status(sid)
        assert status["status"] == "depersonalized"
        assert status["has_depersonalized"] is True
        assert status["can_load_response"] is True
        assert status["can_depersonalize"] is False

    def test_get_session_status_after_repersonalize(self, manager):
        sid = manager.load_text(SAMPLE_TEXT)
        manager.analyze(sid)
        manager.confirm_all_detections(sid)
        deperso = manager.apply_depersonalization(sid)
        manager.load_response_text(sid, f"Response: {deperso}")
        manager.apply_repersonalization(sid)
        status = manager.get_session_status(sid)
        assert status["status"] == "repersonalized"
        assert status["has_repersonalized"] is True
        assert status["can_analyze"] is False
        assert status["can_edit_detections"] is False
        assert status["can_depersonalize"] is False
        assert status["can_load_response"] is False
        assert status["can_repersonalize"] is False


# ---------------------------------------------------------------------------
# Full Workflow Integration
# ---------------------------------------------------------------------------

class TestFullWorkflow:
    def test_full_workflow(self, manager):
        # 1. Load text with multiple PII types
        sid = manager.load_text(SAMPLE_TEXT_MULTI)

        # 2. Analyze
        detections = manager.analyze(sid)
        assert len(detections) > 0

        # 3. Review: reject one, confirm all others
        rejected_det = detections[0]
        rejected_id = rejected_det["id"]
        rejected_value = rejected_det["original_value"]
        manager.update_detection_status(sid, rejected_id, "rejected")
        manager.confirm_all_detections(sid)

        # 4. Depersonalize
        deperso = manager.apply_depersonalization(sid)
        # Rejected PII should still be present
        assert rejected_value in deperso
        # Confirmed PII should be replaced
        confirmed_session = manager.get_session(sid)
        for d in confirmed_session["pii_detections"]:
            if d["status"] == "confirmed":
                assert d["original_value"] not in deperso

        # 5. Construct simulated LLM response
        response = f"Thank you for your message. Here is my response based on: {deperso}"

        # 6. Load response
        manager.load_response_text(sid, response)
        session = manager.get_session(sid)
        assert session["status"] == "awaiting_response"

        # 7. Repersonalize
        result = manager.apply_repersonalization(sid)
        assert "matched" in result["match_summary"]

        # 8. Verify rejected PII was never tracked in repersonalization map
        final_session = manager.get_session(sid)
        assert final_session["status"] == "repersonalized"
        assert final_session["repersonalized_text"] is not None
