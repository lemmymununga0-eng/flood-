import type {
  Alert,
  AlertCreateInput,
  FloodEvent,
  Location,
  Prediction,
  SystemStatus,
  WeatherIngestResult,
} from "../types";

const API_BASE = "http://localhost:8000/api/v1";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} fetching ${path}`);
  }
  return res.json() as Promise<T>;
}

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
    throw new Error(`${res.status} ${res.statusText} ingesting weather for location ${locationId}`);
  }
  return res.json() as Promise<WeatherIngestResult>;
}

export function fetchAlerts(): Promise<Alert[]> {
  return getJson<Alert[]>("/alerts");
}

export async function createAlert(input: AlertCreateInput): Promise<Alert> {
  const res = await fetch(`${API_BASE}/alerts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<Alert>;
}

export function fetchSystemStatus(): Promise<SystemStatus> {
  return getJson<SystemStatus>("/system-status");
}
