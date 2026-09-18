import type { SystemStatus } from "../types";
import { getJson } from "./http";

export function fetchSystemStatus(): Promise<SystemStatus> {
  return getJson<SystemStatus>("/system-status");
}
