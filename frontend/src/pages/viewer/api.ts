/**
 * 閲覧 API の呼び出し（fetch）。アプリ本体の api（axios 等）は読み込まない。
 * トークンは localStorage `viewer_access_token`（読み書きは try/catch。使えなくても画面は動く）。
 */
import type { ViewerInventoryResponse, ViewerLoginResponse, ViewerSignupResponse } from "./types";

export const TOKEN_KEY = "viewer_access_token";
const API_BASE = "/api/v1/viewer";

export function readToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function writeToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* 保存できなくても、このタブの中では動く */
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* 何もしない */
  }
}

/** 失敗の応答。detail は API の detail の文字列（無ければ ''）。 */
export class ViewerApiError extends Error {
  readonly status: number;
  readonly detail: string;
  constructor(status: number, detail: string) {
    super(`viewer api ${status} ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = "";
    try {
      const body: unknown = await res.json();
      const d = (body as { detail?: unknown } | null)?.detail;
      if (typeof d === "string") detail = d;
    } catch {
      /* 本文が JSON でないときは detail なし */
    }
    throw new ViewerApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export function login(email: string, password: string): Promise<ViewerLoginResponse> {
  return request<ViewerLoginResponse>("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function logout(token: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function fetchInventory(token: string): Promise<ViewerInventoryResponse> {
  return request<ViewerInventoryResponse>("/inventory", {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** パスワード変更。成功すると新しいトークンが返る（古いトークンは使えなくなる）。 */
export function changePassword(token: string, current: string, next: string): Promise<ViewerLoginResponse> {
  return request<ViewerLoginResponse>("/password", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ current_password: current, new_password: next }),
  });
}

/** 再発行メールの申請。登録の有無にかかわらず {status:"accepted"}。 */
export function requestPasswordReset(email: string): Promise<{ status: string }> {
  return request<{ status: string }>("/password-reset/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

/** 再発行の確定。成功しても自動ログインはしない。 */
export function confirmPasswordReset(token: string, newPassword: string): Promise<{ status: string }> {
  return request<{ status: string }>("/password-reset/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

/** 申込。成功すると申込コードと招待リンク（作れなければ null）が返る。 */
export function signup(body: {
  email: string;
  line_name: string;
  inventory_issue: string;
  website: string;
}): Promise<ViewerSignupResponse> {
  return request<ViewerSignupResponse>("/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
