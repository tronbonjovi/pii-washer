from pathlib import Path

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import JSONResponse

from pii_washer.document_loader import DocumentLoader

from .config import ALLOWED_EXTENSIONS, APP_VERSION
from .errors import (
    _error_body,
    key_error_response,
    runtime_error_response,
    server_error_response,
    value_error_response,
)
from .models import (
    AnalyzeResponse,
    ConfirmedCountResponse,
    CreateSessionRequest,
    DeletedCountResponse,
    DepersonalizeResponse,
    Detection,
    DetectionPosition,
    EditPlaceholderRequest,
    HealthResponse,
    LoadResponseRequest,
    ManualDetectionRequest,
    ManualDetectionResponse,
    MatchSummary,
    RepersonalizeResponse,
    ResponseLoadedResponse,
    SessionCreatedResponse,
    UpdateDetectionStatusRequest,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sm(request: Request):
    return request.app.state.session_manager


def _to_session_created(session: dict) -> SessionCreatedResponse:
    return SessionCreatedResponse(
        session_id=session["session_id"],
        status=session["status"],
        source_format=session["source_format"],
        source_filename=session["source_filename"],
        original_text=session["original_text"],
    )


def _to_detection(d: dict) -> Detection:
    return Detection(
        id=d["id"],
        category=d["category"],
        original_value=d["original_value"],
        placeholder=d["placeholder"],
        status=d["status"],
        positions=[DetectionPosition(start=p["start"], end=p["end"]) for p in d["positions"]],
        confidence=d["confidence"],
        source=d.get("source", "auto"),
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    sm = _sm(request)
    return HealthResponse(
        status="ok",
        engine_available=sm.detection_engine is not None,
        version=APP_VERSION,
    )


# ---------------------------------------------------------------------------
# Session management — fixed paths first (before parameterized routes)
# ---------------------------------------------------------------------------

@router.post("/sessions", status_code=201, response_model=SessionCreatedResponse)
def create_session(body: CreateSessionRequest, request: Request):
    sm = _sm(request)
    try:
        session_id = sm.load_text(body.text)
        session = sm.get_session(session_id)
        return _to_session_created(session)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)


@router.post("/sessions/upload", status_code=201, response_model=SessionCreatedResponse)
async def upload_session(file: UploadFile, request: Request):
    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "UNSUPPORTED_FORMAT",
                f"File type '{suffix}' is not supported. Allowed: .txt, .md",
            ),
        )

    # Read content with streaming size check (1MB limit, aligned with DocumentLoader)
    max_size = DocumentLoader.MAX_FILE_SIZE
    chunks = []
    total = 0
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            return JSONResponse(
                status_code=413,
                content=_error_body(
                    "FILE_TOO_LARGE",
                    f"File exceeds the {max_size // (1024 * 1024)} MB limit",
                ),
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    # Decode in memory — never write PII to disk
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "DECODE_ERROR",
                "File could not be decoded as UTF-8 text",
            ),
        )

    try:
        sm = _sm(request)
        session_id = sm.load_uploaded_content(text, suffix, file.filename)
        session = sm.get_session(session_id)
        return _to_session_created(session)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)



@router.post("/sessions/reset", response_model=DeletedCountResponse)
def reset_session(request: Request):
    sm = _sm(request)
    deleted_count = sm.reset()
    return DeletedCountResponse(deleted_count=deleted_count)



# ---------------------------------------------------------------------------
# Session management — parameterized paths
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}")
def get_session(session_id: str, request: Request):
    sm = _sm(request)
    try:
        session = sm.get_session(session_id)
        return JSONResponse(content=session)
    except KeyError as exc:
        return key_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)


@router.get("/sessions/{session_id}/status")
def get_session_status(session_id: str, request: Request):
    sm = _sm(request)
    try:
        status = sm.get_session_status(session_id)
        return JSONResponse(content=status)
    except KeyError as exc:
        return key_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)



# ---------------------------------------------------------------------------
# Workflow actions
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/analyze", response_model=AnalyzeResponse)
def analyze(session_id: str, request: Request):
    sm = _sm(request)
    try:
        detections = sm.analyze(session_id)
        return AnalyzeResponse(
            detections=[_to_detection(d) for d in detections],
            detection_count=len(detections),
        )
    except KeyError as exc:
        return key_error_response(exc)
    except ValueError as exc:
        return value_error_response(exc)
    except RuntimeError as exc:
        return runtime_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)


@router.post("/sessions/{session_id}/depersonalize", response_model=DepersonalizeResponse)
def depersonalize(session_id: str, request: Request):
    sm = _sm(request)
    try:
        depersonalized_text = sm.apply_depersonalization(session_id)
        session = sm.get_session(session_id)
        detections = session.get("pii_detections") or []
        confirmed_count = sum(1 for d in detections if d.get("status") == "confirmed")
        rejected_count = sum(1 for d in detections if d.get("status") == "rejected")
        return DepersonalizeResponse(
            depersonalized_text=depersonalized_text,
            confirmed_count=confirmed_count,
            rejected_count=rejected_count,
        )
    except KeyError as exc:
        return key_error_response(exc)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)


@router.post("/sessions/{session_id}/response", response_model=ResponseLoadedResponse)
def load_response(session_id: str, body: LoadResponseRequest, request: Request):
    sm = _sm(request)
    try:
        response_text = sm.load_response_text(session_id, body.text)
        session = sm.get_session(session_id)
        return ResponseLoadedResponse(
            response_text=response_text,
            status=session["status"],
        )
    except KeyError as exc:
        return key_error_response(exc)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)


@router.post("/sessions/{session_id}/repersonalize", response_model=RepersonalizeResponse)
def repersonalize(session_id: str, request: Request):
    sm = _sm(request)
    try:
        result = sm.apply_repersonalization(session_id)
        return RepersonalizeResponse(
            repersonalized_text=result["text"],
            match_summary=MatchSummary(
                matched=len(result["matched"]),
                unmatched_from_map=len(result["unmatched_from_map"]),
                unknown_in_text=len(result["unknown_in_text"]),
            ),
            unmatched_placeholders=result["unmatched_from_map"],
            unknown_in_text=result["unknown_in_text"],
        )
    except KeyError as exc:
        return key_error_response(exc)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)


# ---------------------------------------------------------------------------
# Detection management — fixed paths before parameterized
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/detections/confirm-all", response_model=ConfirmedCountResponse)
def confirm_all(session_id: str, request: Request):
    sm = _sm(request)
    try:
        count = sm.confirm_all_detections(session_id)
        return ConfirmedCountResponse(confirmed_count=count)
    except KeyError as exc:
        return key_error_response(exc)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)


@router.post("/sessions/{session_id}/detections", status_code=201, response_model=ManualDetectionResponse)
def add_manual_detection(session_id: str, body: ManualDetectionRequest, request: Request):
    sm = _sm(request)
    try:
        result = sm.add_manual_detection(session_id, body.text_value, body.category)
        return ManualDetectionResponse(
            detection_id=result["detection_id"],
            original_value=result["original_value"],
            category=result["category"],
            placeholder=result["placeholder"],
            positions=[DetectionPosition(start=p["start"], end=p["end"]) for p in result["positions"]],
            occurrences_found=result["occurrences_found"],
            source=result["source"],
        )
    except KeyError as exc:
        return key_error_response(exc)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)


@router.patch("/sessions/{session_id}/detections/{detection_id}", response_model=Detection)
def update_detection_status(
    session_id: str, detection_id: str, body: UpdateDetectionStatusRequest, request: Request
):
    sm = _sm(request)
    try:
        detection = sm.update_detection_status(session_id, detection_id, body.status)
        return _to_detection(detection)
    except KeyError as exc:
        return key_error_response(exc)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)


@router.patch("/sessions/{session_id}/detections/{detection_id}/placeholder", response_model=Detection)
def edit_placeholder(
    session_id: str, detection_id: str, body: EditPlaceholderRequest, request: Request
):
    sm = _sm(request)
    try:
        detection = sm.edit_detection_placeholder(session_id, detection_id, body.placeholder)
        return _to_detection(detection)
    except KeyError as exc:
        return key_error_response(exc)
    except ValueError as exc:
        return value_error_response(exc)
    except Exception as exc:
        return server_error_response(exc)
