/**
 * API Service - HTTP client for backend communication
 */
import axios, { AxiosError } from 'axios';
import type {
  UploadResponse,
  ProcessResponse,
  ProgressResponse,
  StopResponse,
  ProcessingConfig,
  APIError
} from '../types';

// Get API URL from environment or use default (relative in prod, localhost in dev)
// @ts-ignore
const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error handler
export const handleAPIError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<APIError>;
    if (axiosError.response?.data?.error) {
      return axiosError.response.data.error;
    }
    if (axiosError.message) {
      return axiosError.message;
    }
  }
  return 'An unexpected error occurred';
};

/**
 * Upload responses and codes files
 */
export const uploadFiles = async (
  responsesFile: File,
  codesFile: File
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('responses', responsesFile);
  formData.append('codes', codesFile);

  const response = await apiClient.post<UploadResponse>('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

/**
 * Start processing survey responses
 */
export const startProcessing = async (
  sessionId: string,
  config: ProcessingConfig
): Promise<ProcessResponse> => {
  const response = await apiClient.post<ProcessResponse>('/api/process', {
    session_id: sessionId,
    ...config,
  });

  return response.data;
};

/**
 * Get processing progress (fallback for WebSocket)
 */
export const getProgress = async (sessionId: string): Promise<ProgressResponse> => {
  const response = await apiClient.get<ProgressResponse>(`/api/progress/${sessionId}`);
  return response.data;
};

/**
 * Stop processing
 */
export const stopProcessing = async (sessionId: string): Promise<StopResponse> => {
  const response = await apiClient.post<StopResponse>(`/api/stop/${sessionId}`);
  return response.data;
};

/**
 * Cleanup session and temporary files
 */
export const cleanupSession = async (sessionId: string): Promise<void> => {
  try {
    await apiClient.delete(`/api/cleanup/${sessionId}`);
  } catch (error) {
    console.warn('Cleanup failed:', error);
    // Don't throw, just log
  }
};

/**
 * Get download URL for processed responses
 */
export const getResponsesDownloadUrl = (sessionId: string): string => {
  return `${API_URL}/api/download/responses/${sessionId}`;
};

/**
 * Get download URL for updated codes
 */
export const getCodesDownloadUrl = (sessionId: string): string => {
  return `${API_URL}/api/download/codes/${sessionId}`;
};

/**
 * Health check
 */
export const healthCheck = async (): Promise<{ status: string }> => {
  const response = await apiClient.get('/health');
  return response.data;
};
