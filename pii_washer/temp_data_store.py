import atexit
import copy
import os
from datetime import UTC, datetime

VALID_SOURCE_FORMATS = {".txt", ".md", ".docx", ".pdf", "paste"}
VALID_STATUSES = {
    "user_input", "analyzed", "depersonalized",
    "awaiting_response", "repersonalized", "closed",
}
SESSION_FIELDS = {
    "session_id", "created_at", "updated_at", "status",
    "original_text", "source_format", "source_filename",
    "pii_detections", "depersonalized_text", "response_text",
    "repersonalized_text", "unmatched_placeholders",
}
IMMUTABLE_FIELDS = {"session_id", "created_at"}

class TempDataStore:
    _SENSITIVE_FIELDS = [
        "original_text", "pii_detections", "depersonalized_text",
        "response_text", "repersonalized_text",
    ]

    def __init__(self):
        self._sessions: dict[str, dict] = {}
        atexit.register(self.secure_clear)

    @staticmethod
    def _recursive_wipe(obj) -> None:
        """Best-effort in-place overwrite of all string values in nested structures."""
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                value = obj[key]
                if isinstance(value, str):
                    obj[key] = ""
                elif isinstance(value, dict):
                    TempDataStore._recursive_wipe(value)
                    value.clear()
                elif isinstance(value, list):
                    TempDataStore._recursive_wipe(value)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str):
                    obj[i] = ""
                elif isinstance(item, (dict, list)):
                    TempDataStore._recursive_wipe(item)
            obj.clear()

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

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

    def secure_clear(self) -> int:
        """Overwrite all sensitive fields with empty values before deleting.

        Defense-in-depth: zeroes PII data in memory rather than relying
        on garbage collection alone.  Registered as an atexit handler so
        it runs automatically when the process exits.
        """
        count = len(self._sessions)
        for session in self._sessions.values():
            self._recursive_wipe(session)
        self._sessions.clear()
        return count

    def session_count(self) -> int:
        return len(self._sessions)
