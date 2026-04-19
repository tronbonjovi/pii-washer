"""Unit tests for custom API exception classes and the error-response
handler's type-based classification."""

import json

from pii_washer.api.errors import value_error_response
from pii_washer.api.exceptions import (
    APIError,
    DetectionNotFoundError,
    DuplicateDetectionError,
    InvalidStateError,
    TextNotFoundError,
)


class TestExceptionClassAttributes:
    def test_invalid_state_error_attributes(self):
        exc = InvalidStateError("test")
        assert exc.http_status == 409
        assert exc.error_code == "INVALID_STATE"
        assert isinstance(exc, ValueError)

    def test_detection_not_found_attributes(self):
        exc = DetectionNotFoundError("test")
        assert exc.http_status == 404
        assert exc.error_code == "NOT_FOUND"
        assert isinstance(exc, ValueError)

    def test_duplicate_detection_attributes(self):
        exc = DuplicateDetectionError("test")
        assert exc.http_status == 409
        assert exc.error_code == "DUPLICATE_DETECTION"
        assert isinstance(exc, ValueError)

    def test_text_not_found_attributes(self):
        exc = TextNotFoundError("test")
        assert exc.http_status == 422
        assert exc.error_code == "TEXT_NOT_FOUND"
        assert isinstance(exc, ValueError)

    def test_base_api_error_defaults(self):
        exc = APIError("test")
        assert exc.http_status == 422
        assert exc.error_code == "VALIDATION_ERROR"


class TestValueErrorResponseTypeBased:
    """Verify the response handler uses isinstance checks for APIError."""

    def test_invalid_state_error_returns_409(self):
        resp = value_error_response(InvalidStateError("bad state"))
        assert resp.status_code == 409
        body = _body(resp)
        assert body["error"]["code"] == "INVALID_STATE"
        assert body["error"]["message"] == "bad state"

    def test_detection_not_found_returns_404(self):
        resp = value_error_response(DetectionNotFoundError("det_xyz"))
        assert resp.status_code == 404
        assert _body(resp)["error"]["code"] == "NOT_FOUND"

    def test_duplicate_detection_returns_409(self):
        resp = value_error_response(DuplicateDetectionError("dup"))
        assert resp.status_code == 409
        assert _body(resp)["error"]["code"] == "DUPLICATE_DETECTION"

    def test_text_not_found_returns_422(self):
        resp = value_error_response(TextNotFoundError("missing"))
        assert resp.status_code == 422
        assert _body(resp)["error"]["code"] == "TEXT_NOT_FOUND"

    def test_plain_value_error_falls_back_to_validation_error(self):
        """Un-migrated ValueErrors still default to 422 VALIDATION_ERROR."""
        resp = value_error_response(ValueError("random bad input"))
        assert resp.status_code == 422
        assert _body(resp)["error"]["code"] == "VALIDATION_ERROR"

    def test_legacy_string_match_state_error_still_works(self):
        """Backward-compat: raise ValueError with 'expected' wording → 409."""
        resp = value_error_response(
            ValueError("session status is 'foo', expected 'bar'")
        )
        assert resp.status_code == 409


def _body(resp):
    return json.loads(bytes(resp.body).decode("utf-8"))
