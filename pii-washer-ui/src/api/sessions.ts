import apiClient from './client';
import type {
  Session,
  SessionListItem,
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

export async function listSessions(): Promise<SessionListItem[]> {
  const { data } = await apiClient.get<SessionListItem[]>('/sessions');
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

export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/sessions/${sessionId}`);
}

export async function clearAllSessions(): Promise<{ deleted_count: number }> {
  const { data } = await apiClient.delete<{ deleted_count: number }>('/sessions');
  return data;
}

export async function exportSession(sessionId: string): Promise<string> {
  const { data } = await apiClient.get<string>(`/sessions/${sessionId}/export`);
  return typeof data === 'string' ? data : JSON.stringify(data);
}

export async function importSession(sessionData: string): Promise<{ session_id: string }> {
  const { data } = await apiClient.post<{ session_id: string }>('/sessions/import', {
    session_data: sessionData,
  });
  return data;
}
