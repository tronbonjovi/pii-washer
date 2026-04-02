import apiClient from './client';
import type {
  Session,
  SessionCreatedResponse,
  SessionStatusResponse,
} from '@/types/api';

export async function createSession(text: string): Promise<SessionCreatedResponse> {
  const { data } = await apiClient.post<SessionCreatedResponse>('/sessions', { text });
  return data;
}

export async function uploadFile(file: File): Promise<SessionCreatedResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<SessionCreatedResponse>(
    '/sessions/upload',
    formData
  );
  return data;
}

export async function resetSession(): Promise<{ deleted_count: number }> {
  const { data } = await apiClient.post<{ deleted_count: number }>('/sessions/reset');
  return data;
}

export async function getSession(sessionId: string): Promise<Session> {
  const { data } = await apiClient.get<Session>(`/sessions/${sessionId}`);
  return data;
}

export async function getSessionStatus(sessionId: string): Promise<SessionStatusResponse> {
  const { data } = await apiClient.get<SessionStatusResponse>(`/sessions/${sessionId}/status`);
  return data;
}
