import { api } from "./client";

export type AuthStatus = {
  authenticated: boolean;
  console_url: string | null;
  expires_at: string | null;
};

export type LoginBody =
  | { mode: "token"; console_url: string; token: string }
  | { mode: "keysecret"; console_url: string; key: string; secret: string };

export const auth = {
  status: () => api.get<AuthStatus>("/api/auth/status"),
  login: (body: LoginBody) => api.post<{ authenticated: boolean }>("/api/auth/login", body),
  logout: () => api.post<{ authenticated: boolean }>("/api/auth/logout"),
};
