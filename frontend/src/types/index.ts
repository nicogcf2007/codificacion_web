/**
 * TypeScript type definitions for the Survey Coding application
 */

// Application state types
export type AppStep = 'upload' | 'configure' | 'manual-coding' | 'processing' | 'results';

export type ProcessingStatus = 'idle' | 'processing' | 'completed' | 'error' | 'stopped';

// Manual Coding
export interface FrequencyItem {
    text: string;
    count: number;
    variations: string[];
    display_text?: string;
}

export interface ManualCodingState {
    frequencies: Record<string, FrequencyItem[]>;
    // Mapping: {column: {text: code}}
    mappings: Record<string, Record<string, string>>; 
}

// ... existing types ...

export interface ProcessingConfig {
  columns: ColumnConfig[];
  question_column: string;
  max_new_labels: number;
  start_code: number;
  manual_mappings?: Record<string, Record<string, string>>;
}
export interface UploadedFiles {
  responses: File | null;
  codes: File | null;
}

// API Response types
export interface UploadResponse {
  session_id: string;
  columns: string[];
  questions: string[];
  message: string;
}

export interface ProcessResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface ProgressResponse {
  progress: number;
  status: ProcessingStatus;
  message: string;
  current_column?: string;
}

export interface StopResponse {
  status: string;
  message: string;
}

// Configuration types
export interface ColumnConfig {
  name: string;
  multiLabel: boolean;
  maxLabels: number;
  context: string;
  maxNewLabels?: number; // Added
}

export interface ProcessingConfig {
  columns: ColumnConfig[];
  question_column: string;
  max_new_labels: number;
  start_code: number;
  manual_mappings?: Record<string, Record<string, string>>;
}

// Session data
export interface SessionData {
  session_id: string | null;
  task_id: string | null;
  columns: string[];
  questions: string[];
}

// Progress update from WebSocket
export interface ProgressUpdate {
  progress: number;
  message: string;
  current_column?: string;
  processed_records?: number;
  total_records?: number;
}

// Status update from WebSocket
export interface StatusUpdate {
  status: ProcessingStatus;
  message: string;
}

// Review results
export interface ReviewResults {
  corrections_made: number;
  total_reviewed: number;
}

// Processing results
export interface ProcessingResults {
  processed_columns: number;
  total_records: number;
  new_labels_created?: number;
  review_results?: ReviewResults;
}

// Complete application state
export interface AppState {
  step: AppStep;
  sessionData: SessionData;
  files: UploadedFiles;
  config: ProcessingConfig;
  progress: number;
  status: ProcessingStatus;
  statusMessage: string;
  results: ProcessingResults | null;
}

// Error response from API
export interface APIError {
  error: string;
  details?: Record<string, any>;
  path?: string;
}
