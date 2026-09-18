import type { CitizenReport, CitizenReportCreateInput } from "../types";
import { authedRequest, getJson } from "./http";

export function fetchCitizenReports(): Promise<CitizenReport[]> {
  return getJson<CitizenReport[]>("/citizen-reports");
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
