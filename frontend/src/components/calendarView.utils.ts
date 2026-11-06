/**
 * calendarView.utils — CalendarView の純粋な関数と型（FullCalendar を import しない）
 *
 * 型は CalendarView.tsx から再 export する。呼ぶ側は FullCalendar を知らない。
 */
import type { ReactNode } from 'react';

export type CalendarViewMode = 'days' | 'month';
export type CalendarEventTone =
  | 'personal'
  | 'meeting'
  | 'purchase'
  | 'shipping'
  | 'billing'
  | 'release'
  | 'holiday'; // tokens.css の --cal-* と同じ7つ
export type CalendarEventLine = 'solid' | 'dashed';

export interface CalendarViewEvent {
  id: string;
  title: string;
  /** ISO 8601 */
  start: Date | string;
  end?: Date | string;
  allDay?: boolean;
  /** 既定 'personal' */
  tone?: CalendarEventTone;
  /** 既定 'solid'（見積もりは 'dashed'） */
  line?: CalendarEventLine;
  /** 重なりの赤枠 */
  conflict?: boolean;
}

export interface CalendarViewProps {
  mode: CalendarViewMode;
  /** days: 最初の列の日／month: その月の中の日 */
  date: Date | string;
  /** days の列の数。既定 7 */
  dayCount?: 1 | 2 | 3 | 4 | 5 | 6 | 7;
  events: CalendarViewEvent[];
  /** 既定 8 */
  startHour?: number;
  /** 既定 20 */
  endHour?: number;
  /** 既定 2。超えた分は「ほか N 件」 */
  monthMaxEvents?: number;
  renderEventContent?: (event: CalendarViewEvent, timeText: string) => ReactNode;
  onEventClick?: (id: string) => void;
  /** 月の升目の日付・「ほか N 件」を押したとき */
  onDayClick?: (date: Date) => void;
  ariaLabel: string;
  className?: string;
}

export interface HourRange {
  slotMinTime: string;
  slotMaxTime: string;
}

const MS_PER_HOUR = 60 * 60 * 1000;

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

function toHourString(hour: number): string {
  return `${pad2(hour)}:00:00`;
}

function sameLocalDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

/**
 * 時間割の表示範囲（時）を計算する。
 * - allDay の予定は数えない。end が無い時刻つきの予定は開始＋1時間として数える。
 * - 最小 = min(startHour, 各予定の開始の「時」切り捨て)
 * - 最大 = max(endHour, 各予定の終了の「時」切り上げ)。日をまたぐ予定はその日の 24:00 まで。
 * - 時刻は動かしている機械の時刻（Date の getHours）で読む。
 */
export function computeHourRange(
  events: ReadonlyArray<CalendarViewEvent>,
  startHour = 8,
  endHour = 20,
): HourRange {
  let minHour = startHour;
  let maxHour = endHour;

  for (const ev of events) {
    if (ev.allDay) continue;
    const start = new Date(ev.start);
    if (Number.isNaN(start.getTime())) continue;
    const end = ev.end !== undefined ? new Date(ev.end) : new Date(start.getTime() + MS_PER_HOUR);
    const endValid = !Number.isNaN(end.getTime());
    const effectiveEnd = endValid ? end : new Date(start.getTime() + MS_PER_HOUR);

    minHour = Math.min(minHour, start.getHours());

    let endH: number;
    if (!sameLocalDay(start, effectiveEnd)) {
      // 24:00 ちょうどで終わる予定（翌日 0:00）も同じ扱い
      endH = 24;
    } else {
      const h = effectiveEnd.getHours();
      const hasRemainder =
        effectiveEnd.getMinutes() > 0 ||
        effectiveEnd.getSeconds() > 0 ||
        effectiveEnd.getMilliseconds() > 0;
      endH = hasRemainder ? h + 1 : h;
    }
    maxHour = Math.max(maxHour, endH);
  }

  minHour = Math.max(0, Math.min(minHour, 24));
  maxHour = Math.max(0, Math.min(maxHour, 24));

  return {
    slotMinTime: toHourString(minHour),
    slotMaxTime: toHourString(maxHour),
  };
}

/** 予定の class 名（色・線・重なり）。null は除く。 */
export function eventClassNames(
  event: Pick<CalendarViewEvent, 'tone' | 'line' | 'conflict'>,
): string[] {
  const tone = event.tone ?? 'personal';
  const line = event.line ?? 'solid';
  return [
    'comp-calendar__event',
    `comp-calendar__event--tone-${tone}`,
    `comp-calendar__event--line-${line}`,
    event.conflict ? 'comp-calendar__event--conflict' : null,
  ].filter((c): c is string => c !== null);
}
