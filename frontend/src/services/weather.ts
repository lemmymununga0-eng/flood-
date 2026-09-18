import type { WeatherIngestResult } from "../types";
import { API_BASE, ApiError, parseErrorBody } from "./http";

export async function ingestWeather(locationId: number): Promise<WeatherIngestResult> {
  const res = await fetch(`${API_BASE}/weather/${locationId}/ingest`, { method: "POST" });
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }
  return res.json() as Promise<WeatherIngestResult>;
}
