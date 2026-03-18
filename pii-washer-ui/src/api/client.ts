import axios from 'axios';
import type { APIErrorResponse } from '@/types/api';
import { apiBaseUrl } from '@/lib/runtime';
export type { APIError } from '@/types/api';

function extractHTTPErrorMessage(
  status: number,
  data: unknown,
  fallback: string,
): string {
  if (
    typeof data === 'object' &&
    data !== null &&
    'detail' in data &&
    Array.isArray((data as { detail?: unknown }).detail)
  ) {
    const parts = ((data as { detail: Array<{ msg?: unknown }> }).detail)
      .map((item) => item?.msg)
      .filter((msg): msg is string => typeof msg === 'string');
    if (parts.length > 0) {
      return parts.join('; ');
    }
  }

  if (
    typeof data === 'object' &&
    data !== null &&
    'detail' in data &&
    typeof (data as { detail?: unknown }).detail === 'string'
  ) {
    return (data as { detail: string }).detail;
  }

  return fallback || `Request failed with status ${status}`;
}

const apiClient = axios.create({
  baseURL: apiBaseUrl,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.error) {
      const apiError = error.response.data as APIErrorResponse;
      return Promise.reject({
        code: apiError.error.code,
        message: apiError.error.message,
        details: apiError.error.details,
        httpStatus: error.response.status,
      });
    }
    if (error.response) {
      return Promise.reject({
        code: 'HTTP_ERROR',
        message: extractHTTPErrorMessage(
          error.response.status,
          error.response.data,
          error.message,
        ),
        details: error.response.data ?? null,
        httpStatus: error.response.status,
      });
    }
    return Promise.reject({
      code: 'NETWORK_ERROR',
      message: error.message || 'Unable to reach the PII Washer backend',
      details: null,
      httpStatus: null,
    });
  }
);

export default apiClient;
