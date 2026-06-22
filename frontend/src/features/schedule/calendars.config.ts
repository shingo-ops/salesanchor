export type CalendarId =
  | "meeting"
  | "personal"
  | "procurement"
  | "shipping"
  | "billing"
  | "release"
  | "holiday";

export interface CalendarMeta {
  id: CalendarId;
  labelKey: string;
  colorVar: string;
  tintVar: string;
  textVar: string;
  primary: boolean;
}

export const CALENDARS: CalendarMeta[] = [
  {
    id: "meeting",
    labelKey: "schedule.calendarLabels.meeting",
    colorVar: "#1a73e8",
    tintVar: "#e8f0fe",
    textVar: "#174ea6",
    primary: true,
  },
  {
    id: "personal",
    labelKey: "schedule.calendarLabels.personal",
    colorVar: "#9333ea",
    tintVar: "#f3e8ff",
    textVar: "#6b21a8",
    primary: true,
  },
  {
    id: "procurement",
    labelKey: "schedule.calendarLabels.procurement",
    colorVar: "#0f9d58",
    tintVar: "#e6f4ea",
    textVar: "#166534",
    primary: true,
  },
  {
    id: "shipping",
    labelKey: "schedule.calendarLabels.shipping",
    colorVar: "#d93025",
    tintVar: "#fce8e6",
    textVar: "#b91c1c",
    primary: true,
  },
  {
    id: "billing",
    labelKey: "schedule.calendarLabels.billing",
    colorVar: "#f29900",
    tintVar: "#fef3c7",
    textVar: "#92400e",
    primary: true,
  },
  {
    id: "release",
    labelKey: "schedule.calendarLabels.release",
    colorVar: "#5f6368",
    tintVar: "#f3f4f6",
    textVar: "#374151",
    primary: true,
  },
  {
    id: "holiday",
    labelKey: "schedule.calendarLabels.holiday",
    colorVar: "#7e22ce",
    tintVar: "#f5f3ff",
    textVar: "#6b21a8",
    primary: false,
  },
];

export const CALENDAR_MAP = Object.fromEntries(
  CALENDARS.map((calendar) => [calendar.id, calendar]),
) as Record<CalendarId, CalendarMeta>;

export function cssVar(value: string | null | undefined): string {
  return value ?? "";
}
