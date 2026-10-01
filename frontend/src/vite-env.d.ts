/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Overrides the API base URL (e.g. when the backend runs on a non-default port).
   * Falls back to http://localhost:8000/api/v1 when unset — see services/http.ts. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
