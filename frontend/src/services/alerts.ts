import type { Alert, AlertCreateInput } from "../types";
import { authedRequest, getJson } from "./http";

// Alert creation requires ADMIN/ANALYST/OPERATOR — enforced server-side.

export function fetchAlerts(): Promise<Alert[]> {
  return getJson<Alert[]>("/alerts");
}

export function createAlert(input: AlertCreateInput): Promise<Alert> {
  return authedRequest<Alert>("/alerts", { method: "POST", body: input });
}
