// Shared HTTP plumbing used by every domain service file in this folder — the API
// base URL, token storage, error type, and the two low-level request helpers.

// Relative by default, so the browser talks to whatever origin served the app and
// vite's dev proxy (see vite.config.ts) forwards /api to the backend. This keeps the
// app same-origin, which means it works from localhost, 127.0.0.1 and the LAN address
// vite prints as "Network:" without any of them needing to be in the backend's CORS
// allowlist.
//
// The previous default was the absolute "http://localhost:8000/api/v1". That made every
// request cross-origin, and on a machine where port 8000 belongs to a different service
// it failed CORS outright — surfacing as "Unable to load data / Failed to fetch" on
// every page.
//
// Set VITE_API_BASE_URL to an absolute URL for a deployment whose API is on a different
// origin (that origin must then allow it via CORS).
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
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

export async function parseErrorBody(res: Response): Promise<ApiErrorBody | string> {
  try {
    return (await res.json()) as ApiErrorBody;
  } catch {
    return res.statusText;
  }
}

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }
  return res.json() as Promise<T>;
}

export async function authedRequest<T>(
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

export { API_BASE };
