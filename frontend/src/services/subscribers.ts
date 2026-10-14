import type { SmsSubscriber, SmsSubscriberInput } from "../types";
import { authedRequest } from "./http";

// ADMIN-only — enforced server-side.

export function fetchSubscribers(): Promise<SmsSubscriber[]> {
  return authedRequest<SmsSubscriber[]>("/sms-subscribers");
}

export function addSubscriber(input: SmsSubscriberInput): Promise<SmsSubscriber> {
  return authedRequest<SmsSubscriber>("/sms-subscribers", { method: "POST", body: input });
}

export function removeSubscriber(id: number): Promise<{ deleted: number }> {
  return authedRequest<{ deleted: number }>(`/sms-subscribers/${id}`, { method: "DELETE" });
}

export function optOutSubscriber(id: number): Promise<SmsSubscriber> {
  return authedRequest<SmsSubscriber>(`/sms-subscribers/${id}/opt-out`, { method: "POST" });
}

export function resubscribe(id: number, consent_note: string): Promise<SmsSubscriber> {
  return authedRequest<SmsSubscriber>(`/sms-subscribers/${id}/resubscribe`, {
    method: "POST",
    body: { consent: true, consent_note },
  });
}
