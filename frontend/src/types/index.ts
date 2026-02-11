// ===== Enums =====

export type AlertCategory =
  | "natural_disaster"
  | "political"
  | "crime"
  | "health"
  | "terrorism"
  | "civil_unrest";

export type ReportStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "sent";

export type UserRole = "admin" | "viewer";

// ===== Models =====

export interface Alert {
  id: number;
  title: string;
  summary: string;
  full_content: string | null;
  category: AlertCategory;
  severity: number;
  country: string;
  region: string | null;
  latitude: number | null;
  longitude: number | null;
  sources: Record<string, unknown>[] | Record<string, unknown> | null;
  verified: boolean;
  verification_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  created_at: string;
}

export interface Report {
  id: number;
  title: string;
  summary: string | null;
  content_json: ReportContent | null;
  pdf_path: string | null;
  status: ReportStatus;
  created_by: number;
  approved_by: number | null;
  geographic_scope: string | null;
  date_range_start: string | null;
  date_range_end: string | null;
  created_at: string;
}

export interface ReportAlertItem {
  id: number;
  title: string;
  summary: string;
  category: AlertCategory;
  severity: number;
  country: string;
  region: string | null;
  verified: boolean;
  verification_score: number | null;
  created_at: string;
}

export interface ReportContent {
  generated_at: string;
  geographic_scope: string;
  date_range: {
    start: string;
    end: string;
  };
  total_alerts: number;
  verified_alerts: number;
  high_severity_alerts: number;
  executive_summary: string;
  key_findings: string[];
  recommendations: string[];
  category_breakdown: Array<{ category: string; count: number }>;
  country_breakdown: Array<{ country: string; count: number }>;
  top_alerts: ReportAlertItem[];
}

export interface ReportGenerationRequest {
  title?: string | null;
  geographic_scope?: string | null;
  date_range_start?: string | null;
  date_range_end?: string | null;
  categories: AlertCategory[];
  max_alerts: number;
  include_unverified: boolean;
  generate_pdf: boolean;
}

export interface ReportGenerationResponse {
  report: Report;
  alerts_used: number;
}

export interface MailingList {
  id: number;
  name: string;
  geographic_regions: string[];
  description: string | null;
  created_by: number;
  created_at: string;
  subscriber_count: number;
}

export interface Subscriber {
  id: number;
  email: string;
  name: string | null;
  organization: string | null;
  mailing_list_id: number;
  created_at: string;
}

export interface CsvImportResult {
  total_rows: number;
  imported_count: number;
  skipped_count: number;
  invalid_rows: number;
}

export interface ReportDispatchResponse {
  task_id: string | null;
  status: string;
}

// ===== API Responses =====

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type AlertListResponse = PaginatedResponse<Alert>;

export interface SeverityDistributionItem {
  severity: number;
  count: number;
}

export interface CategoryDistributionItem {
  category: AlertCategory;
  count: number;
}

export interface AlertsStatsResponse {
  total_alerts: number;
  critical_alerts: number;
  countries_affected: number;
  severity_distribution: SeverityDistributionItem[];
  category_distribution: CategoryDistributionItem[];
}

export type AlertSortBy = "created_at" | "severity";
export type SortOrder = "asc" | "desc";

export interface AlertQueryParams {
  category?: AlertCategory;
  severity_min?: number;
  severity_max?: number;
  country?: string;
  region?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
  sort_by?: AlertSortBy;
  sort_order?: SortOrder;
  page?: number;
  page_size?: number;
}
