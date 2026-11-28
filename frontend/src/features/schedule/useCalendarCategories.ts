/**
 * 予定の種類の正本（GET /calendar/categories）。画面で種類の一覧を持たず、ここから読む（schedule-settings 便2a）。
 * 7 種の名前は i18n（schedule.calendarLabels.<key>）。name が付いていればその名前を出す。
 * ADR-027: 文字は t() 経由。読み方は useApiQuery（ADR-1054）。
 */
import { useMemo } from "react";
import { useApiQuery } from "../../lib/query/apiQuery";

/** 共有の値（画面の型の正本）。自分だけ・全員・チーム。裏側の値との変換は下の 1 組だけ */
export type CalendarShare = "self" | "all" | "team";
export type CalendarCategoryShare = CalendarShare;
/** 予定が裏側に持つ共有の値（calendar_type） */
export type CalendarTypeValue = "personal" | "shared" | "team";

/** 画面の共有 → 裏側の calendar_type（self↔personal・all↔shared・team↔team） */
export function shareToCalendarType(share: CalendarShare): CalendarTypeValue {
  if (share === "self") return "personal";
  return share === "team" ? "team" : "shared";
}

/** 裏側の calendar_type → 画面の共有。知らない値は全員（今までの丸めと同じ） */
export function calendarTypeToShare(calendarType: string | null | undefined): CalendarShare {
  if (calendarType === "personal") return "self";
  return calendarType === "team" ? "team" : "all";
}

/** 選び方（select）の値 → 共有。知らない値は全員 */
export function parseShare(value: string): CalendarShare {
  if (value === "self" || value === "team") return value;
  return "all";
}

export interface CalendarCategory {
  key: string;
  name: string | null;
  color_key: string | null;
  default_share: CalendarShare;
  /** 共有の初期値が team のときの初期のチーム（使っているチームだけ・昇順） */
  default_team_ids: number[];
  sort_order: number;
  is_active: boolean;
}

type Translate = (key: string, options?: { defaultValue?: string }) => string;

const EMPTY: CalendarCategory[] = [];

/** 種類の名前。名前が付いていればそれ・無ければ 7 種の i18n の名前・どちらも無ければ鍵そのまま */
export function categoryLabel(key: string, name: string | null | undefined, t: Translate): string {
  if (name) return name;
  return t(`schedule.calendarLabels.${key}`, { defaultValue: key });
}

export function useCalendarCategories() {
  const query = useApiQuery<CalendarCategory[]>("/calendar/categories");
  const categories = Array.isArray(query.data) ? query.data : EMPTY;
  const byKey = useMemo(() => new Map(categories.map((category) => [category.key, category])), [categories]);
  return { categories, byKey, isLoaded: query.data !== undefined, query };
}
