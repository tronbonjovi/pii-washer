import apiClient from './client';
import type { Detection, ManualDetectionResponse, PIICategory } from '@/types/api';

export async function updateDetectionStatus(
  sessionId: string,
  detectionId: string,
  status: 'pending' | 'confirmed' | 'rejected'
): Promise<Detection> {
  const { data } = await apiClient.patch<Detection>(
    `/sessions/${sessionId}/detections/${detectionId}`,
    { status }
  );
  return data;
}

export async function editDetectionPlaceholder(
  sessionId: string,
  detectionId: string,
  placeholder: string
): Promise<Detection> {
  const { data } = await apiClient.patch<Detection>(
    `/sessions/${sessionId}/detections/${detectionId}/placeholder`,
    { placeholder }
  );
  return data;
}

export async function confirmAllDetections(
  sessionId: string
): Promise<{ confirmed_count: number }> {
  const { data } = await apiClient.post<{ confirmed_count: number }>(
    `/sessions/${sessionId}/detections/confirm-all`
  );
  return data;
}

export async function addManualDetection(
  sessionId: string,
  textValue: string,
  category: PIICategory
): Promise<ManualDetectionResponse> {
  const { data } = await apiClient.post<ManualDetectionResponse>(
    `/sessions/${sessionId}/detections`,
    { text_value: textValue, category }
  );
  return data;
}
