/**
 * 予定の共有先に選べるチーム（GET /calendar/teams）。使っているチームの名前と番号だけ（メンバーは出ない）。
 * teams.view の無い人も読める道。写しは作らず、ここから読む（schedule-settings 便2b）。
 * MultiSelect の selected・options[].value は文字なので、チームの番号（数）との変換はこのファイルの 1 組だけに置く。
 * ADR-027: 文字は t() 経由。読み方は useApiQuery（ADR-1054）。
 */
import { useMemo } from "react";
import { useApiQuery } from "../../lib/query/apiQuery";

export interface CalendarTeam {
  id: number;
  name: string;
}

const EMPTY: CalendarTeam[] = [];

/** チームの番号 → MultiSelect の値（文字） */
export function teamIdsToValues(ids: readonly number[]): string[] {
  return ids.map((id) => String(id));
}

/** MultiSelect の値（文字） → チームの番号（数）。数にならない値は落とす */
export function valuesToTeamIds(values: readonly string[]): number[] {
  return values.map((value) => Number(value)).filter((id) => Number.isInteger(id));
}

/** 2 つのチームの組が同じか（順番と重なりは見ない） */
export function sameTeamIds(a: readonly number[], b: readonly number[]): boolean {
  const left = [...new Set(a)].sort((x, y) => x - y);
  const right = [...new Set(b)].sort((x, y) => x - y);
  return left.length === right.length && left.every((id, index) => id === right[index]);
}

export function useCalendarTeams(settings?: { enabled?: boolean }) {
  const query = useApiQuery<CalendarTeam[]>("/calendar/teams", { enabled: settings?.enabled });
  const teams = Array.isArray(query.data) ? query.data : EMPTY;
  const byId = useMemo(() => new Map(teams.map((team) => [team.id, team])), [teams]);
  const options = useMemo(() => teams.map((team) => ({ value: String(team.id), label: team.name })), [teams]);
  return { teams, byId, options, isLoaded: query.data !== undefined, query };
}
