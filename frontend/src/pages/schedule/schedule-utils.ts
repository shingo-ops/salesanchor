export type ScheduleView = "day" | "week" | "month";
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
  created_by_name: string | null;
  category?: string | null;
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
  organizer?: string | null;
  location?: string | null;
  description?: string | null;
  createdByName?: string | null;
}

export interface DayLayoutItem {
  item: ScheduleItem;
  top: number;
  left: number;
  width: number;
  height: number;
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

export function formatTimeRange(start: Date, end: Date, allDay: boolean, locale = "ja-JP", allDayLabel = "all day"): string {
  if (allDay) return allDayLabel;
  const fmt = new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${fmt.format(start)} - ${fmt.format(end)}`;
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

export function toRangeStart(view: ScheduleView, anchor: Date): Date {
  if (view === "month") return new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  if (view === "day") return new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate());
  return getWeekDays(anchor)[0];
}

export function toRangeEnd(view: ScheduleView, anchor: Date): Date {
  if (view === "month") return addMonths(new Date(anchor.getFullYear(), anchor.getMonth(), 1), 1);
  if (view === "day") return addDays(new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate()), 1);
  return addDays(getWeekDays(anchor)[6], 1);
}

export function normalizeEvent(event: ApiCalendarEvent): ScheduleItem {
  const start = parseLocalDate(event.start_datetime);
  const end = parseLocalDate(event.end_datetime);
  const category = (event.category ?? (event.calendar_type === "personal" ? "personal" : "meeting")) as ScheduleItem["category"];
  return {
    id: `event-${event.id}`,
    title: event.title,
    start,
    end,
    allDay: event.is_all_day,
    category,
    calendarType: event.calendar_type === "personal" ? "personal" : "shared",
    source: event.source === "google" ? "google" : "app",
    organizer: event.created_by_name ?? null,
    location: event.location ?? null,
    description: event.description ?? null,
    createdByName: event.created_by_name ?? null,
  };
}

export function normalizeShift(shift: ApiShift): ScheduleItem {
  const start = parseDateTime(shift.shift_date, shift.start_time);
  const end = parseDateTime(shift.shift_date, shift.end_time);
  return {
    id: `shift-${shift.id}`,
    title: shift.shift_type === "holiday" ? "Holiday" : "Shift",
    start,
    end,
    allDay: false,
    category: "personal",
    calendarType: "personal",
    source: "shift",
    description: shift.notes ?? null,
  };
}

type LayoutCandidate = {
  item: ScheduleItem;
  startOffset: number;
  endOffset: number;
};

export function layoutDay(items: ScheduleItem[], rowHeight: number): DayLayoutItem[] {
  const candidates: LayoutCandidate[] = items
    .slice()
    .sort((left, right) => left.start.getTime() - right.start.getTime())
    .map((item) => ({
      item,
      startOffset: item.start.getHours() * rowHeight + (item.start.getMinutes() / 60) * rowHeight,
      endOffset: item.end.getHours() * rowHeight + (item.end.getMinutes() / 60) * rowHeight,
    }));

  const lanes: LayoutCandidate[][] = [];
  for (const candidate of candidates) {
    let laneIndex = lanes.findIndex((existingLane) => existingLane.every((other) => candidate.endOffset <= other.startOffset || candidate.startOffset >= other.endOffset));
    if (laneIndex < 0) {
      laneIndex = lanes.length;
      lanes.push([]);
    }
    lanes[laneIndex].push(candidate);
  }

  const laneCount = Math.max(1, lanes.length);
  return lanes.flatMap((lane, laneIndex) => lane.map((candidate) => ({
    item: candidate.item,
    top: candidate.startOffset,
    left: (laneIndex / laneCount) * 100,
    width: 100 / laneCount,
    height: Math.max(candidate.endOffset - candidate.startOffset, rowHeight * 0.5),
  })));
}
