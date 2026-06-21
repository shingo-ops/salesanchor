// ============================================================
// Sales Anchor — Schedule calendar definitions
//
// `design_handoff_schedule_gcal` の category 正本。
// PR2/PR3 では UI のフィルタ・設定・業務連動の全てがここを参照する。
// ============================================================

export type CalendarId =
  | "personal"
  | "meeting"
  | "purchase"
  | "shipping"
  | "billing"
  | "release"
  | "holiday";

export interface CalendarDef {
  id: CalendarId;
  labelKey: string;
  label: string;
  colorVar: string;
  tintVar: string;
  textVar: string;
  primary: boolean;
}

export const CALENDARS: readonly CalendarDef[] = [
  { id: "personal", labelKey: "schedule.personal", label: "Personal", colorVar: "--cal-personal", tintVar: "--cal-personal-tint", textVar: "--cal-personal-text", primary: true },
  { id: "meeting", labelKey: "schedule.meeting", label: "Meeting", colorVar: "--cal-meeting", tintVar: "--cal-meeting-tint", textVar: "--cal-meeting-text", primary: true },
  { id: "purchase", labelKey: "schedule.purchase", label: "Purchase", colorVar: "--cal-purchase", tintVar: "--cal-purchase-tint", textVar: "--cal-purchase-text", primary: true },
  { id: "shipping", labelKey: "schedule.shipping", label: "Shipping", colorVar: "--cal-shipping", tintVar: "--cal-shipping-tint", textVar: "--cal-shipping-text", primary: true },
  { id: "billing", labelKey: "schedule.billing", label: "Billing", colorVar: "--cal-billing", tintVar: "--cal-billing-tint", textVar: "--cal-billing-text", primary: true },
  { id: "release", labelKey: "schedule.release", label: "Release", colorVar: "--cal-release", tintVar: "--cal-release-tint", textVar: "--cal-release-text", primary: true },
  { id: "holiday", labelKey: "schedule.holiday", label: "Holiday", colorVar: "--cal-holiday", tintVar: "--cal-holiday-tint", textVar: "--cal-holiday-text", primary: false },
] as const;

export const CALENDAR_MAP: Record<CalendarId, CalendarDef> =
  Object.fromEntries(CALENDARS.map((calendar) => [calendar.id, calendar])) as Record<CalendarId, CalendarDef>;

export const cssVar = (name: string) => `var(${name})`;
