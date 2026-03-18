import atexit
import copy
import json
import os
from datetime import datetime, timezone


VALID_SOURCE_FORMATS = {".txt", ".md", "paste"}
VALID_STATUSES = {
    "user_input", "analyzed", "confirmed", "depersonalized",
    "awaiting_response", "repersonalized", "closed",
}
SESSION_FIELDS = {
    "session_id", "created_at", "updated_at", "status",
    "original_text", "source_format", "source_filename",
    "pii_detections", "depersonalized_text", "response_text",
    "repersonalized_text", "unmatched_placeholders",
}
IMMUTABLE_FIELDS = {"session_id", "created_at"}
REQUIRED_IMPORT_FIELDS = [
    "session_id", "created_at", "status", "original_text", "source_format",
]


class TempDataStore:
    _SENSITIVE_FIELDS = [
        "original_text", "pii_detections", "depersonalized_text",
        "response_text", "repersonalized_text",
    ]

    def __init__(self):
        self._sessions: dict[str, dict] = {}
        atexit.register(self.secure_clear)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _generate_id(self) -> str:
        while True:
            session_id = os.urandom(3).hex()
            if session_id not in self._sessions:
                return session_id

    def create_session(
        self, text: str, source_format: str, filename: str | None = None
    ) -> str:
        if not isinstance(text, str) or not text:
            raise ValueError("Text cannot be empty")
        if source_format not in VALID_SOURCE_FORMATS:
            raise ValueError(f"Invalid source format: {source_format}")

        session_id = self._generate_id()
        now = self._now()

        self._sessions[session_id] = {
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
            "status": "user_input",
            "original_text": text,
            "source_format": source_format,
            "source_filename": filename,
            "pii_detections": [],
            "depersonalized_text": None,
            "response_text": None,
            "repersonalized_text": None,
            "unmatched_placeholders": [],
        }
        return session_id

    def get_session(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")
        return copy.deepcopy(self._sessions[session_id])

    def update_session(self, session_id: str, updates: dict) -> dict:
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")

        for field in IMMUTABLE_FIELDS:
            if field in updates:
                raise ValueError(f"Cannot modify {field}")

        if "status" in updates and updates["status"] not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {updates['status']}")
        if "source_format" in updates and updates["source_format"] not in VALID_SOURCE_FORMATS:
            raise ValueError(f"Invalid source format: {updates['source_format']}")

        session = self._sessions[session_id]
        for key, value in updates.items():
            if key in SESSION_FIELDS and key not in IMMUTABLE_FIELDS:
                session[key] = value
        session["updated_at"] = self._now()

        return copy.deepcopy(session)

    def delete_session(self, session_id: str) -> None:
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")
        del self._sessions[session_id]

    def list_sessions(self) -> list[dict]:
        summaries = [
            {
                "session_id": s["session_id"],
                "status": s["status"],
                "source_format": s["source_format"],
                "source_filename": s["source_filename"],
                "created_at": s["created_at"],
                "updated_at": s["updated_at"],
            }
            for s in self._sessions.values()
        ]
        summaries.sort(key=lambda x: x["created_at"], reverse=True)
        return summaries

    def clear_all(self) -> int:
        count = len(self._sessions)
        self._sessions.clear()
        return count

    def export_session(self, session_id: str) -> str:
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")
        return json.dumps(self._sessions[session_id], indent=2)

    def import_session(self, json_string: str) -> str:
        try:
            data = json.loads(json_string)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("Invalid JSON")

        for field in REQUIRED_IMPORT_FIELDS:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        if data["status"] not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {data['status']}")
        if data["source_format"] not in VALID_SOURCE_FORMATS:
            raise ValueError(f"Invalid source format: {data['source_format']}")

        session_id = data["session_id"]
        if session_id in self._sessions:
            raise ValueError(f"Session already exists: {session_id}")

        # Fill any optional fields absent from the import with canonical defaults
        data.setdefault("source_filename", None)
        data.setdefault("pii_detections", [])
        data.setdefault("depersonalized_text", None)
        data.setdefault("response_text", None)
        data.setdefault("repersonalized_text", None)
        data.setdefault("unmatched_placeholders", [])

        data["updated_at"] = self._now()
        # Only persist known session fields; drop anything else that may
        # have been injected into the JSON payload.
        self._sessions[session_id] = {
            k: v for k, v in data.items() if k in SESSION_FIELDS
        }
        return session_id

    def secure_clear(self) -> int:
        """Overwrite all sensitive fields with empty values before deleting.

        Defense-in-depth: zeroes PII data in memory rather than relying
        on garbage collection alone.  Registered as an atexit handler so
        it runs automatically when the process exits.
        """
        count = len(self._sessions)
        for session in self._sessions.values():
            for field in self._SENSITIVE_FIELDS:
                if field in session and isinstance(session[field], str):
                    session[field] = ""
                elif field in session and isinstance(session[field], list):
                    session[field] = []
        self._sessions.clear()
        return count

    def session_count(self) -> int:
        return len(self._sessions)
