import type { AuthConfig, AuthErrorPayload, LoginResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class AuthApiError extends Error {
  constructor(
    public status: number,
    public payload: AuthErrorPayload,
  ) {
    super(payload.detail ?? "Auth error");
  }
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const res = await fetch(`${API_BASE}/auth/config`, { credentials: "include" });
  if (!res.ok) throw new Error(`auth config failed: ${res.status}`);
  return res.json();
}

export async function login(params: {
  email: string;
  password: string;
  captcha_token?: string | null;
}): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: params.email,
      password: params.password,
      captcha_token: params.captcha_token ?? null,
    }),
  });
  if (!res.ok) {
    const payload = (await res.json().catch(() => ({}))) as AuthErrorPayload;
    throw new AuthApiError(res.status, payload);
  }
  return res.json();
}
