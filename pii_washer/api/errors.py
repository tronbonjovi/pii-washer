import logging

from fastapi.responses import JSONResponse

from .exceptions import APIError

logger = logging.getLogger("pii_washer")


def _error_body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def classify_value_error(message: str) -> tuple[int, str]:
    """Legacy classifier for plain ValueErrors. Kept as a fallback so raise
    sites that haven't yet migrated to specific APIError subclasses still get
    the right HTTP status. New code should raise a concrete APIError subclass
    from pii_washer.api.exceptions instead."""
    if "session status is" in message or "expected '" in message:
        return 409, "INVALID_STATE"
    if "Detection not found:" in message:
        return 404, "NOT_FOUND"
    if "already detected as" in message:
        return 409, "DUPLICATE_DETECTION"
    if "was not found in the document" in message:
        return 422, "TEXT_NOT_FOUND"
    return 422, "VALIDATION_ERROR"


def key_error_response(exc: KeyError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=_error_body("NOT_FOUND", str(exc).strip("'")),
    )


def value_error_response(exc: ValueError) -> JSONResponse:
    message = str(exc)
    # Prefer type-based classification. Any APIError subclass carries its own
    # status + code, so we don't need to match on message wording.
    if isinstance(exc, APIError):
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_body(exc.error_code, message),
        )
    status_code, code = classify_value_error(message)
    return JSONResponse(
        status_code=status_code,
        content=_error_body(code, message),
    )


def runtime_error_response(exc: RuntimeError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=_error_body("ENGINE_UNAVAILABLE", str(exc)),
    )


def server_error_response(exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_body("SERVER_ERROR", "An unexpected error occurred"),
    )
