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
    colorVar: "var(--calendar-meeting-color)",
    tintVar: "var(--calendar-meeting-tint)",
    textVar: "var(--calendar-meeting-text)",
    primary: true,
  },
  {
    id: "personal",
    labelKey: "schedule.calendarLabels.personal",
    colorVar: "var(--calendar-personal-color)",
    tintVar: "var(--calendar-personal-tint)",
    textVar: "var(--calendar-personal-text)",
    primary: true,
  },
  {
    id: "procurement",
    labelKey: "schedule.calendarLabels.procurement",
    colorVar: "var(--calendar-procurement-color)",
    tintVar: "var(--calendar-procurement-tint)",
    textVar: "var(--calendar-procurement-text)",
    primary: true,
  },
  {
    id: "shipping",
    labelKey: "schedule.calendarLabels.shipping",
    colorVar: "var(--calendar-shipping-color)",
    tintVar: "var(--calendar-shipping-tint)",
    textVar: "var(--calendar-shipping-text)",
    primary: true,
  },
  {
    id: "billing",
    labelKey: "schedule.calendarLabels.billing",
    colorVar: "var(--calendar-billing-color)",
    tintVar: "var(--calendar-billing-tint)",
    textVar: "var(--calendar-billing-text)",
    primary: true,
  },
  {
    id: "release",
    labelKey: "schedule.calendarLabels.release",
    colorVar: "var(--calendar-release-color)",
    tintVar: "var(--calendar-release-tint)",
    textVar: "var(--calendar-release-text)",
    primary: true,
  },
  {
    id: "holiday",
    labelKey: "schedule.calendarLabels.holiday",
    colorVar: "var(--calendar-holiday-color)",
    tintVar: "var(--calendar-holiday-tint)",
    textVar: "var(--calendar-holiday-text)",
    primary: false,
  },
];

export const CALENDAR_MAP = Object.fromEntries(
  CALENDARS.map((calendar) => [calendar.id, calendar]),
) as Record<CalendarId, CalendarMeta>;
