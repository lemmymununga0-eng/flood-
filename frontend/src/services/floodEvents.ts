import type { FloodEvent } from "../types";
import { getJson } from "./http";

export function fetchFloodEvents(): Promise<FloodEvent[]> {
  return getJson<FloodEvent[]>("/flood-events");
}
