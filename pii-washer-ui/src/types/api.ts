// src/types/api.ts

// --- Session types ---

export type SessionStatus =
  | 'user_input'
  | 'analyzed'
  | 'depersonalized'
  | 'awaiting_response'
  | 'repersonalized';

export type DetectionStatus = 'pending' | 'confirmed' | 'rejected';

export type DetectionSource = 'auto' | 'manual';

export type PIICategory =
  | 'NAME'
  | 'ADDRESS'
  | 'PHONE'
  | 'EMAIL'
  | 'SSN'
  | 'DOB'
  | 'CCN'
  | 'IP'
  | 'URL';

export interface DetectionPosition {
  start: number;
  end: number;
}

export interface Detection {
  id: string;
  category: PIICategory;
  original_value: string;
  placeholder: string;
  status: DetectionStatus;
  positions: DetectionPosition[];
  confidence: number;
  source: DetectionSource;
}

export interface Session {
  session_id: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  source_format: string;
  source_filename: string | null;
  original_text: string;
  pii_detections: Detection[];
  depersonalized_text: string | null;
  response_text: string | null;
  repersonalized_text: string | null;
  unmatched_placeholders: string[];
}

export interface SessionListItem {
  session_id: string;
  status: SessionStatus;
  source_format: string;
  source_filename: string | null;
  created_at: string;
  detection_count: number;
}

export interface SessionStatusResponse {
  session_id: string;
  status: SessionStatus;
  source_format: string;
  source_filename: string | null;
  detection_count: number;
  confirmed_count: number;
  rejected_count: number;
  pending_count: number;
  has_depersonalized: boolean;
  has_response: boolean;
  has_repersonalized: boolean;
  can_analyze: boolean;
  can_edit_detections: boolean;
  can_depersonalize: boolean;
  can_load_response: boolean;
  can_repersonalize: boolean;
}

// --- Response types ---

export interface SessionCreatedResponse {
  session_id: string;
  status: SessionStatus;
  source_format: string;
  source_filename: string | null;
  original_text: string;
}

export interface AnalyzeResponse {
  detections: Detection[];
  detection_count: number;
}

export interface DepersonalizeResponse {
  depersonalized_text: string;
  confirmed_count: number;
  rejected_count: number;
}

export interface LoadResponseResponse {
  response_text: string;
  status: SessionStatus;
}

export interface MatchSummary {
  matched: number;
  unmatched_from_map: number;
  unknown_in_text: number;
}

export interface RepersonalizeResponse {
  repersonalized_text: string;
  match_summary: MatchSummary;
  unmatched_placeholders: string[];
  unknown_in_text: string[];
}

export interface ManualDetectionResponse {
  detection_id: string;
  original_value: string;
  category: PIICategory;
  placeholder: string;
  positions: DetectionPosition[];
  occurrences_found: number;
  source: DetectionSource;
}

export interface HealthResponse {
  status: string;
  engine_available: boolean;
  version: string;
}

// --- Error types ---

export interface APIErrorDetail {
  code: string;
  message: string;
  details: unknown | null;
}

export interface APIErrorResponse {
  error: APIErrorDetail;
}

// Normalized error shape produced by the Axios interceptor in src/api/client.ts
// Defined here (not in client.ts) to avoid circular imports when components import both
export interface APIError {
  code: string;
  message: string;
  details: unknown | null;
  httpStatus: number | null;
}

// Type guard for the normalized APIError shape (post-interceptor)
export function isAPIError(error: unknown): error is APIError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    typeof (error as Record<string, unknown>).code === 'string' &&
    'message' in error &&
    typeof (error as Record<string, unknown>).message === 'string' &&
    'httpStatus' in error
  );
}
