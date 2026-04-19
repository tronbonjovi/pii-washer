"""Custom API exception classes.

Each class extends ValueError (so existing `except ValueError` handlers
still catch them) and carries its HTTP status + machine-readable error
code. The api/errors.py response handler matches by type first, falling
back to string-matching for un-migrated ValueError raise sites.
"""


class APIError(ValueError):
    """Base class for API-handled exceptions.

    Subclasses set `http_status` and `error_code` as class attributes.
    """

    http_status: int = 422
    error_code: str = "VALIDATION_ERROR"


class InvalidStateError(APIError):
    """Raised when an operation is attempted in the wrong session state."""

    http_status = 409
    error_code = "INVALID_STATE"


class DetectionNotFoundError(APIError):
    """Raised when a detection id doesn't exist in the session."""

    http_status = 404
    error_code = "NOT_FOUND"


class DuplicateDetectionError(APIError):
    """Raised when a manual detection duplicates an existing one."""

    http_status = 409
    error_code = "DUPLICATE_DETECTION"


class TextNotFoundError(APIError):
    """Raised when a text value doesn't appear in the document."""

    http_status = 422
    error_code = "TEXT_NOT_FOUND"
