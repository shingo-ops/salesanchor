/**
 * 予定ごとの色（ADR-1081）。鍵の並びは裏側の正本 backend/app/services/event_colors.py と同じ
 * （backend/tests/test_event_colors_tokens.py が照らす）。色の値はトークン --event-color-* にだけある。
 */
export const EVENT_COLOR_KEYS = [
  "radicchio", "cherry_blossom", "flamingo", "tomato", "tangerine", "pumpkin",
  "mango", "banana", "citron", "avocado", "pistachio", "basil",
  "sage", "eucalyptus", "peacock", "cobalt", "lavender", "blueberry",
  "wisteria", "amethyst", "grape", "cocoa", "graphite", "birch",
] as const;

export type EventColorKey = (typeof EVENT_COLOR_KEYS)[number];

export function isEventColorKey(value: unknown): value is EventColorKey {
  return typeof value === "string" && (EVENT_COLOR_KEYS as readonly string[]).includes(value);
}

/** 色のトークンの文字。鍵の _ は - にする */
export function eventColorVar(key: EventColorKey): string {
  return `var(--event-color-${key.replace(/_/g, "-")})`;
}

/** 画面の文字の鍵 */
export function eventColorLabelKey(key: EventColorKey | null): string {
  return key === null ? "schedule.eventColors.default" : `schedule.eventColors.${key}`;
}

/** 予定の色を決める場所は 1 つ（箱・一覧の丸・仮の箱が通る）。色なしは持ち主の色 */
export function eventDisplayColor(colorKey: EventColorKey | null | undefined, ownerColor: string): string {
  return colorKey ? eventColorVar(colorKey) : ownerColor;
}
