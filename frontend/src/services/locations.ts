import type { Location } from "../types";
import { getJson } from "./http";

export function fetchLocations(): Promise<Location[]> {
  return getJson<Location[]>("/locations");
}
