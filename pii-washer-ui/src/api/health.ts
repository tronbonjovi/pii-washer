import apiClient from './client';
import type { HealthResponse } from '@/types/api';

export async function checkHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health');
  return data;
}
