import type { Notification } from "../types";
import { authedRequest } from "./http";

export function fetchNotifications(): Promise<Notification[]> {
  return authedRequest<Notification[]>("/notifications");
}

export function markNotificationRead(id: number): Promise<Notification> {
  return authedRequest<Notification>(`/notifications/${id}/read`, { method: "POST" });
}
