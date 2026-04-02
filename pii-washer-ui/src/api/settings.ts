import type { UpdateCheckResponse } from '@/types/api';
import apiClient from './client';

export async function checkForUpdates(): Promise<UpdateCheckResponse> {
  const { data } = await apiClient.get<UpdateCheckResponse>('/updates/check');
  return data;
}

export async function getAppVersion(): Promise<string> {
  const { data } = await apiClient.get<{ version: string }>('/health');
  return data.version;
}
