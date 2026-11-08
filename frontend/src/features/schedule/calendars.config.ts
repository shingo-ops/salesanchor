import type { BadgeVariant } from "../../components/Badge";

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
  badgeVariant: BadgeVariant;
  primary: boolean;
}

export const CALENDARS: CalendarMeta[] = [
  {
    id: "meeting",
    labelKey: "schedule.calendarLabels.meeting",
    badgeVariant: "info",
    primary: true,
  },
  {
    id: "personal",
    labelKey: "schedule.calendarLabels.personal",
    badgeVariant: "purple",
    primary: true,
  },
  {
    id: "procurement",
    labelKey: "schedule.calendarLabels.procurement",
    badgeVariant: "success",
    primary: true,
  },
  {
    id: "shipping",
    labelKey: "schedule.calendarLabels.shipping",
    badgeVariant: "danger",
    primary: true,
  },
  {
    id: "billing",
    labelKey: "schedule.calendarLabels.billing",
    badgeVariant: "warning",
    primary: true,
  },
  {
    id: "release",
    labelKey: "schedule.calendarLabels.release",
    badgeVariant: "neutral",
    primary: true,
  },
  {
    id: "holiday",
    labelKey: "schedule.calendarLabels.holiday",
    badgeVariant: "purple",
    primary: false,
  },
];

export const CALENDAR_MAP = Object.fromEntries(
  CALENDARS.map((calendar) => [calendar.id, calendar]),
) as Record<CalendarId, CalendarMeta>;
