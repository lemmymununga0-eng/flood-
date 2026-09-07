import type { FloodEvent, Location, Prediction, WeatherIngestResult } from "../types";

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
