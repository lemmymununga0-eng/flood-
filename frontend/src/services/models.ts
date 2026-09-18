import type { ModelVersionEntry } from "../types";
import { getJson } from "./http";

export function fetchModels(): Promise<ModelVersionEntry[]> {
  return getJson<ModelVersionEntry[]>("/models");
}
