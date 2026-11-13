import { formatMeridiem, formatTimeRange as formatEventTimeRange, type CalendarViewEvent } from "../../components/calendarView.utils";

export type ScheduleView = "day" | "threeDay" | "week" | "month" | "list";
export type DemoState = "normal" | "loading" | "empty";

export interface AnchorRect {
  top: number;
  right: number;
  bottom: number;
  left: number;
  width: number;
  height: number;
}

export interface ApiCalendarEvent {
  id: number;
  user_id: number | null;
  calendar_type: "shared" | "personal" | string;
  title: string;
  description: string | null;
  location: string | null;
  start_datetime: string;
  end_datetime: string;
  is_all_day: boolean;
  google_event_id: string | null;
  source: "app" | "google" | string;
  sync_status: string | null;
  created_by_user_id: number | null;
  created_at: string | null;
  updated_at: string | null;
  owner_name?: string | null;
  created_by_name: string | null;
  category?: string | null;
  meet_url?: string | null;
  recurrence_rule?: string | null;
  recurrence?: string | null;
  recurring_event_id?: number | null;
  occurrence_start?: string | null;
  is_first_occurrence?: boolean;
}

export interface ApiShift {
  id: number;
  user_id: number;
  shift_date: string;
  start_time: string;
  end_time: string;
  shift_type: string;
  notes: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ScheduleItem {
  id: string;
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  category: import("../../features/schedule/calendars.config").CalendarId | null;
  calendarType: "shared" | "personal";
  source: "app" | "google" | "shift";
  ownerUserId: number | null;
  ownerName: string | null;
  organizer?: string | null;
  location?: string | null;
  description?: string | null;
  createdByName?: string | null;
  meetUrl?: string | null;
  googleEventId?: string | null;
  /** 繰り返しの選び方（design §12.6）。単発は "none" */
  recurrence?: ScheduleRecurrence;
  /** 回のとき元の行の id。単発は null */
  recurringEventId?: number | null;
  /** 回の元の始まり（直した回でも元の日時）。単発は null */
  occurrenceStart?: Date | null;
  /** 1 回目の回か（サーバーが決める・§12.6.1 G1） */
  isFirstOccurrence?: boolean;
}

function parseLocalDate(date: string): Date {
  return new Date(date.includes("T") ? date : `${date}T00:00:00`);
}

function parseDateTime(date: string, time: string): Date {
  return new Date(`${date}T${time.length === 5 ? `${time}:00` : time}`);
}

export function addDays(date: Date, amount: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + amount);
  return next;
}

export function addMonths(date: Date, amount: number): Date {
  const next = new Date(date);
  next.setMonth(next.getMonth() + amount);
  return next;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function combineDateTime(date: string, time: string): Date {
  return parseDateTime(date, time);
}

type Translate = (key: string, opts?: Record<string, unknown>) => string;

/**
 * 作る小窓の日時の 1 行（design §3.9・G3 ②）。例「11月10日(火) 午前10時～午前11時」。
 * 日付が読めないときは空。終わりだけ読めないときは始まりだけ。
 */
export function formatDraftDateLine(
  value: { startDate: string; startTime: string; endDate: string; endTime: string; allDay: boolean },
  t: Translate,
  language: string,
): string {
  const day = (date: Date) =>
    new Intl.DateTimeFormat(language, { month: "long", day: "numeric", weekday: "short" }).format(date);
  const start = parseDateTime(value.startDate, value.allDay ? "00:00" : value.startTime);
  if (Number.isNaN(start.getTime())) return "";
  const end = parseDateTime(value.endDate, value.allDay ? "00:00" : value.endTime);
  const endValid = !Number.isNaN(end.getTime());
  if (value.allDay) {
    if (!endValid || value.endDate === value.startDate) {
      return t("schedule.dateTimeLine", { date: day(start), time: t("schedule.allDay") });
    }
    return t("calendarView.timeRange", { start: day(start), end: day(end) });
  }
  if (!endValid) return t("schedule.dateTimeLine", { date: day(start), time: formatMeridiem(start, t) });
  if (value.endDate === value.startDate) {
    return t("schedule.dateTimeLine", { date: day(start), time: formatEventTimeRange(start, end, t, false) });
  }
  return t("calendarView.timeRange", {
    start: t("schedule.dateTimeLine", { date: day(start), time: formatMeridiem(start, t) }),
    end: t("schedule.dateTimeLine", { date: day(end), time: formatMeridiem(end, t) }),
  });
}

/** 検索の結果の 2 行目（便5 G12）。終日は「11月10日(火) 終日」、時間ありは formatDraftDateLine と同じ形 */
export function formatSearchResultLine(item: ScheduleItem, t: Translate, language: string): string {
  return formatDraftDateLine(
    {
      startDate: formatDateInput(item.start),
      startTime: formatTimeInput(item.start),
      endDate: item.allDay ? formatDateInput(item.start) : formatDateInput(item.end),
      endTime: formatTimeInput(item.end),
      allDay: item.allDay,
    },
    t,
    language,
  );
}

export function formatDateInput(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function formatDayKey(date: Date): string {
  return formatDateInput(date);
}

export function formatDayLabel(date: Date, locale = "ja-JP"): string {
  return new Intl.DateTimeFormat(locale, { month: "numeric", day: "numeric", weekday: "short" }).format(date);
}

export function formatMonthLabel(date: Date, locale = "ja-JP"): string {
  return new Intl.DateTimeFormat(locale, { year: "numeric", month: "long" }).format(date);
}

export function formatTimeInput(date: Date): string {
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

export function getMonthCells(anchor: Date): Date[] {
  const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  const start = addDays(first, -first.getDay());
  return Array.from({ length: 42 }, (_, index) => addDays(start, index));
}

export function getWeekDays(anchor: Date): Date[] {
  const base = new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate());
  const start = addDays(base, -base.getDay());
  return Array.from({ length: 7 }, (_, index) => addDays(start, index));
}

export function isSameDay(left: Date, right: Date): boolean {
  return left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate();
}

export function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

/** 一覧の表示で見せる日数（選んだ日から） */
export const LIST_VIEW_DAYS = 30;
export const THREE_DAY_VIEW_DAYS = 3;

export function toRangeStart(view: ScheduleView, anchor: Date): Date {
  if (view === "list") return new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate());
  if (view === "month") return new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  if (view === "day" || view === "threeDay") return new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate());
  return getWeekDays(anchor)[0];
}

export function toRangeEnd(view: ScheduleView, anchor: Date): Date {
  if (view === "list") return addDays(new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate()), LIST_VIEW_DAYS);
  if (view === "month") return addMonths(new Date(anchor.getFullYear(), anchor.getMonth(), 1), 1);
  if (view === "day") return addDays(new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate()), 1);
  if (view === "threeDay") return addDays(new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate()), THREE_DAY_VIEW_DAYS);
  return addDays(getWeekDays(anchor)[6], 1);
}

export interface PopoverSize {
  width: number;
  height: number;
}

export interface PopoverViewport {
  width: number;
  height: number;
}

/**
 * 小窓の置き場所を、出したあとに測った大きさから決める（純粋な関数）。
 * 高さの上限は CSS（.schedule-popover の max-height）が画面の高さ−2×margin に保つので、
 * ここは高さを返さず、左上の位置だけ返す。
 * 枠が無いとき（C キー・サイドバーの作成ボタン）は画面の真ん中。
 */
export function fitPopover(
  anchor: AnchorRect | null,
  size: PopoverSize,
  viewport: PopoverViewport,
  margin: number,
): { left: number; top: number } {
  const maxLeft = Math.max(margin, viewport.width - size.width - margin);
  const maxTop = Math.max(margin, viewport.height - size.height - margin);
  if (!anchor) {
    return {
      left: clamp((viewport.width - size.width) / 2, margin, maxLeft),
      top: clamp((viewport.height - size.height) / 2, margin, maxTop),
    };
  }
  const rightSide = anchor.right + margin;
  const leftSide = anchor.left - size.width - margin;
  const left = clamp(rightSide + size.width > viewport.width - margin ? leftSide : rightSide, margin, maxLeft);
  const top = clamp(anchor.top, margin, maxTop);
  return { left, top };
}

/** 下書きの日時の 5 項目（ScheduleDraft の一部・design §3.17 作り方 1） */
export interface DraftDates {
  startDate: string;
  startTime: string;
  endDate: string;
  endTime: string;
  allDay: boolean;
}

/** 作る小窓を仮の箱の横に置くときの、箱と小窓のあき(px)。--space-2 と同じ値（design §3.17 作り方 4） */
export const CREATE_POPOVER_GAP = 8;

/**
 * 下書きの日時 → 仮の箱の start・end・allDay（design §3.17 作り方 1・G47）。
 * 終日の end は endDate の次の日 0 時（FullCalendar の終日の end と同じ）。
 * 日時が読めない・end が start 以前のときは null（箱を出さない）。保存（saveEvent）と同じ combineDateTime を使う。
 */
export function draftToRange(draft: DraftDates): { start: Date; end: Date; allDay: boolean } | null {
  const start = combineDateTime(draft.startDate, draft.allDay ? "00:00" : draft.startTime);
  const end = draft.allDay
    ? addDays(combineDateTime(draft.endDate, "00:00"), 1)
    : combineDateTime(draft.endDate, draft.endTime);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end.getTime() <= start.getTime()) return null;
  return { start, end, allDay: draft.allDay };
}

/**
 * 箱の日時 → 下書きの日時（design §3.17 作り方 2）。openCreateRange と moveDraft の両方が使う。
 * 終日: endDate は end（無ければ start＋1 日）の 1 日前、時刻は 00:00／23:59。
 * 時刻つき: end が無ければ start＋1 時間（FullCalendar の既定と同じ）。
 */
export function rangeToDraftDates(start: Date, end: Date | null, allDay: boolean): DraftDates {
  if (allDay) {
    const endDay = end ?? addDays(start, 1);
    return {
      startDate: formatDateInput(start),
      startTime: "00:00",
      endDate: formatDateInput(addDays(endDay, -1)),
      endTime: "23:59",
      allDay: true,
    };
  }
  const timedEnd = end ?? new Date(start.getTime() + 60 * 60 * 1000);
  return {
    startDate: formatDateInput(start),
    startTime: formatTimeInput(start),
    endDate: formatDateInput(timedEnd),
    endTime: formatTimeInput(timedEnd),
    allDay: false,
  };
}

/**
 * 作る小窓で始まりの日付・時刻だけを直したとき、長さを保って終わりも同じだけずらす（design §3.17 作り方 1・Google と同じ）。
 * 今の下書きの長さが読めない（どちらかが読めない・0 以下）か、新しい始まりが読めないときは、始まりだけ入れ替える。
 */
export function shiftDraftStart<T extends DraftDates>(draft: T, nextStartDate: string, nextStartTime: string): T {
  const startOnly = { ...draft, startDate: nextStartDate, startTime: nextStartTime };
  if (draft.allDay) {
    const oldStart = combineDateTime(draft.startDate, "00:00");
    const oldEnd = combineDateTime(draft.endDate, "00:00");
    const nextStart = combineDateTime(nextStartDate, "00:00");
    if ([oldStart, oldEnd, nextStart].some((d) => Number.isNaN(d.getTime())) || oldEnd < oldStart) return startOnly;
    const days = Math.round((oldEnd.getTime() - oldStart.getTime()) / (24 * 60 * 60 * 1000));
    return { ...startOnly, endDate: formatDateInput(addDays(nextStart, days)) };
  }
  const oldStart = combineDateTime(draft.startDate, draft.startTime);
  const oldEnd = combineDateTime(draft.endDate, draft.endTime);
  const nextStart = combineDateTime(nextStartDate, nextStartTime);
  if ([oldStart, oldEnd, nextStart].some((d) => Number.isNaN(d.getTime())) || oldEnd <= oldStart) return startOnly;
  const nextEnd = new Date(nextStart.getTime() + (oldEnd.getTime() - oldStart.getTime()));
  return { ...startOnly, endDate: formatDateInput(nextEnd), endTime: formatTimeInput(nextEnd) };
}

/**
 * 作る小窓を仮の箱の横に置く（design §3.17 作り方 4・G43・Google の実測 R12-3）。
 * 横: 箱の右＋gap。入らなければ箱の左−小窓の幅−gap。
 * 縦: 「箱の上の端」と「画面の真ん中に置いた位置」の小さい方を、margin〜(画面の高さ−小窓の高さ−margin) に収める。
 * 箱が無いとき（C キー・作成ボタン）は fitPopover と同じ真ん中。
 */
export function fitCreatePopover(
  anchor: AnchorRect | null,
  size: PopoverSize,
  viewport: PopoverViewport,
  margin: number,
  gap: number,
): { left: number; top: number } {
  if (!anchor) return fitPopover(null, size, viewport, margin);
  const maxLeft = Math.max(margin, viewport.width - size.width - margin);
  const maxTop = Math.max(margin, viewport.height - size.height - margin);
  const rightSide = anchor.right + gap;
  const leftSide = anchor.left - size.width - gap;
  const left = clamp(rightSide + size.width > viewport.width - margin ? leftSide : rightSide, margin, maxLeft);
  const top = clamp(Math.min(anchor.top, (viewport.height - size.height) / 2), margin, maxTop);
  return { left, top };
}

export function normalizeEvent(event: ApiCalendarEvent): ScheduleItem {
  const start = parseLocalDate(event.start_datetime);
  const end = parseLocalDate(event.end_datetime);
  const category = (event.category ?? (event.calendar_type === "personal" ? "personal" : "meeting")) as ScheduleItem["category"];
  const ownerUserId = event.user_id ?? event.created_by_user_id ?? null;
  const ownerName = event.owner_name ?? event.created_by_name ?? null;
  const occurrenceStart = event.occurrence_start ? parseLocalDate(event.occurrence_start) : null;
  return {
    // 回は同じ元の行から何件も出るので、回の元の始まりで id を分ける（design §12.6.1）
    id: occurrenceStart ? `event-${event.id}-${occurrenceStart.getTime()}` : `event-${event.id}`,
    title: event.title,
    start,
    end,
    allDay: event.is_all_day,
    category,
    calendarType: event.calendar_type === "personal" ? "personal" : "shared",
    source: event.source === "google" ? "google" : "app",
    ownerUserId,
    ownerName,
    organizer: event.created_by_name ?? null,
    location: event.location ?? null,
    description: event.description ?? null,
    createdByName: event.created_by_name ?? null,
    meetUrl: event.meet_url ?? null,
    googleEventId: event.google_event_id ?? null,
    recurrence: toScheduleRecurrence(event.recurrence),
    recurringEventId: event.recurring_event_id ?? null,
    occurrenceStart,
    isFirstOccurrence: event.is_first_occurrence === true,
  };
}

export function normalizeShift(shift: ApiShift, t: (key: string) => string): ScheduleItem {
  const start = parseDateTime(shift.shift_date, shift.start_time);
  const end = parseDateTime(shift.shift_date, shift.end_time);
  return {
    id: `shift-${shift.id}`,
    title: shift.shift_type === "holiday" ? t("schedule.holiday") : t("schedule.shiftLabel"),
    start,
    end,
    allDay: false,
    category: "personal",
    calendarType: "personal",
    source: "shift",
    ownerUserId: shift.user_id,
    ownerName: null,
    description: shift.notes ?? null,
  };
}

export interface ApiHoliday {
  date: string; // YYYY-MM-DD
  name: string;
}

/** 祝日を金型の予定の形にする。終日・動かせない・tone holiday（design §3.6・§3.10） */
export function toHolidayEvents(holidays: ApiHoliday[] | undefined): CalendarViewEvent[] {
  if (!Array.isArray(holidays)) return [];
  return holidays.flatMap((holiday) => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(holiday.date);
    if (!match) return [];
    const start = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    return [{
      id: `holiday-${holiday.date}`,
      title: holiday.name,
      start: holiday.date,
      end: formatDateInput(addDays(start, 1)),
      allDay: true,
      tone: "holiday" as const,
      editable: false,
    }];
  });
}

/** "event-12" と回の "event-12-1762909200000" → 12。シフト・仮の箱など予定でない id は null */
export function eventNumericId(id: string): number | null {
  const m = /^event-(\d+)(?:-\d+)?$/.exec(id);
  return m ? Number(m[1]) : null;
}

/**
 * 動かした後の終わり（送る値）。
 * - 終日: FullCalendar の終わりは「次の日 0:00」なので 1 日戻し、その日の 23:59（design §3.3 の 3）
 * - 終わりが null: 元の長さを保つ（終日は同じ 1 日）
 * - 終日 → 時刻つきへ動かして終わりが null: 1 時間（元の 23 時間 59 分を引き継がない）
 */
export function toCalendarEnd(
  start: Date,
  end: Date | null,
  allDay: boolean,
  item: Pick<ScheduleItem, "start" | "end" | "allDay">,
): Date {
  if (allDay) {
    const last = end ? addDays(end, -1) : start;
    const lastDay = last.getTime() < start.getTime() ? start : last;
    return combineDateTime(formatDateInput(lastDay), "23:59");
  }
  if (end) return end;
  if (item.allDay) return new Date(start.getTime() + 60 * 60 * 1000);
  return new Date(start.getTime() + (item.end.getTime() - item.start.getTime()));
}

/** 繰り返しの選び方（backend/app/routers/calendar.py の RecurrenceValue と、表せない決まりの "custom"） */
export type ScheduleRecurrence =
  | "none" | "daily" | "weekly" | "monthly_nth" | "monthly_last" | "yearly" | "weekdays" | "custom";

const RECURRENCE_VALUES: readonly ScheduleRecurrence[] = [
  "none", "daily", "weekly", "monthly_nth", "monthly_last", "yearly", "weekdays", "custom",
];

export function toScheduleRecurrence(value: string | null | undefined): ScheduleRecurrence {
  return RECURRENCE_VALUES.includes(value as ScheduleRecurrence) ? (value as ScheduleRecurrence) : "none";
}

/** 開始日で選べる値（design §12.2 G70。サーバーの build_rule と同じ決まり） */
export function recurrenceChoicesFor(date: Date): ScheduleRecurrence[] {
  const choices: ScheduleRecurrence[] = ["none", "daily", "weekly"];
  if (date.getDate() <= 28) choices.push("monthly_nth");
  if (addDays(date, 7).getMonth() !== date.getMonth()) choices.push("monthly_last");
  choices.push("yearly", "weekdays");
  return choices;
}

/** 選ぶ欄に並べる値。すでに繰り返している予定の今の値（keep）は開始日で選べなくても残す（§12.6.1 G5） */
export function recurrenceOptionsFor(date: Date, keep: ScheduleRecurrence | null): ScheduleRecurrence[] {
  const choices = recurrenceChoicesFor(date);
  return RECURRENCE_VALUES.filter((v) => v !== "custom" && (choices.includes(v) || v === keep));
}

const ORDINAL_KEYS = [
  "schedule.recurrence.ordinal1",
  "schedule.recurrence.ordinal2",
  "schedule.recurrence.ordinal3",
  "schedule.recurrence.ordinal4",
] as const;

/** 選び方の文字（例「毎週 木曜日」）。日付が読めないときと custom は空 */
export function recurrenceLabel(value: ScheduleRecurrence, date: Date, t: Translate, language: string): string {
  if (Number.isNaN(date.getTime())) return "";
  const weekday = new Intl.DateTimeFormat(language, { weekday: "long" }).format(date);
  switch (value) {
    case "none":
      return t("schedule.recurrence.none");
    case "daily":
      return t("schedule.recurrence.daily");
    case "weekly":
      return t("schedule.recurrence.weekly", { weekday });
    case "monthly_nth":
      return t("schedule.recurrence.monthlyNth", {
        ordinal: t(ORDINAL_KEYS[Math.min(Math.ceil(date.getDate() / 7), 4) - 1]),
        weekday,
      });
    case "monthly_last":
      return t("schedule.recurrence.monthlyLast", { weekday });
    case "yearly":
      return t("schedule.recurrence.yearly", {
        date: new Intl.DateTimeFormat(language, { month: "long", day: "numeric" }).format(date),
      });
    case "weekdays":
      return t("schedule.recurrence.weekdays");
    default:
      return "";
  }
}

/** 新しい予定・単発の予定で開始日を変えたとき、使えなくなった「第 N」「最終」をもう一方へ入れ替える（§12.6.1 G5） */
export function fitRecurrenceToDate(value: ScheduleRecurrence, date: Date): ScheduleRecurrence {
  if (Number.isNaN(date.getTime())) return value;
  if (value !== "monthly_nth" && value !== "monthly_last") return value;
  if (recurrenceChoicesFor(date).includes(value)) return value;
  return value === "monthly_nth" ? "monthly_last" : "monthly_nth";
}

export type RecurrenceScope = "this" | "following" | "all";
export type ScopeKind = "save" | "delete" | "move";

/**
 * 3 択の小窓に出す値（design §12.2 G73・G75・G79、§12.6.1 G9）。
 * changesSeries は「選び方か社員への見せ方を変えた」（サーバーは「この予定」で 422 にする）。
 */
export function scopeChoices(kind: ScopeKind, isFirst: boolean, changesSeries: boolean): RecurrenceScope[] {
  if (kind === "move") return isFirst ? ["this", "all"] : ["this", "following"];
  if (kind === "save" && changesSeries) return isFirst ? ["all"] : ["following", "all"];
  return isFirst ? ["this", "all"] : ["this", "following", "all"];
}

/** 繰り返しの予定の回（または検索で返る元の行）か */
export function isRecurringItem(item: ScheduleItem): boolean {
  return item.recurringEventId != null || (item.recurrence != null && item.recurrence !== "none");
}

/** 送る回の始まり。回の元の始まりが無いとき（検索で返る元の行）は予定の始まり */
export function occurrenceStartOf(item: ScheduleItem): Date {
  return item.occurrenceStart ?? item.start;
}
