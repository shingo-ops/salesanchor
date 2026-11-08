export type CalendarShareMode = "self" | "view" | "edit";

export interface ApiCalendarOwner {
  staff_id: number;
  user_id: number | null;
  staff_code: string;
  name: string;
  primary_email: string | null;
  color: string;
  is_visible: boolean;
  share_mode: CalendarShareMode | string;
  is_self: boolean;
}

export interface ApiCalendarOwnersResponse {
  can_manage_others: boolean;
  current_staff_id: number | null;
  current_user_id: number;
  owners: ApiCalendarOwner[];
}

export interface CalendarOwner {
  staffId: number;
  userId: number | null;
  staffCode: string;
  name: string;
  primaryEmail: string | null;
  color: string;
  visible: boolean;
  shareMode: CalendarShareMode;
  isSelf: boolean;
}

/** 持ち主が見つからない時に画面に描く色。持ち主の色の正本はサーバー（backend/app/routers/calendar.py の _DEFAULT_OWNER_COLOR） */
export const DEFAULT_OWNER_COLOR = "var(--calendar-google-blue)";

export function normalizeOwner(owner: ApiCalendarOwner): CalendarOwner {
  return {
    staffId: owner.staff_id,
    userId: owner.user_id,
    staffCode: owner.staff_code,
    name: owner.name,
    primaryEmail: owner.primary_email,
    color: owner.color,
    visible: Boolean(owner.is_visible),
    shareMode: owner.share_mode === "view" || owner.share_mode === "edit" ? owner.share_mode : "self",
    isSelf: owner.is_self,
  };
}

