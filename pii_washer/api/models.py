from typing import Any

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    text: str


class LoadResponseRequest(BaseModel):
    text: str


class UpdateDetectionStatusRequest(BaseModel):
    status: str


class EditPlaceholderRequest(BaseModel):
    placeholder: str


class ManualDetectionRequest(BaseModel):
    text_value: str
    category: str



# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SessionCreatedResponse(BaseModel):
    session_id: str
    status: str
    source_format: str
    source_filename: str | None



class DetectionPosition(BaseModel):
    start: int
    end: int


class Detection(BaseModel):
    id: str
    category: str
    original_value: str
    placeholder: str
    status: str
    positions: list[DetectionPosition]
    confidence: float
    source: str = "auto"


class SessionDetailResponse(BaseModel):
    session_id: str
    status: str
    created_at: str
    updated_at: str
    source_format: str
    source_filename: str | None
    original_text: str
    pii_detections: list[Detection]
    depersonalized_text: str | None
    response_text: str | None
    repersonalized_text: str | None
    unmatched_placeholders: list[str]


class AnalyzeResponse(BaseModel):
    detections: list[Detection]
    detection_count: int


class DepersonalizeResponse(BaseModel):
    depersonalized_text: str
    confirmed_count: int
    rejected_count: int


class MatchSummary(BaseModel):
    matched: int
    unmatched_from_map: int
    unknown_in_text: int


class RepersonalizeResponse(BaseModel):
    repersonalized_text: str
    match_summary: MatchSummary
    unmatched_placeholders: list[str]
    unknown_in_text: list[str]


class ManualDetectionResponse(BaseModel):
    detection_id: str
    original_value: str
    category: str
    placeholder: str
    positions: list[DetectionPosition]
    occurrences_found: int
    source: str


class HealthResponse(BaseModel):
    status: str
    engine_available: bool
    version: str


class DeletedCountResponse(BaseModel):
    deleted_count: int


class ConfirmedCountResponse(BaseModel):
    confirmed_count: int



class ResponseLoadedResponse(BaseModel):
    response_text: str
    status: str


class UpdateCheckResponse(BaseModel):
    current_version: str
    latest_version: str | None
    update_available: bool
    release_url: str | None = None
    error: str | None = None
