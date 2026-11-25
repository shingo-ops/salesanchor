/**
 * 秘書チャットの口の呼び出しと型（ADR-1056 段2）。
 * 口: POST /api/v1/assistant/messages（backend/app/routers/assistant.py）
 */

import { api, ApiError } from "../../lib/api";
import { combineDateTime } from "../../pages/schedule/schedule-utils";

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
  /** 便W: 直す頼みの答えのときだけ真偽（直せたか）。ほかは null か無し */
  edited?: boolean | null;
  /** 便W2: 直す頼みで Meet を付けてと言われたが付けられない人のとき真（ほかは null か無し） */
  meet_refused?: boolean | null;
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
  /** 便W: 真なら確かめ待ちの下書きを声で直す頼み */
  edit?: boolean;
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

/** 便W: 日付と時刻の欄の値を、時差の印つき（YYYY-MM-DDTHH:mm:00±HH:mm）の文字にする */
export function toKarteTime(date: string, time: string): string {
  const d = combineDateTime(date, time);
  const pad = (n: number) => String(n).padStart(2, "0");
  const offset = -d.getTimezoneOffset();
  const sign = offset >= 0 ? "+" : "-";
  const abs = Math.abs(offset);
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:00${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  );
}

export type AssistantReply =
  | { kind: "invoice"; draft: InvoiceDraftData; candidates: Candidates }
  | { kind: "event"; draft: EventDraftData; candidates: Candidates }
  | { kind: "unknown"; draft: { reply: string }; candidates: Candidates };

/** 本文には karte の鍵を必ず載せる（カルテが無ければ null）。backend は鍵の有無で新しい画面か古い画面かを分ける */
export function sendSecretaryMessage(text: string, karte: EventKarte | null = null): Promise<AssistantReply> {
  return api.postWithTimeout<AssistantReply>("/assistant/messages", { text, karte }, SECRETARY_TIMEOUT_MS);
}

/** 読み上げの口（POST /assistant/speech）の待ち時間と 1 回の最大字数（backend の SpeechIn max_length と同じ） */
export const SPEECH_TIMEOUT_MS = 15_000;
export const SPEECH_MAX_CHARS = 300;

export interface VoiceSettings {
  voices: string[];
  default: string;
  selected: string;
}

export function getSecretaryVoice(): Promise<VoiceSettings> {
  return api.get<VoiceSettings>("/assistant/voice");
}

export function saveSecretaryVoice(voice: string): Promise<VoiceSettings> {
  return api.put<VoiceSettings>("/assistant/voice", { voice });
}

export function fetchSecretarySpeech(text: string): Promise<Blob> {
  return api.postBlob("/assistant/speech", { text }, SPEECH_TIMEOUT_MS);
}

/** 今月の読み上げの上限に達した失敗か */
export function isSpeechCapError(err: unknown): boolean {
  if (!(err instanceof ApiError)) return false;
  const detail = err.responseDetail;
  return !!detail && typeof detail === "object" && (detail as { code?: unknown }).code === "tts_monthly_cap_reached";
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
