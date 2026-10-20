export interface User {
  id: string;
  email: string;
  name: string;
  role: "ADMIN" | "STANDARD";
  active: boolean;
  must_change_password: boolean;
  created_at: string;
}
export interface Session {
  user: User;
  csrf_token: string;
}
export interface AdminOverview {
  projects: number;
  jobs: number;
  users: number;
  active_jobs: number;
  completed_jobs: number;
}
export interface AuditEvent {
  id: string;
  actor_id: string | null;
  actor_name: string | null;
  actor_email: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  project_id: string | null;
  job_id: string | null;
  created_at: string;
}
export type ProviderMode = "blocked" | "demo" | "openai";
export interface Health {
  status: string;
  provider_mode: ProviderMode;
  database: string;
  auth_required: boolean;
}
export interface Project {
  id: string;
  name: string;
  client: string;
  status: string;
  created_at: string;
  survey_count: number;
  job_count: number;
}
export interface Category {
  code: string;
  label: string;
}
export interface CodebookSource {
  filename: string;
  sheet: string;
  field_id: string;
  question_number: string;
  question_text: string;
  target_columns: string[];
  groupings: Record<string, string>;
}
export interface CodebookCatalog {
  key: string;
  sheet: string;
  field_id: string;
  question_number: string;
  question_text: string;
  categories: Category[];
  compatible: boolean;
  issues: string[];
  candidate_columns: string[];
}
export interface CodebookPreview {
  filename: string;
  sheets: string[];
  catalogs: CodebookCatalog[];
  warnings: string[];
}
export interface CodebookSelection {
  column_name: string;
  catalog_key: string;
  max_labels: number;
}
export interface CodebookImport {
  filename: string;
  codebooks: Codebook[];
  mappings: { column_name: string; codebook_id: string; question_text: string }[];
}
export interface Codebook {
  id: string;
  project_id: string;
  name: string;
  categories: Category[];
  max_labels: number;
  created_at: string;
  source?: CodebookSource | null;
}
export interface Survey {
  id: string;
  project_id: string;
  filename: string;
  total_records: number;
  columns: string[];
  preview: Record<string, unknown>[];
  created_at: string;
}
export interface JobQuestion {
  id: string;
  column_name: string;
  question_text: string;
  codebook_id: string;
  categories: Category[];
  max_labels: number;
}
export type JobStatus =
  | "PENDING"
  | "RUNNING"
  | "PAUSED"
  | "FAILED"
  | "COMPLETED";
export interface Metrics {
  api_calls: number;
  saved_calls: number;
  savings_pct: number;
  cost_usd: number | null;
  saved_usd: number | null;
  purity: number | null;
  records_per_second: number;
  eta_seconds: number | null;
  input_tokens: number;
  output_tokens: number;
}
export interface Job {
  id: string;
  project_id: string;
  survey_id: string;
  name: string;
  status: JobStatus;
  progress: number;
  total_records: number;
  processed_records: number;
  provider_mode: ProviderMode;
  pause_reason: string | null;
  metrics: Metrics;
  questions: JobQuestion[];
  created_at: string;
  updated_at: string;
}
export interface CodedRecord {
  id: string;
  job_id: string;
  question_id: string;
  response_id: number;
  column_name: string;
  text_original: string;
  codes: string[];
  confidence: number | null;
  was_grouped: boolean;
  prototype_id: string | null;
  review_status: "PENDING" | "APPROVED";
  review_reason: string | null;
}
export interface Snapshot {
  job: Job;
  records: CodedRecord[];
}
export interface Analytics {
  distribution: {
    question_id: string;
    column_name: string;
    code: string;
    label: string;
    count: number;
  }[];
  total_records: number;
  processed_records: number;
  pending_review: number;
}
