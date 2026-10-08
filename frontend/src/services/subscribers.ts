import type { SmsDelivery, SmsSubscriber, SmsSubscriberInput } from "../types";
import { authedRequest } from "./http";

// Staff-only (ADMIN/ANALYST/OPERATOR) — enforced server-side.

export function fetchSubscribers(): Promise<SmsSubscriber[]> {
  return authedRequest<SmsSubscriber[]>("/sms-subscribers");
}

export function addSubscriber(input: SmsSubscriberInput): Promise<SmsSubscriber> {
  return authedRequest<SmsSubscriber>("/sms-subscribers", { method: "POST", body: input });
}

export function removeSubscriber(id: number): Promise<{ deleted: number }> {
  return authedRequest<{ deleted: number }>(`/sms-subscribers/${id}`, { method: "DELETE" });
}

export function testSubscriber(id: number): Promise<SmsDelivery[]> {
  return authedRequest<SmsDelivery[]>(`/sms-subscribers/${id}/test`, { method: "POST" });
}
