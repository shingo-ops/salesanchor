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

/** 押した所・箱の四角（AnchorRect と同じ 4 辺＋幅・高さ） */
export interface CalendarViewRect {
  top: number;
  right: number;
  bottom: number;
  left: number;
  width: number;
  height: number;
}

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
  /** 担当者の色（DB が正本。呼ぶ側は受けた値をそのまま渡す）。あるときは tone より優先 */
  color?: string;
  /** false で動かせない（FullCalendar の予定ごとの editable）。無いときは金型の設定に従う */
  editable?: boolean;
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
  onEventClick?: (id: string, rect: CalendarViewRect | null) => void;
  /** 月の升目の日付・「ほか N 件」を押したとき */
  onDayClick?: (date: Date) => void;
  /** 時刻の書き方。'h24'＝今の「13:00」（既定）／'meridiem'＝「午後1時」 */
  timeStyle?: 'h24' | 'meridiem';
  /** 箱の並び。'inline'＝時刻・題名を 1 行（既定）／'stacked'＝題名の下に時刻 */
  eventLayout?: 'inline' | 'stacked';
  /** 見える時間。'events'＝startHour〜endHour を予定で広げる（既定）／'full'＝0〜24 時 */
  hourRange?: 'events' | 'full';
  /** true で、開いたとき今の時刻の 1 時間前の所を上に出す */
  scrollToNow?: boolean;
  /** 週の始まり。0＝日曜／1＝月曜（既定） */
  weekStart?: 0 | 1;
  /** true で包む枠の高さいっぱいに広げる（月の升目を下まで）。既定は中身の高さ */
  fillHeight?: boolean;
  /** 押す・引っぱるで選んだ範囲。渡したときだけ選べる */
  onSelectRange?: (start: Date, end: Date, allDay: boolean, anchor: CalendarViewRect | null) => void;
  /** 予定をつかんで動かした。渡したときだけ動かせる。失敗したら revert() で元に戻す */
  onEventMove?: (id: string, start: Date, end: Date | null, allDay: boolean, revert: () => void) => void;
  /** 予定の下の端を引いて長さを変えた。渡したときだけ変えられる */
  onEventResize?: (id: string, start: Date, end: Date | null, revert: () => void) => void;
  /** 月の「ほか N 件」。渡したときは onDayClick を呼ばずにこちらを呼ぶ */
  onMoreClick?: (date: Date, rect: CalendarViewRect | null) => void;
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
  event: Pick<CalendarViewEvent, 'tone' | 'line' | 'conflict' | 'color'>,
): string[] {
  const tone = event.tone ?? 'personal';
  const line = event.line ?? 'solid';
  return [
    'comp-calendar__event',
    `comp-calendar__event--tone-${tone}`,
    `comp-calendar__event--line-${line}`,
    event.color ? 'comp-calendar__event--owner-color' : null,
    event.conflict ? 'comp-calendar__event--conflict' : null,
  ].filter((c): c is string => c !== null);
}

/** 0〜23 時 → 12 時間表記の時と午前・午後。0 時は 午前12、12 時は 午後12（Google と同じ） */
export function toMeridiemHour(hour: number): { hour12: number; pm: boolean } {
  const h = ((hour % 24) + 24) % 24;
  return { hour12: h % 12 === 0 ? 12 : h % 12, pm: h >= 12 };
}

type Translate = (key: string, opts?: Record<string, unknown>) => string;

/** 1 つの時刻の本体（午前・午後なし）。分が 0 なら「8時」、あれば「12:30」 */
export function formatClock(date: Date, t: Translate): string {
  const { hour12 } = toMeridiemHour(date.getHours());
  const minute = date.getMinutes();
  return minute === 0
    ? t('calendarView.clockHour', { hour: hour12 })
    : t('calendarView.clockMinute', { hour: hour12, minute: String(minute).padStart(2, '0') });
}

/** 午前・午後を付けた時刻（目盛りにも使う） */
export function formatMeridiem(date: Date, t: Translate): string {
  const key = toMeridiemHour(date.getHours()).pm ? 'calendarView.pm' : 'calendarView.am';
  return t(key, { time: formatClock(date, t) });
}

/**
 * 箱の時刻「午後12:30～1:30」。終わりが無いときは始まりだけ。
 * omitSameMeridiem が真で、始まりと終わりの午前・午後が同じなら、終わりの午前・午後を書かない。
 */
export function formatTimeRange(
  start: Date,
  end: Date | null,
  t: Translate,
  omitSameMeridiem: boolean,
): string {
  const startText = formatMeridiem(start, t);
  if (!end) return startText;
  const same = toMeridiemHour(start.getHours()).pm === toMeridiemHour(end.getHours()).pm;
  const endText = omitSameMeridiem && same ? formatClock(end, t) : formatMeridiem(end, t);
  return t('calendarView.timeRange', { start: startText, end: endText });
}

/** 今の時刻の 1 時間前（0 時より前にしない）を "HH:00:00" で */
export function scrollTimeForNow(now: Date): string {
  return `${pad2(Math.max(0, now.getHours() - 1))}:00:00`;
}

/** 押しただけ（15 分以下）なら始まりから 1 時間に広げる。終日はそのまま */
export function normalizeSelectedRange(
  start: Date,
  end: Date,
  allDay: boolean,
): { start: Date; end: Date } {
  if (allDay) return { start, end };
  const QUARTER = 15 * 60 * 1000;
  if (end.getTime() - start.getTime() <= QUARTER) {
    return { start, end: new Date(start.getTime() + MS_PER_HOUR) };
  }
  return { start, end };
}

/** 要素の四角を CalendarViewRect に。要素が無ければ null */
export function rectOf(el: Element | null | undefined): CalendarViewRect | null {
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return { top: r.top, right: r.right, bottom: r.bottom, left: r.left, width: r.width, height: r.height };
}

/** 押した 1 点を幅・高さ 0 の四角に。イベントが無ければ null */
export function pointRect(ev: { clientX: number; clientY: number } | null | undefined): CalendarViewRect | null {
  if (!ev) return null;
  return { top: ev.clientY, bottom: ev.clientY, left: ev.clientX, right: ev.clientX, width: 0, height: 0 };
}
