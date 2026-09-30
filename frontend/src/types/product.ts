
export interface Project {
  id: string;
  name: string;
  description: string;
  catalog_count?: number;
  job_count?: number;
  created_at: string;
  updated_at: string;
}

export interface CatalogEntry {
  code: string;
  label: string;
  description?: string;
  examples?: string[];
  exclusions?: string[];
  parent_code?: string | null;
}

export interface Catalog {
  id: string;
  project_id: string;
  name: string;
  version: number;
  multi_label: boolean;
  max_labels: number;
  entries: CatalogEntry[];
  validation: {
    valid?: boolean;
    errors?: string[];
    warnings?: string[];
  };
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  project_id?: string | null;
  session_id: string;
  name: string;
  kind: string;
  status: string;
  progress: number;
  processed_records: number;
  total_records: number;
  review_count?: number;
  pending_review_count?: number;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface ReviewItem {
  id: string;
  job_id: string;
  source_row: number;
  source_column: string;
  question: string;
  response: string;
  suggested_codes: string[];
  final_codes: string[];
  status: string;
  confidence?: number | null;
  reason: string;
  reviewer: string;
  comment: string;
  updated_at: string;
}
