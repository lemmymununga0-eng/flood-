import type { DataSourceEntry } from "../types";
import { authedRequest, getJson } from "./http";

export function fetchDataSources(): Promise<DataSourceEntry[]> {
  return getJson<DataSourceEntry[]>("/data-sources");
}

export function checkDataSource(id: number): Promise<DataSourceEntry> {
  return authedRequest<DataSourceEntry>(`/data-sources/${id}/check`, { method: "POST" });
}
