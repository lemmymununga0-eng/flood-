import type { Prediction } from "../types";
import { getJson } from "./http";

export function fetchPredictions(): Promise<Prediction[]> {
  return getJson<Prediction[]>("/predictions");
}
