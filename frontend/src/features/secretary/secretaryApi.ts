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

/** ADR-1078: 予定のカルテで聞く欄（聞く順は backend が決める） */
export type KarteAsk = "title" | "start" | "end" | "add_meet";

export interface EventDraftData {
  title: string | null;
  start: string | null;
  end: string | null;
  is_all_day: boolean;
  location: string | null;
  description: string | null;
  calendar_type: "personal";
  is_meeting: boolean;
  add_meet: boolean | null;
  meet_available: boolean;
  ask: KarteAsk | null;
  ask_count: number;
}

/** ADR-1078: 会話の間だけ持つ予定のカルテ（保存しない。閉じたら消す） */
export interface EventKarte {
  title: string | null;
  start: string | null;
  end: string | null;
  is_all_day: boolean;
  location: string | null;
  description: string | null;
  is_meeting: boolean;
  add_meet: boolean | null;
  asked: KarteAsk | null;
  asked_count: number;
}

/** 返ってきた下書きから次のカルテを作る（同じ名前の欄・asked ← ask・asked_count ← ask_count） */
export function karteFromDraft(draft: EventDraftData): EventKarte {
  return {
    title: draft.title,
    start: draft.start,
    end: draft.end,
    is_all_day: draft.is_all_day,
    location: draft.location,
    description: draft.description,
    is_meeting: draft.is_meeting,
    add_meet: draft.add_meet,
    asked: draft.ask,
    asked_count: draft.ask_count,
  };
}

export type AssistantReply =
  | { kind: "invoice"; draft: InvoiceDraftData; candidates: Candidates }
  | { kind: "event"; draft: EventDraftData; candidates: Candidates }
  | { kind: "unknown"; draft: { reply: string }; candidates: Candidates };

/** 本文には karte の鍵を必ず載せる（カルテが無ければ null）。backend は鍵の有無で新しい画面か古い画面かを分ける */
export function sendSecretaryMessage(text: string, karte: EventKarte | null = null): Promise<AssistantReply> {
  return api.postWithTimeout<AssistantReply>("/assistant/messages", { text, karte }, SECRETARY_TIMEOUT_MS);
}

export type SecretaryErrorKind = "notReady" | "busy" | "timeout" | "unreadable" | "generic" | "forbidden" | "authFailed" | "agentFailed" | "rulesTooLong";

const KNOWN_CODES: Record<string, SecretaryErrorKind> = {
  not_ready: "notReady",
  busy: "busy",
  timeout: "timeout",
  unreadable: "unreadable",
  auth_failed: "authFailed",
  agent_failed: "agentFailed",
  rules_too_long: "rulesTooLong",
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
