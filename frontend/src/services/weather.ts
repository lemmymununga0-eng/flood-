import type { WeatherObservation, WeatherIngestResult } from "../types";
import { API_BASE, ApiError, getJson, parseErrorBody } from "./http";

export async function ingestWeather(locationId: number): Promise<WeatherIngestResult> {
  const res = await fetch(`${API_BASE}/weather/${locationId}/ingest`, { method: "POST" });
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }
  return res.json() as Promise<WeatherIngestResult>;
}

export interface WeatherSummaryDay {
  date: string;
  mean_rainfall_mm: number | null;
  max_rainfall_mm: number | null;
  mean_temperature_c: number | null;
  mean_humidity_pct: number | null;
  observations: number;
}

export interface WeatherSummary {
  source: string;
  days: WeatherSummaryDay[];
}

/** Real daily aggregates across all stored NASA POWER observations. */
export function fetchWeatherSummary(): Promise<WeatherSummary> {
  return getJson<WeatherSummary>("/weather/summary");
}

/** Stored observations for one location, newest first.
 *
 * Backs the "Stored weather history" panel on Location Detail. The endpoint already
 * existed and was correct; nothing in the UI called it, so ingested data was written
 * and then never shown. */
export function fetchLocationObservations(locationId: number): Promise<WeatherObservation[]> {
  return getJson<WeatherObservation[]>(`/weather/${locationId}`);
}
