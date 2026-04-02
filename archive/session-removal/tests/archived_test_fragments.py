# Archived session management tests — removed as part of session removal.
# These tests covered multi-session CRUD operations that no longer exist.
# Kept for reference only.

# ==========================================================================
# From test_api.py
# ==========================================================================


# --- TestSessionCRUD (partial) ---

class TestSessionCRUD_archived:
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

    def test_delete_session_returns_204_then_404(self, client):
        r = client.post("/api/v1/sessions", json={"text": SAMPLE_TEXT})
        session_id = r.json()["session_id"]
        r2 = client.delete(f"/api/v1/sessions/{session_id}")
        assert r2.status_code == 204
        r3 = client.get(f"/api/v1/sessions/{session_id}")
        assert r3.status_code == 404


# --- TestExportImport ---

class TestExportImport_archived:
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


# --- TestErrorHandling (partial) ---

class TestErrorHandling_archived:
    def test_import_invalid_json_returns_422(self, client):
        r = client.post(
            "/api/v1/sessions/import",
            json={"session_data": "not valid json {{{"},
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"


# ==========================================================================
# From test_session_manager.py
# ==========================================================================


class TestSessionManagement_archived:
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
        count = manager.reset()
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

    def test_import_drops_unknown_keys(self, manager):
        """Deferred item: unknown keys in imported JSON must not be persisted."""
        import json
        payload = json.dumps({
            "session_id": "unk001",
            "created_at": "2026-01-01T00:00:00Z",
            "status": "user_input",
            "original_text": "Hello world",
            "source_format": "paste",
            "injected_field": "should be dropped",
            "__proto__": {"admin": True},
        })
        sid = manager.import_session(payload)
        session = manager.get_session(sid)
        assert "injected_field" not in session
        assert "__proto__" not in session
        # Also verify export doesn't leak unknown keys
        exported = json.loads(manager.export_session(sid))
        assert "injected_field" not in exported
        assert "__proto__" not in exported

    def test_import_minimal_session_get_status_does_not_raise(self, manager):
        """Finding 5 regression: get_session_status() must not KeyError on a minimally-imported session."""
        import json
        minimal = json.dumps({
            "session_id": "min001",
            "created_at": "2026-01-01T00:00:00Z",
            "status": "user_input",
            "original_text": "Hello world",
            "source_format": "paste",
        })
        sid = manager.import_session(minimal)
        status = manager.get_session_status(sid)
        assert status["status"] == "user_input"
        assert status["source_filename"] is None
        assert status["detection_count"] == 0
        assert status["has_depersonalized"] is False
        assert status["has_response"] is False
        assert status["has_repersonalized"] is False


# ==========================================================================
# From test_temp_data_store.py
# ==========================================================================


def test_delete_session_archived():
    store = TempDataStore()
    sid = store.create_session("Hello", "paste")
    store.delete_session(sid)
    assert store.session_count() == 0
    with pytest.raises(KeyError):
        store.get_session(sid)


def test_delete_session_not_found_archived():
    store = TempDataStore()
    with pytest.raises(KeyError):
        store.delete_session("nonexistent")


def test_delete_one_of_many_archived():
    store = TempDataStore()
    ids = [store.create_session(f"Text {i}", "paste") for i in range(3)]
    store.delete_session(ids[1])
    assert store.session_count() == 2
    with pytest.raises(KeyError):
        store.get_session(ids[1])
    assert store.get_session(ids[0])["original_text"] == "Text 0"
    assert store.get_session(ids[2])["original_text"] == "Text 2"


def test_list_sessions_empty_archived():
    store = TempDataStore()
    assert store.list_sessions() == []


def test_list_sessions_content_archived():
    store = TempDataStore()
    store.create_session("First", "paste")
    time.sleep(0.01)
    store.create_session("Second", ".md")
    result = store.list_sessions()
    assert len(result) == 2
    expected_keys = {"session_id", "status", "source_format", "source_filename", "created_at", "updated_at"}
    for entry in result:
        assert set(entry.keys()) == expected_keys
        assert "original_text" not in entry


def test_list_sessions_sorted_newest_first_archived():
    store = TempDataStore()
    sid_a = store.create_session("First", "paste")
    time.sleep(0.01)
    sid_b = store.create_session("Second", "paste")
    result = store.list_sessions()
    assert result[0]["session_id"] == sid_b


def test_clear_all_archived():
    store = TempDataStore()
    for i in range(3):
        store.create_session(f"Text {i}", "paste")
    assert store.clear_all() == 3
    assert store.session_count() == 0
    assert store.list_sessions() == []


def test_clear_all_empty_archived():
    store = TempDataStore()
    assert store.clear_all() == 0


def test_export_session_archived():
    store = TempDataStore()
    sid = store.create_session("Test export", "paste")
    exported = store.export_session(sid)
    assert isinstance(exported, str)
    parsed = json.loads(exported)
    assert parsed["session_id"] == sid
    assert parsed["original_text"] == "Test export"
    assert parsed["status"] == "user_input"


def test_export_session_not_found_archived():
    store = TempDataStore()
    with pytest.raises(KeyError):
        store.export_session("nonexistent")


def test_import_session_archived():
    store = TempDataStore()
    sid = store.create_session("Import test", "paste")
    exported = store.export_session(sid)
    store.delete_session(sid)
    returned_id = store.import_session(exported)
    assert returned_id == sid
    session = store.get_session(sid)
    assert session["original_text"] == "Import test"
    assert store.session_count() == 1


def test_import_session_duplicate_archived():
    store = TempDataStore()
    sid = store.create_session("Dup test", "paste")
    exported = store.export_session(sid)
    with pytest.raises(ValueError, match="already exists"):
        store.import_session(exported)


def test_import_session_missing_field_archived():
    store = TempDataStore()
    data = '{"session_id": "abc123", "created_at": "2026-01-01T00:00:00Z", "original_text": "test", "source_format": "paste"}'
    with pytest.raises(ValueError, match="Missing required field"):
        store.import_session(data)


def test_import_session_invalid_json_archived():
    store = TempDataStore()
    with pytest.raises(ValueError, match="Invalid JSON"):
        store.import_session("not valid json{{{")


def test_import_session_invalid_status_raises_archived():
    """Finding 5 regression: import must reject invalid status values."""
    store = TempDataStore()
    data = json.dumps({
        "session_id": "abc123",
        "created_at": "2026-01-01T00:00:00Z",
        "status": "hacked",
        "original_text": "test",
        "source_format": "paste",
    })
    with pytest.raises(ValueError, match="Invalid status"):
        store.import_session(data)


def test_import_session_invalid_source_format_raises_archived():
    """Finding 5 regression: import must reject invalid source_format values."""
    store = TempDataStore()
    data = json.dumps({
        "session_id": "abc123",
        "created_at": "2026-01-01T00:00:00Z",
        "status": "user_input",
        "original_text": "test",
        "source_format": ".docx",
    })
    with pytest.raises(ValueError, match="Invalid source format"):
        store.import_session(data)


def test_import_session_fills_missing_optional_fields_archived():
    """Finding 5 regression: import with only required fields must not crash get_session_status."""
    store = TempDataStore()
    data = json.dumps({
        "session_id": "abc123",
        "created_at": "2026-01-01T00:00:00Z",
        "status": "user_input",
        "original_text": "test",
        "source_format": "paste",
    })
    sid = store.import_session(data)
    session = store.get_session(sid)
    assert session["source_filename"] is None
    assert session["pii_detections"] == []
    assert session["depersonalized_text"] is None
    assert session["response_text"] is None
    assert session["repersonalized_text"] is None
    assert session["unmatched_placeholders"] == []


# --- test_full_lifecycle (partial — export/delete/import round-trip portion) ---
# The full_lifecycle test also used export_session, delete_session, and import_session
# at the end. That portion is archived here:

def test_full_lifecycle_export_import_portion_archived():
    """
    The last section of test_full_lifecycle that exercised export/delete/import:

        # Export, delete, import round-trip
        exported = store.export_session(sid)
        store.delete_session(sid)
        assert store.session_count() == 0

        store.import_session(exported)
        restored = store.get_session(sid)
        assert restored["original_text"] == "My name is John Smith"
        assert restored["status"] == "closed"
        assert restored["depersonalized_text"] == "My name is [Person_1]"
        assert len(restored["pii_detections"]) == 1
    """
    pass
