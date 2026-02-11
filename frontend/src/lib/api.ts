import type {
  Alert,
  AlertListResponse,
  AlertQueryParams,
  AlertsStatsResponse,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: HeadersInit = { ...options.headers };
    const isFormDataBody =
      typeof FormData !== "undefined" && options.body instanceof FormData;
    if (!isFormDataBody && !(headers as Record<string, string>)["Content-Type"]) {
      (headers as Record<string, string>)["Content-Type"] = "application/json";
    }

    // Add auth token if available
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        (headers as Record<string, string>)["Authorization"] =
          `Bearer ${token}`;
      }
    }

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
      });
    } catch {
      throw new ApiError(0, "Unable to reach the server. Check your connection.");
    }

    if (!response.ok) {
      const errorBody = await this.tryParseJson(response);
      throw new ApiError(
        response.status,
        this.getErrorMessage(errorBody, response.statusText)
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const responseBody = await this.tryParseJson(response);
    return responseBody as T;
  }

  private async tryParseJson(response: Response): Promise<unknown> {
    const text = await response.text();
    if (!text) {
      return null;
    }

    try {
      return JSON.parse(text) as unknown;
    } catch {
      return { detail: text };
    }
  }

  private getErrorMessage(errorBody: unknown, fallbackMessage: string): string {
    if (typeof errorBody === "string" && errorBody.trim()) {
      return errorBody;
    }

    if (
      typeof errorBody === "object" &&
      errorBody !== null &&
      "detail" in errorBody &&
      typeof (errorBody as { detail?: unknown }).detail === "string"
    ) {
      return (errorBody as { detail: string }).detail;
    }

    return fallbackMessage || "Request failed";
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async postForm<T>(endpoint: string, formData: FormData): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: formData,
    });
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  private toQueryString(params: Record<string, string | number | undefined>): string {
    const searchParams = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined) {
        return;
      }
      if (typeof value === "string" && value.trim().length === 0) {
        return;
      }
      searchParams.set(key, String(value));
    });

    const queryString = searchParams.toString();
    return queryString ? `?${queryString}` : "";
  }

  // Health check
  async healthCheck() {
    return this.get<{ status: string; version: string; environment: string }>(
      "/health"
    );
  }

  async getAlerts(params: AlertQueryParams = {}): Promise<AlertListResponse> {
    return this.get<AlertListResponse>(
      `/alerts${this.toQueryString({
        category: params.category,
        severity_min: params.severity_min,
        severity_max: params.severity_max,
        country: params.country,
        region: params.region,
        start_date: params.start_date,
        end_date: params.end_date,
        search: params.search,
        sort_by: params.sort_by,
        sort_order: params.sort_order,
        page: params.page,
        page_size: params.page_size,
      })}`
    );
  }

  async getAlertStats(): Promise<AlertsStatsResponse> {
    return this.get<AlertsStatsResponse>("/alerts/stats");
  }

  async getAlert(alertId: number): Promise<Alert> {
    return this.get<Alert>(`/alerts/${alertId}`);
  }

  async downloadReportPdf(reportId: number): Promise<Blob> {
    const endpoint = `/reports/${reportId}/pdf`;
    const url = `${this.baseUrl}${endpoint}`;
    const headers: HeadersInit = {};

    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
      }
    }

    const response = await fetch(url, {
      method: "GET",
      headers,
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      throw new ApiError(
        response.status,
        errorBody?.detail || "Failed to download report PDF"
      );
    }

    return response.blob();
  }
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export const api = new ApiClient(API_BASE_URL);
