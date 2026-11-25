/**
 * 予定の種類の正本（GET /calendar/categories）。画面で種類の一覧を持たず、ここから読む（schedule-settings 便2a）。
 * 7 種の名前は i18n（schedule.calendarLabels.<key>）。name が付いていればその名前を出す。
 * ADR-027: 文字は t() 経由。読み方は useApiQuery（ADR-1054）。
 */
import { useMemo } from "react";
import { useApiQuery } from "../../lib/query/apiQuery";

export type CalendarCategoryShare = "self" | "all";

export interface CalendarCategory {
  key: string;
  name: string | null;
  color_key: string | null;
  default_share: CalendarCategoryShare;
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
