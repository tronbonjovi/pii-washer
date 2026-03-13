"""PII Shield Component 5: Session Manager.

Orchestrates the full PII Shield workflow by coordinating all other components.
Acts as the single interface the UI calls.
"""


class SessionManager:
    """Coordinates all PII Shield components through a single interface."""

    VALID_DETECTION_STATUSES = ["pending", "confirmed", "rejected"]

    WORKFLOW_STATES = {
        "user_input":        {"can_analyze": True,  "can_edit_detections": False, "can_depersonalize": False, "can_load_response": False, "can_repersonalize": False},
        "analyzed":          {"can_analyze": False, "can_edit_detections": True,  "can_depersonalize": True,  "can_load_response": False, "can_repersonalize": False},
        "depersonalized":    {"can_analyze": False, "can_edit_detections": False, "can_depersonalize": False, "can_load_response": True,  "can_repersonalize": False},
        "awaiting_response": {"can_analyze": False, "can_edit_detections": False, "can_depersonalize": False, "can_load_response": False, "can_repersonalize": True},
        "repersonalized":    {"can_analyze": False, "can_edit_detections": False, "can_depersonalize": False, "can_load_response": False, "can_repersonalize": False},
        "closed":            {"can_analyze": False, "can_edit_detections": False, "can_depersonalize": False, "can_load_response": False, "can_repersonalize": False},
    }

    def __init__(self, store=None, document_loader=None, detection_engine=None,
                 placeholder_generator=None, substitution_engine=None):
        if store is None:
            from pii_shield.temp_data_store import TempDataStore
            store = TempDataStore()
        self.store = store

        if document_loader is None:
            from pii_shield.document_loader import DocumentLoader
            document_loader = DocumentLoader()
        self.document_loader = document_loader

        if detection_engine is None:
            try:
                from pii_shield.pii_detection_engine import PIIDetectionEngine
                detection_engine = PIIDetectionEngine()
            except Exception:
                detection_engine = None
        self.detection_engine = detection_engine

        if placeholder_generator is None:
            from pii_shield.placeholder_generator import PlaceholderGenerator
            placeholder_generator = PlaceholderGenerator()
        self.placeholder_generator = placeholder_generator

        if substitution_engine is None:
            from pii_shield.text_substitution_engine import TextSubstitutionEngine
            substitution_engine = TextSubstitutionEngine()
        self.substitution_engine = substitution_engine

    def load_text(self, text):
        result = self.document_loader.load_text(text)
        session_id = self.store.create_session(
            result["text"], result["source_format"], result["filename"]
        )
        return session_id

    def load_file(self, filepath):
        result = self.document_loader.load_file(filepath)
        session_id = self.store.create_session(
            result["text"], result["source_format"], result["filename"]
        )
        return session_id

    def analyze(self, session_id):
        session = self.store.get_session(session_id)
        status = session["status"]
        if status != "user_input":
            raise ValueError(
                f"Cannot analyze: session status is '{status}', expected 'user_input'"
            )
        if self.detection_engine is None:
            raise RuntimeError(
                "PII Detection Engine is not available. Is spaCy installed?"
            )

        detections = self.detection_engine.detect(session["original_text"])

        if not detections:
            self.store.update_session(session_id, {
                "pii_detections": [],
                "status": "analyzed",
            })
            return []

        detections = self.placeholder_generator.assign_placeholders(detections)

        for detection in detections:
            detection["status"] = "pending"

        self.store.update_session(session_id, {
            "pii_detections": detections,
            "status": "analyzed",
        })
        return detections

    def update_detection_status(self, session_id, detection_id, status):
        session = self.store.get_session(session_id)
        sess_status = session["status"]
        if sess_status != "analyzed":
            raise ValueError(
                f"Cannot update detections: session status is '{sess_status}', expected 'analyzed'"
            )
        if status not in self.VALID_DETECTION_STATUSES:
            raise ValueError(f"Invalid detection status: {status}")

        for detection in session["pii_detections"]:
            if detection["id"] == detection_id:
                detection["status"] = status
                self.store.update_session(session_id, {
                    "pii_detections": session["pii_detections"],
                })
                return detection

        raise ValueError(f"Detection not found: {detection_id}")

    def confirm_all_detections(self, session_id):
        session = self.store.get_session(session_id)
        sess_status = session["status"]
        if sess_status != "analyzed":
            raise ValueError(
                f"Cannot update detections: session status is '{sess_status}', expected 'analyzed'"
            )

        count = 0
        for detection in session["pii_detections"]:
            if detection["status"] == "pending":
                detection["status"] = "confirmed"
                count += 1

        self.store.update_session(session_id, {
            "pii_detections": session["pii_detections"],
        })
        return count

    def edit_detection_placeholder(self, session_id, detection_id, new_placeholder):
        session = self.store.get_session(session_id)
        sess_status = session["status"]
        if sess_status != "analyzed":
            raise ValueError(
                f"Cannot update detections: session status is '{sess_status}', expected 'analyzed'"
            )
        if not new_placeholder:
            raise ValueError("Placeholder cannot be empty")

        for detection in session["pii_detections"]:
            if detection["id"] == detection_id:
                detection["placeholder"] = new_placeholder
                self.store.update_session(session_id, {
                    "pii_detections": session["pii_detections"],
                })
                return detection

        raise ValueError(f"Detection not found: {detection_id}")

    def apply_depersonalization(self, session_id):
        session = self.store.get_session(session_id)
        status = session["status"]
        if status != "analyzed":
            raise ValueError(
                f"Cannot depersonalize: session status is '{status}', expected 'analyzed'"
            )

        confirmed = [d for d in session["pii_detections"] if d["status"] == "confirmed"]
        if not confirmed:
            raise ValueError("Cannot depersonalize: no confirmed detections")

        depersonalized = self.substitution_engine.depersonalize(
            session["original_text"], session["pii_detections"]
        )
        self.store.update_session(session_id, {
            "depersonalized_text": depersonalized,
            "status": "depersonalized",
        })
        return depersonalized

    def get_depersonalized_text(self, session_id):
        session = self.store.get_session(session_id)
        if session["depersonalized_text"] is None:
            raise ValueError("Session has not been depersonalized yet")
        return session["depersonalized_text"]

    def load_response_text(self, session_id, text):
        session = self.store.get_session(session_id)
        status = session["status"]
        if status != "depersonalized":
            raise ValueError(
                f"Cannot load response: session status is '{status}', expected 'depersonalized'"
            )

        result = self.document_loader.load_text(text)
        self.store.update_session(session_id, {
            "response_text": result["text"],
            "status": "awaiting_response",
        })
        return result["text"]

    def load_response_file(self, session_id, filepath):
        session = self.store.get_session(session_id)
        status = session["status"]
        if status != "depersonalized":
            raise ValueError(
                f"Cannot load response: session status is '{status}', expected 'depersonalized'"
            )

        result = self.document_loader.load_file(filepath)
        self.store.update_session(session_id, {
            "response_text": result["text"],
            "status": "awaiting_response",
        })
        return result["text"]

    def apply_repersonalization(self, session_id):
        session = self.store.get_session(session_id)
        status = session["status"]
        if status != "awaiting_response":
            raise ValueError(
                f"Cannot repersonalize: session status is '{status}', expected 'awaiting_response'"
            )

        result = self.substitution_engine.repersonalize(
            session["response_text"], session["pii_detections"]
        )
        self.store.update_session(session_id, {
            "repersonalized_text": result["text"],
            "unmatched_placeholders": result["unmatched_from_map"],
            "status": "repersonalized",
        })
        return result

    def get_session(self, session_id):
        return self.store.get_session(session_id)

    def list_sessions(self):
        return self.store.list_sessions()

    def delete_session(self, session_id):
        return self.store.delete_session(session_id)

    def clear_all_sessions(self):
        return self.store.clear_all()

    def export_session(self, session_id):
        return self.store.export_session(session_id)

    def import_session(self, json_string):
        return self.store.import_session(json_string)

    def get_session_status(self, session_id):
        session = self.store.get_session(session_id)
        status = session["status"]
        detections = session.get("pii_detections") or []

        confirmed_count = sum(1 for d in detections if d.get("status") == "confirmed")
        rejected_count = sum(1 for d in detections if d.get("status") == "rejected")
        pending_count = sum(1 for d in detections if d.get("status") == "pending")

        workflow = self.WORKFLOW_STATES.get(status, {
            "can_analyze": False, "can_edit_detections": False,
            "can_depersonalize": False, "can_load_response": False,
            "can_repersonalize": False,
        })

        can_depersonalize = workflow["can_depersonalize"] and confirmed_count > 0

        return {
            "session_id": session_id,
            "status": status,
            "source_format": session["source_format"],
            "source_filename": session["source_filename"],
            "detection_count": len(detections),
            "confirmed_count": confirmed_count,
            "rejected_count": rejected_count,
            "pending_count": pending_count,
            "has_depersonalized": session["depersonalized_text"] is not None,
            "has_response": session["response_text"] is not None,
            "has_repersonalized": session["repersonalized_text"] is not None,
            "can_analyze": workflow["can_analyze"],
            "can_edit_detections": workflow["can_edit_detections"],
            "can_depersonalize": can_depersonalize,
            "can_load_response": workflow["can_load_response"],
            "can_repersonalize": workflow["can_repersonalize"],
        }
