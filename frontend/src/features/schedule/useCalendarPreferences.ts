/**
 * ひとりひとりの予定の初期値（GET /calendar/preferences）。開いたときの形・週の始まり・新しい予定の長さ・
 * Meet を付けるか・誰の予定を出すか。自分の分だけ。行が無い人は、今までと同じ動き（週・日曜・60 分・Meet なし・自分だけ）。
 * 画面側の既定値はこのファイルの DEFAULT_CALENDAR_PREFERENCES だけに置く。
 * ADR-027: 文字は t() 経由。読み方は useApiQuery（ADR-1054）。
 */
import { useMemo } from "react";
import { useApiQuery } from "../../lib/query/apiQuery";

export type PreferenceView = "day" | "threeDay" | "week" | "month" | "list";
export type PreferenceOpenOwners = "self" | "all" | "team";

export const PREFERENCE_VIEWS: readonly PreferenceView[] = ["day", "threeDay", "week", "month", "list"];
export const PREFERENCE_EVENT_MINUTES: readonly number[] = [15, 30, 45, 60, 90, 120];
export const PREFERENCE_OPEN_OWNERS: readonly PreferenceOpenOwners[] = ["self", "all", "team"];

export interface ApiCalendarPreferences {
  default_view: PreferenceView;
  week_start: 0 | 1;
  event_minutes: number;
  auto_meet: boolean;
  open_owners: PreferenceOpenOwners;
  open_team_id: number | null;
}

/** 行が無い人・読めない値の既定（サーバーの既定と同じ。画面側の置き場はここだけ） */
export const DEFAULT_CALENDAR_PREFERENCES: ApiCalendarPreferences = {
  default_view: "week",
  week_start: 0,
  event_minutes: 60,
  auto_meet: false,
  open_owners: "self",
  open_team_id: null,
};

/** 欠けた値・知らない値は既定に戻す */
export function normalizePreferences(raw: Partial<ApiCalendarPreferences> | null | undefined): ApiCalendarPreferences {
  const d = DEFAULT_CALENDAR_PREFERENCES;
  if (!raw) return d;
  return {
    default_view: PREFERENCE_VIEWS.includes(raw.default_view as PreferenceView) ? (raw.default_view as PreferenceView) : d.default_view,
    week_start: raw.week_start === 0 || raw.week_start === 1 ? raw.week_start : d.week_start,
    event_minutes:
      typeof raw.event_minutes === "number" && PREFERENCE_EVENT_MINUTES.includes(raw.event_minutes)
        ? raw.event_minutes
        : d.event_minutes,
    auto_meet: typeof raw.auto_meet === "boolean" ? raw.auto_meet : d.auto_meet,
    open_owners: PREFERENCE_OPEN_OWNERS.includes(raw.open_owners as PreferenceOpenOwners)
      ? (raw.open_owners as PreferenceOpenOwners)
      : d.open_owners,
    open_team_id: typeof raw.open_team_id === "number" ? raw.open_team_id : d.open_team_id,
  };
}

export function useCalendarPreferences(settings?: { enabled?: boolean }) {
  const query = useApiQuery<ApiCalendarPreferences>("/calendar/preferences", { enabled: settings?.enabled });
  const raw = query.data;
  // 読めるまでは既定値を返す（isLoaded で読めたかを見分ける）
  const prefs = useMemo(() => normalizePreferences(raw), [raw]);
  return { prefs, isLoaded: raw !== undefined, query };
}
