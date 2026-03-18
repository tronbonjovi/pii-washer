import apiClient from './client';
import type {
  AnalyzeResponse,
  DepersonalizeResponse,
  LoadResponseResponse,
  RepersonalizeResponse,
} from '@/types/api';

export async function analyzeSession(sessionId: string): Promise<AnalyzeResponse> {
  const { data } = await apiClient.post<AnalyzeResponse>(`/sessions/${sessionId}/analyze`);
  return data;
}

export async function depersonalizeSession(sessionId: string): Promise<DepersonalizeResponse> {
  const { data } = await apiClient.post<DepersonalizeResponse>(
    `/sessions/${sessionId}/depersonalize`
  );
  return data;
}

export async function loadResponseText(
  sessionId: string,
  text: string
): Promise<LoadResponseResponse> {
  const { data } = await apiClient.post<LoadResponseResponse>(
    `/sessions/${sessionId}/response`,
    { text }
  );
  return data;
}

export async function repersonalizeSession(sessionId: string): Promise<RepersonalizeResponse> {
  const { data } = await apiClient.post<RepersonalizeResponse>(
    `/sessions/${sessionId}/repersonalize`
  );
  return data;
}
