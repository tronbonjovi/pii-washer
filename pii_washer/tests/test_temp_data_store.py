import time

import pytest

from pii_washer.temp_data_store import TempDataStore

# --- Session Creation ---


def test_create_session_basic():
    store = TempDataStore()
    sid = store.create_session("Hello world", "paste")
    assert isinstance(sid, str)
    assert len(sid) == 6
    assert store.session_count() == 1


def test_create_session_with_filename():
    store = TempDataStore()
    sid = store.create_session("File content", ".txt", "notes.txt")
    session = store.get_session(sid)
    assert session["source_filename"] == "notes.txt"
    assert session["source_format"] == ".txt"
    assert session["original_text"] == "File content"


def test_create_session_defaults():
    store = TempDataStore()
    sid = store.create_session("Some text", "paste")
    session = store.get_session(sid)
    assert session["status"] == "user_input"
    assert session["pii_detections"] == []
    assert session["depersonalized_text"] is None
    assert session["response_text"] is None
    assert session["repersonalized_text"] is None
    assert session["unmatched_placeholders"] == []
    assert session["created_at"]
    assert session["updated_at"]


def test_create_session_empty_text_raises():
    store = TempDataStore()
    with pytest.raises(ValueError, match="cannot be empty"):
        store.create_session("", "paste")


def test_create_session_invalid_format_raises():
    store = TempDataStore()
    with pytest.raises(ValueError, match="Invalid source format"):
        store.create_session("text", ".xyz")


def test_create_multiple_sessions():
    store = TempDataStore()
    ids = [store.create_session(f"Text {i}", "paste") for i in range(3)]
    assert store.session_count() == 3
    assert len(set(ids)) == 3


# --- Session Retrieval ---


def test_get_session_returns_deep_copy():
    store = TempDataStore()
    sid = store.create_session("Hello", "paste")
    result = store.get_session(sid)
    result["status"] = "closed"
    assert store.get_session(sid)["status"] == "user_input"


def test_get_session_not_found():
    store = TempDataStore()
    with pytest.raises(KeyError):
        store.get_session("nonexistent")


# --- Session Updates ---


def test_update_session_basic():
    store = TempDataStore()
    sid = store.create_session("Hello", "paste")
    created = store.get_session(sid)["created_at"]
    time.sleep(0.01)
    store.update_session(sid, {"status": "analyzed"})
    session = store.get_session(sid)
    assert session["status"] == "analyzed"
    assert session["updated_at"] >= created


def test_update_session_partial():
    store = TempDataStore()
    sid = store.create_session("Original text", "paste")
    store.update_session(sid, {"depersonalized_text": "Clean text here"})
    session = store.get_session(sid)
    assert session["depersonalized_text"] == "Clean text here"
    assert session["original_text"] == "Original text"


def test_update_session_pii_detections():
    store = TempDataStore()
    sid = store.create_session("John Smith is here", "paste")
    detection = {
        "id": "pii_001",
        "category": "NAME",
        "original_value": "John Smith",
        "placeholder": "[Person_1]",
        "status": "pending",
        "positions": [{"start": 0, "end": 10}],
        "confidence": 0.95,
    }
    store.update_session(sid, {"pii_detections": [detection]})
    session = store.get_session(sid)
    assert len(session["pii_detections"]) == 1
    assert session["pii_detections"][0] == detection


def test_update_session_immutable_id():
    store = TempDataStore()
    sid = store.create_session("Hello", "paste")
    with pytest.raises(ValueError, match="Cannot modify session_id"):
        store.update_session(sid, {"session_id": "hacked"})


def test_update_session_immutable_created_at():
    store = TempDataStore()
    sid = store.create_session("Hello", "paste")
    with pytest.raises(ValueError, match="Cannot modify created_at"):
        store.update_session(sid, {"created_at": "2000-01-01T00:00:00Z"})


def test_update_session_invalid_status():
    store = TempDataStore()
    sid = store.create_session("Hello", "paste")
    with pytest.raises(ValueError, match="Invalid status"):
        store.update_session(sid, {"status": "banana"})


def test_update_session_unknown_keys_ignored():
    store = TempDataStore()
    sid = store.create_session("Hello", "paste")
    store.update_session(sid, {"status": "analyzed", "banana": "yellow"})
    session = store.get_session(sid)
    assert session["status"] == "analyzed"
    assert "banana" not in session


def test_update_session_not_found():
    store = TempDataStore()
    with pytest.raises(KeyError):
        store.update_session("nonexistent", {"status": "analyzed"})


# --- Secure Clear ---


def test_secure_clear_overwrites_sensitive_fields():
    store = TempDataStore()
    sid = store.create_session("Sensitive PII text", "paste")
    store.update_session(sid, {
        "pii_detections": [{"id": "d1", "original_value": "John"}],
        "depersonalized_text": "Clean text",
        "response_text": "LLM response",
        "repersonalized_text": "Final output",
    })
    # Grab a direct reference to the session dict before clearing
    session_ref = store._sessions[sid]
    assert store.secure_clear() == 1
    # Verify sensitive fields were overwritten before deletion
    assert session_ref["original_text"] == ""
    assert session_ref["pii_detections"] == []
    assert session_ref["depersonalized_text"] == ""
    assert session_ref["response_text"] == ""
    assert session_ref["repersonalized_text"] == ""
    assert store.session_count() == 0


def test_secure_clear_empty():
    store = TempDataStore()
    assert store.secure_clear() == 0


# --- Round-Trip Integration ---


def test_full_lifecycle():
    store = TempDataStore()

    # Create
    sid = store.create_session("My name is John Smith", "paste")

    # Analyze
    store.update_session(sid, {"status": "analyzed"})
    detection = {
        "id": "pii_001",
        "category": "NAME",
        "original_value": "John Smith",
        "placeholder": "[Person_1]",
        "status": "pending",
        "positions": [{"start": 11, "end": 21}],
        "confidence": 0.95,
    }
    store.update_session(sid, {"pii_detections": [detection]})

    # Depersonalize
    store.update_session(sid, {
        "status": "depersonalized",
        "depersonalized_text": "My name is [Person_1]",
    })

    # Awaiting response
    store.update_session(sid, {"status": "awaiting_response"})

    # Response received
    store.update_session(sid, {
        "response_text": "Dear [Person_1], your application is approved.",
    })

    # Repersonalize
    store.update_session(sid, {
        "status": "repersonalized",
        "repersonalized_text": "Dear John Smith, your application is approved.",
    })

    # Close
    store.update_session(sid, {"status": "closed"})

    # Verify final state
    session = store.get_session(sid)
    assert session["status"] == "closed"
    assert session["original_text"] == "My name is John Smith"
    assert session["depersonalized_text"] == "My name is [Person_1]"
    assert session["response_text"] == "Dear [Person_1], your application is approved."
    assert session["repersonalized_text"] == "Dear John Smith, your application is approved."
    assert len(session["pii_detections"]) == 1
