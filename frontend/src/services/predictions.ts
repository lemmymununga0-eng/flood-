import type { Prediction, RiskPredictionRequest, RiskPredictionResponse } from "../types";
import { API_BASE, ApiError, getJson, parseErrorBody } from "./http";

export function fetchPredictions(): Promise<Prediction[]> {
  return getJson<Prediction[]>("/predictions");
}

/** Run the real trained model against a supplied weather observation. Public
 * endpoint (no auth) — it computes a risk estimate and writes nothing. */
export async function requestPrediction(
  input: RiskPredictionRequest,
): Promise<RiskPredictionResponse> {
  const res = await fetch(`${API_BASE}/predictions/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }
  return res.json() as Promise<RiskPredictionResponse>;
}
