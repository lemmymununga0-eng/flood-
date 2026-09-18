import type { AuthUser, LoginInputData, RegisterInput, TokenResponse } from "../types";
import { API_BASE, ApiError, authedRequest, parseErrorBody } from "./http";

export async function login(input: LoginInputData): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorBody(res));
  return res.json() as Promise<TokenResponse>;
}

export async function register(input: RegisterInput): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorBody(res));
  return res.json() as Promise<TokenResponse>;
}

export function fetchMe(): Promise<AuthUser> {
  return authedRequest<AuthUser>("/auth/me");
}
