import { CALENDAR_MAP, type CalendarId } from "../../features/schedule/calendars.config";

export type ScheduleView = "week" | "day" | "month";
export type DemoState = "normal" | "loading" | "empty";

export interface ApiCalendarEvent {
  id: number;
  user_id: number;
  calendar_type: "shared" | "personal";
  category?: CalendarId | null;
  title: string;
  description: string | null;
  location: string | null;
  start_datetime: string;
  end_datetime: string;
  is_all_day: boolean;
  source: "app" | "google";
  sync_status: "synced" | "pending" | "failed";
  created_by_user_id: number;
  created_by_name?: string | null;
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
}

export interface ScheduleItem {
  id: string;
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  category: CalendarId | null;
  calendarType: "shared" | "personal";
  source: "app" | "google" | "shift";
  description: string | null;
  location: string | null;
  organizer: string | null;
  ownerName: string | null;
  ownerUserId: number | null;
  syncStatus?: "synced" | "pending" | "failed";
  rawEvent?: ApiCalendarEvent;
  rawShift?: ApiShift;
}

export interface AnchorRect {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

export interface DayLaneItem {
  item: ScheduleItem;
  left: number;
  width: number;
  top: number;
  height: number;
  lane: number;
  laneCount: number;
}

const CATEGORY_KEYWORDS: Array<[CalendarId, RegExp[]]> = [
  ["billing", [/\b請求\b/, /\b入金\b/, /請求/, /入金/, /billing/i, /invoice/i, /payment/i]],
  ["shipping", [/発送/, /集荷/, /出荷/, /shipping/i, /delivery/i, /pickup/i]],
  ["purchase", [/仕入/, /入荷/, /発注/, /purchase/i, /procure/i, /buy/i]],
  ["release", [/発売/, /リリース/, /新商品/, /release/i, /launch/i]],
  ["holiday", [/祝日/, /休日/, /holiday/i]],
  ["meeting", [/商談/, /打合せ/, /打ち合わせ/, /会議/, /meeting/i, /call/i, /sync/i]],
];

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

export function parseDate(value: string): Date {
  return new Date(value);
}

export function formatDayKey(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function formatDateInput(date: Date): string {
  return formatDayKey(date);
}

export function formatTimeInput(date: Date): string {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function formatMonthLabel(date: Date, locale = "ja-JP"): string {
  return new Intl.DateTimeFormat(locale, { year: "numeric", month: "long" }).format(date);
}

export function formatDayLabel(date: Date, locale = "ja-JP"): string {
  return new Intl.DateTimeFormat(locale, {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(date);
}

export function formatTimeRange(
  start: Date,
  end: Date,
  allDay = false,
  locale = "ja-JP",
  allDayLabel = "All day",
): string {
  if (allDay) return allDayLabel;
  const formatter = new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${formatter.format(start)}–${formatter.format(end)}`;
}

export function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export function endOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
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

export function startOfWeek(date: Date): Date {
  const start = startOfDay(date);
  start.setDate(start.getDate() - start.getDay());
  return start;
}

export function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

export function isSameDay(left: Date, right: Date): boolean {
  return left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate();
}

export function isBeforeDate(left: Date, right: Date): boolean {
  return left.getTime() < right.getTime();
}

export function getWeekDays(anchor: Date): Date[] {
  const first = startOfWeek(anchor);
  return Array.from({ length: 7 }, (_, index) => addDays(first, index));
}

export function getMonthCells(anchor: Date): Date[] {
  const firstOfMonth = startOfMonth(anchor);
  const start = startOfWeek(firstOfMonth);
  return Array.from({ length: 42 }, (_, index) => addDays(start, index));
}

export function toRangeStart(view: ScheduleView, anchor: Date): Date {
  if (view === "month") return startOfMonth(anchor);
  if (view === "day") return startOfDay(anchor);
  return startOfWeek(anchor);
}

export function toRangeEnd(view: ScheduleView, anchor: Date): Date {
  if (view === "month") return endOfDay(addDays(startOfMonth(addMonths(anchor, 1)), -1));
  if (view === "day") return endOfDay(anchor);
  return endOfDay(addDays(startOfWeek(anchor), 6));
}

export function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

export function minutesFromMidnight(date: Date): number {
  return date.getHours() * 60 + date.getMinutes();
}

export function parseDateTimeParts(date: Date): { date: string; time: string } {
  return {
    date: formatDateInput(date),
    time: formatTimeInput(date),
  };
}

export function combineDateTime(date: string, time: string): Date {
  return new Date(`${date}T${time}:00`);
}

export function deriveCategoryFromEvent(event: ApiCalendarEvent): CalendarId {
  if (event.calendar_type === "personal") return "personal";
  const haystack = `${event.title}\n${event.description ?? ""}\n${event.location ?? ""}`;
  for (const [category, patterns] of CATEGORY_KEYWORDS) {
    if (patterns.some((pattern) => pattern.test(haystack))) {
      return category;
    }
  }
  return "meeting";
}

export function deriveCategoryFromShift(shift: ApiShift): CalendarId {
  const haystack = `${shift.shift_type}\n${shift.notes ?? ""}`;
  if (/祝日|休日|holiday/i.test(haystack)) return "holiday";
  if (/発送|集荷|出荷|delivery|shipping/i.test(haystack)) return "shipping";
  if (/仕入|入荷|purchase|procure/i.test(haystack)) return "purchase";
  if (/請求|入金|billing|invoice|payment/i.test(haystack)) return "billing";
  if (/発売|リリース|新商品|release|launch/i.test(haystack)) return "release";
  return "meeting";
}

export function normalizeEvent(event: ApiCalendarEvent): ScheduleItem {
  const start = parseDate(event.start_datetime);
  const end = parseDate(event.end_datetime);
  return {
    id: String(event.id),
    title: event.title,
    start,
    end,
    allDay: event.is_all_day,
    category: event.category ?? deriveCategoryFromEvent(event),
    calendarType: event.calendar_type,
    source: event.source,
    description: event.description,
    location: event.location,
    organizer: event.created_by_name ?? null,
    ownerName: event.created_by_name ?? null,
    ownerUserId: event.user_id ?? null,
    syncStatus: event.sync_status,
    rawEvent: event,
  };
}

export function normalizeShift(shift: ApiShift): ScheduleItem {
  const start = new Date(`${shift.shift_date}T${shift.start_time}`);
  const end = new Date(`${shift.shift_date}T${shift.end_time}`);
  return {
    id: `shift-${shift.id}`,
    title: shift.shift_type,
    start,
    end,
    allDay: false,
    category: deriveCategoryFromShift(shift),
    calendarType: "shared",
    source: "shift",
    description: shift.notes,
    location: null,
    organizer: null,
    ownerName: null,
    ownerUserId: shift.user_id,
    rawShift: shift,
  };
}

export function layoutDay(items: ScheduleItem[], rowHeight: number): DayLaneItem[] {
  const entries = items
    .map((item) => ({
      item,
      start: minutesFromMidnight(item.start),
      end: Math.max(minutesFromMidnight(item.end), minutesFromMidnight(item.start) + 30),
    }))
    .sort((left, right) => left.start - right.start || right.end - left.end);

  const laidOut: DayLaneItem[] = [];
  let group: Array<{ item: ScheduleItem; start: number; end: number; lane: number }> = [];
  let groupEnd = -1;

  const flush = () => {
    if (group.length === 0) return;

    const laneEnds: number[] = [];
    for (const entry of group) {
      let lane = laneEnds.findIndex((end) => end <= entry.start);
      if (lane === -1) {
        lane = laneEnds.length;
        laneEnds.push(entry.end);
      } else {
        laneEnds[lane] = entry.end;
      }
      entry.lane = lane;
    }

    const laneCount = Math.max(laneEnds.length, 1);
    for (const entry of group) {
      const top = (entry.start / 60) * rowHeight;
      const height = Math.max(((entry.end - entry.start) / 60) * rowHeight, rowHeight * 0.5);
      laidOut.push({
        item: entry.item,
        left: (entry.lane / laneCount) * 100,
        width: 100 / laneCount,
        top,
        height,
        lane: entry.lane,
        laneCount,
      });
    }

    group = [];
    groupEnd = -1;
  };

  for (const entry of entries) {
    if (group.length > 0 && entry.start >= groupEnd) {
      flush();
    }
    groupEnd = group.length === 0 ? entry.end : Math.max(groupEnd, entry.end);
    group.push({ ...entry, lane: 0 });
  }

  flush();
  return laidOut;
}

export function getCategoryMeta(category: CalendarId | null) {
  return category ? CALENDAR_MAP[category] : null;
}
