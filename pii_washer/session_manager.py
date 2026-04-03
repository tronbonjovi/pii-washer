"""Pii Washer Component 5: Session Manager.

Orchestrates the full Pii Washer workflow by coordinating all other components.
Acts as the single interface the UI calls.
"""

import logging
import re

_UNSET = object()
_log = logging.getLogger(__name__)


class SessionManager:
    """Coordinates all Pii Washer components through a single interface."""

    VALID_DETECTION_STATUSES = ["pending", "confirmed", "rejected"]

    WORKFLOW_STATES = {
        "user_input":        {"can_analyze": True,  "can_edit_detections": False, "can_depersonalize": False, "can_load_response": False, "can_repersonalize": False},
        "analyzed":          {"can_analyze": False, "can_edit_detections": True,  "can_depersonalize": True,  "can_load_response": False, "can_repersonalize": False},
        "depersonalized":    {"can_analyze": False, "can_edit_detections": False, "can_depersonalize": False, "can_load_response": True,  "can_repersonalize": False},
        "awaiting_response": {"can_analyze": False, "can_edit_detections": False, "can_depersonalize": False, "can_load_response": False, "can_repersonalize": True},
        "repersonalized":    {"can_analyze": False, "can_edit_detections": False, "can_depersonalize": False, "can_load_response": False, "can_repersonalize": False},
        "closed":            {"can_analyze": False, "can_edit_detections": False, "can_depersonalize": False, "can_load_response": False, "can_repersonalize": False},
    }

    def __init__(self, store=None, document_loader=None, detection_engine=_UNSET,
                 placeholder_generator=None, substitution_engine=None):
        if store is None:
            from pii_washer.temp_data_store import TempDataStore
            store = TempDataStore()
        self.store = store

        if document_loader is None:
            from pii_washer.document_loader import DocumentLoader
            document_loader = DocumentLoader()
        self.document_loader = document_loader

        if detection_engine is _UNSET:
            try:
                from pii_washer.pii_detection_engine import PIIDetectionEngine
                detection_engine = PIIDetectionEngine()
            except ImportError:
                _log.info("PII detection unavailable: spaCy or Presidio not installed")
                detection_engine = None
            except OSError as exc:
                # spacy.load() raises OSError when the language model is missing
                _log.warning("PII detection unavailable: spaCy model not found (%s)", exc)
                detection_engine = None
        self.detection_engine = detection_engine

        if placeholder_generator is None:
            from pii_washer.placeholder_generator import PlaceholderGenerator
            placeholder_generator = PlaceholderGenerator()
        self.placeholder_generator = placeholder_generator

        if substitution_engine is None:
            from pii_washer.text_substitution_engine import TextSubstitutionEngine
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

    def load_uploaded_content(self, text, source_format, filename):
        """Create a session from uploaded file content with correct metadata."""
        normalized = self.document_loader.load_text(text)
        session_id = self.store.create_session(
            normalized["text"], source_format, filename
        )
        return session_id

    def load_uploaded_bytes(self, content, extension, filename):
        """Create a session from raw binary upload bytes (e.g. .docx).

        Delegates extraction to DocumentLoader.load_bytes(), which routes
        through the extractor registry.
        """
        result = self.document_loader.load_bytes(content, extension, filename)
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
        if len(new_placeholder) > 50:
            raise ValueError("Placeholder cannot exceed 50 characters")
        if not re.match(r'^[A-Za-z0-9_\-\[\] ]+$', new_placeholder):
            raise ValueError(
                "Placeholder can only contain letters, numbers, underscores, "
                "hyphens, spaces, and brackets"
            )

        for detection in session["pii_detections"]:
            if detection["id"] != detection_id and detection.get("placeholder") == new_placeholder:
                raise ValueError(
                    f"Placeholder '{new_placeholder}' is already used by detection {detection['id']}. "
                    "Each detection must have a unique placeholder."
                )

        for detection in session["pii_detections"]:
            if detection["id"] == detection_id:
                detection["placeholder"] = new_placeholder
                self.store.update_session(session_id, {
                    "pii_detections": session["pii_detections"],
                })
                return detection

        raise ValueError(f"Detection not found: {detection_id}")

    def add_manual_detection(self, session_id, text_value, category):
        """Add a user-specified PII item to a session's detection list.

        Parameters:
            session_id: The session to add the detection to.
            text_value: The PII text to find and add.
            category: A valid PII category string (e.g., "NAME", "ADDRESS").

        Returns:
            A dict describing the added detection.
        """
        # 1. Validate session exists (KeyError propagates from store)
        session = self.store.get_session(session_id)

        # 2. Validate session status
        status = session["status"]
        if status != "analyzed":
            raise ValueError(
                f"Manual detection can only be added in 'analyzed' state, "
                f"current state: {status}"
            )

        # 3. Validate category
        if category not in self.placeholder_generator.CATEGORY_PREFIX_MAP:
            raise ValueError(f"Unknown category: {category}")

        # 4. Validate text_value
        if not text_value or not text_value.strip():
            raise ValueError("Text value cannot be empty")

        detections = session["pii_detections"]

        # 5. Check for exact duplicates (same value + same category, case-insensitive)
        for det in detections:
            if (det["original_value"].lower() == text_value.strip().lower()
                    and det["category"] == category):
                raise ValueError(
                    f"'{text_value}' is already detected as {category}. "
                    "You can confirm or edit it in the detection list."
                )

        # 6. Search original text for all occurrences (case-insensitive, literal)
        original_text = session["original_text"]
        positions = []
        for match in re.finditer(re.escape(text_value.strip()), original_text, re.IGNORECASE):
            positions.append({"start": match.start(), "end": match.end()})

        # 7. Handle no matches
        if not positions:
            raise ValueError(
                f"'{text_value}' was not found in the document text."
            )

        # 8. Determine next placeholder counter for this category
        prefix = self.placeholder_generator.CATEGORY_PREFIX_MAP[category]
        max_counter = 0
        for det in detections:
            ph = det.get("placeholder", "")
            # Match pattern like [Person_3] for the same category prefix
            ph_match = re.match(r'^\[' + re.escape(prefix) + r'_(\d+)\]$', ph)
            if ph_match:
                max_counter = max(max_counter, int(ph_match.group(1)))

        placeholder = self.placeholder_generator.generate_placeholder(
            category, max_counter + 1
        )

        # 9. Assign detection ID
        max_id = 0
        for det in detections:
            id_match = re.match(r'^pii_(\d+)$', det["id"])
            if id_match:
                max_id = max(max_id, int(id_match.group(1)))
        new_id = f"pii_{max_id + 1:03d}"

        # 10. Build detection entry — use casing from first occurrence in text
        first_occurrence = original_text[positions[0]["start"]:positions[0]["end"]]
        new_detection = {
            "id": new_id,
            "category": category,
            "original_value": first_occurrence,
            "placeholder": placeholder,
            "positions": positions,
            "confidence": 1.0,
            "status": "pending",
            "source": "manual",
        }

        # 11. Append and save
        detections.append(new_detection)
        self.store.update_session(session_id, {
            "pii_detections": detections,
        })

        # 12. Return result
        return {
            "detection_id": new_id,
            "original_value": first_occurrence,
            "category": category,
            "placeholder": placeholder,
            "positions": positions,
            "occurrences_found": len(positions),
            "source": "manual",
        }

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

    def reset(self):
        return self.store.secure_clear()

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
