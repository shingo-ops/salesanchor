/**
 * 秘書チャットの口の呼び出しと型（ADR-1056 段2）。
 * 口: POST /api/v1/assistant/messages（backend/app/routers/assistant.py）
 */

import { api, ApiError } from "../../lib/api";

/** 口が返すのは下書きだけ。何も作られない */
export const SECRETARY_TIMEOUT_MS = 100_000;
export const SECRETARY_MAX_TEXT = 1000;

export interface Candidate {
  id: number;
  name: string;
}

export interface Candidates {
  companies: Candidate[];
  contacts: Candidate[];
}

export interface DraftItem {
  product_name: string;
  quantity: number;
  unit_price: number | null;
}

export interface InvoiceDraftData {
  company_name: string | null;
  contact_name: string | null;
  items: DraftItem[];
  due_date: string | null;
  notes: string | null;
  currency: string;
}

export interface EventDraftData {
  title: string;
  start: string;
  end: string;
  is_all_day: boolean;
  location: string | null;
  description: string | null;
  calendar_type: "personal";
}

export type AssistantReply =
  | { kind: "invoice"; draft: InvoiceDraftData; candidates: Candidates }
  | { kind: "event"; draft: EventDraftData; candidates: Candidates }
  | { kind: "unknown"; draft: { reply: string }; candidates: Candidates };

export function sendSecretaryMessage(text: string): Promise<AssistantReply> {
  return api.postWithTimeout<AssistantReply>("/assistant/messages", { text }, SECRETARY_TIMEOUT_MS);
}

export type SecretaryErrorKind = "notReady" | "busy" | "timeout" | "unreadable" | "generic" | "forbidden" | "authFailed" | "agentFailed";

const KNOWN_CODES: Record<string, SecretaryErrorKind> = {
  not_ready: "notReady",
  busy: "busy",
  timeout: "timeout",
  unreadable: "unreadable",
  auth_failed: "authFailed",
  agent_failed: "agentFailed",
};

/** 失敗を言葉の種類に分ける。403 は forbidden（呼ぶ側が印を消す） */
export function classifySecretaryError(err: unknown): SecretaryErrorKind {
  // 画面の打ち切り（request が投げる AbortError）も timeout
  if (err instanceof Error && err.name === "AbortError") return "timeout";
  if (err instanceof ApiError) {
    if (err.status === 403) return "forbidden";
    const detail = err.responseDetail;
    if (detail && typeof detail === "object" && "code" in detail) {
      const code = (detail as { code: unknown }).code;
      if (typeof code === "string" && code in KNOWN_CODES) return KNOWN_CODES[code];
    }
  }
  return "generic";
}
