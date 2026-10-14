import type {
  SmsBroadcastDetail,
  SmsBroadcastSummary,
  SmsCompose,
  SmsPreview,
  SmsProviderStatus,
} from "../types";
import { authedRequest } from "./http";

// ADMIN-only. Every call here hits the real backend; nothing is simulated client-side.

export const fetchSmsStatus = () => authedRequest<SmsProviderStatus>("/sms/status");

export const previewSms = (input: SmsCompose & { subscriber_id?: number }) =>
  authedRequest<SmsPreview>("/sms/preview", { method: "POST", body: input });

export const sendTestSms = (
  input: SmsCompose & { subscriber_id: number; idempotency_key: string },
) =>
  authedRequest<SmsBroadcastDetail>("/sms/test", {
    method: "POST",
    body: { ...input, confirm: true },
  });

export const sendBroadcastSms = (
  input: SmsCompose & { idempotency_key: string; expected_recipient_count: number },
) =>
  authedRequest<SmsBroadcastDetail>("/sms/broadcasts", {
    method: "POST",
    body: { ...input, confirm: true },
  });

export const fetchSmsHistory = () => authedRequest<SmsBroadcastSummary[]>("/sms/broadcasts?limit=50");

export const fetchSmsBroadcast = (id: number) =>
  authedRequest<SmsBroadcastDetail>(`/sms/broadcasts/${id}`);

/** A fresh key per confirmation dialog: a retry or double-click re-uses it and cannot text twice. */
export function newIdempotencyKey(): string {
  return crypto.randomUUID().replace(/-/g, "");
}

/** The API returns UTC timestamps without a zone suffix; treat them as UTC, show local time. */
export function formatUtc(ts: string | null): string {
  if (!ts) return "—";
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(ts) ? ts : `${ts}Z`);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString();
}
