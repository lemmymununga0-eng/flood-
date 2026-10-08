import type { Alert, AlertCreated, AlertCreateInput } from "../types";
import { authedRequest, getJson } from "./http";

// Alert creation requires ADMIN/ANALYST/OPERATOR — enforced server-side.

export function fetchAlerts(): Promise<Alert[]> {
  return getJson<Alert[]>("/alerts");
}

export function createAlert(input: AlertCreateInput): Promise<AlertCreated> {
  return authedRequest<AlertCreated>("/alerts", { method: "POST", body: input });
}
