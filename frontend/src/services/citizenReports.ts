import type { CitizenReport, CitizenReportCreateInput } from "../types";
import { API_BASE, authedRequest, getStoredToken, parseErrorBody, ApiError } from "./http";

// Sends the token when there is one: staff then see every report, a signed-in citizen also sees their
// own, and everyone else sees verified reports only. The server decides; an expired token is
// treated as anonymous rather than as an error.
export async function fetchCitizenReports(): Promise<CitizenReport[]> {
  const token = getStoredToken();
  const res = await fetch(`${API_BASE}/citizen-reports`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorBody(res));
  return res.json() as Promise<CitizenReport[]>;
}

export function submitCitizenReport(input: CitizenReportCreateInput): Promise<CitizenReport> {
  return authedRequest<CitizenReport>("/citizen-reports", { method: "POST", body: input });
}

export function moderateCitizenReport(
  id: number,
  status: "verified" | "rejected",
  reviewNote: string,
): Promise<CitizenReport> {
  return authedRequest<CitizenReport>(`/citizen-reports/${id}/moderate`, {
    method: "POST",
    body: { status, review_note: reviewNote },
  });
}
