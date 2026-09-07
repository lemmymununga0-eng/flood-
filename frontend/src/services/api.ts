import type {
  Alert,
  AlertCreateInput,
  AuthUser,
  CitizenReport,
  CitizenReportCreateInput,
  DataSourceEntry,
  FloodEvent,
  Location,
  LoginInputData,
  ModelVersionEntry,
  Prediction,
  RegisterInput,
  SystemStatus,
  TokenResponse,
  WeatherIngestResult,
} from "../types";

const API_BASE = "http://localhost:8000/api/v1";
const TOKEN_STORAGE_KEY = "floodshield_access_token";

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Storage unavailable (private browsing, etc.) — auth still works for this tab
    // via in-memory AuthContext state, it just won't survive a reload.
  }
}

interface ApiErrorBody {
  error?: string;
  message?: string;
  fields?: unknown;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, body: ApiErrorBody | string) {
    const message = typeof body === "string" ? body : body.message ?? `Request failed with ${status}`;
    super(message);
    this.status = status;
    this.code = typeof body === "object" ? body.error : undefined;
  }
}

async function parseErrorBody(res: Response): Promise<ApiErrorBody | string> {
  try {
    return (await res.json()) as ApiErrorBody;
  } catch {
    return res.statusText;
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }
  return res.json() as Promise<T>;
}

async function authedRequest<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const token = getStoredToken();
  if (!token) {
    throw new ApiError(401, "You must be signed in to do this.");
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }
  return res.json() as Promise<T>;
}

// --- Auth ---

export async function login(input: LoginInputData): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorBody(res));
  return res.json() as Promise<TokenResponse>;
}

export async function register(input: RegisterInput): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorBody(res));
  return res.json() as Promise<TokenResponse>;
}

export function fetchMe(): Promise<AuthUser> {
  return authedRequest<AuthUser>("/auth/me");
}

// --- Locations / flood events / predictions ---

export function fetchLocations(): Promise<Location[]> {
  return getJson<Location[]>("/locations");
}

export function fetchFloodEvents(): Promise<FloodEvent[]> {
  return getJson<FloodEvent[]>("/flood-events");
}

export function fetchPredictions(): Promise<Prediction[]> {
  return getJson<Prediction[]>("/predictions");
}

export async function ingestWeather(locationId: number): Promise<WeatherIngestResult> {
  const res = await fetch(`${API_BASE}/weather/${locationId}/ingest`, { method: "POST" });
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }
  return res.json() as Promise<WeatherIngestResult>;
}

// --- Alerts (creation requires ADMIN/ANALYST/OPERATOR — enforced server-side) ---

export function fetchAlerts(): Promise<Alert[]> {
  return getJson<Alert[]>("/alerts");
}

export function createAlert(input: AlertCreateInput): Promise<Alert> {
  return authedRequest<Alert>("/alerts", { method: "POST", body: input });
}

// --- Citizen reports ---

export function fetchCitizenReports(): Promise<CitizenReport[]> {
  return getJson<CitizenReport[]>("/citizen-reports");
}

export function submitCitizenReport(input: CitizenReportCreateInput): Promise<CitizenReport> {
  return authedRequest<CitizenReport>("/citizen-reports", { method: "POST", body: input });
}

export function moderateCitizenReport(
  id: number,
  status: "verified" | "rejected",
  reviewNote: string,
): Promise<CitizenReport> {
  return authedRequest<CitizenReport>(`/citizen-reports/${id}/moderate`, {
    method: "POST",
    body: { status, review_note: reviewNote },
  });
}

// --- Model registry / data sources / system status ---

export function fetchModels(): Promise<ModelVersionEntry[]> {
  return getJson<ModelVersionEntry[]>("/models");
}

export function fetchDataSources(): Promise<DataSourceEntry[]> {
  return getJson<DataSourceEntry[]>("/data-sources");
}

export function checkDataSource(id: number): Promise<DataSourceEntry> {
  return authedRequest<DataSourceEntry>(`/data-sources/${id}/check`, { method: "POST" });
}

export function fetchSystemStatus(): Promise<SystemStatus> {
  return getJson<SystemStatus>("/system-status");
}
