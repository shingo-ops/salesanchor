import { eventColorVar, isEventColorKey, type EventColorKey } from "./eventColors";

export interface ApiCalendarOwner {
  staff_id: number;
  user_id: number | null;
  staff_code: string;
  name: string;
  primary_email: string | null;
  color_key: string | null;
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
  /** 選んだ 24 色の鍵。標準の色なら null */
  colorKey: EventColorKey | null;
  /** 画面に描く色 */
  color: string;
  isSelf: boolean;
}

/** 色を決めていない（標準の色の）人や、持ち主が見つからない時に画面に描く色。標準の色の置き場はこの 1 か所だけ */
export const DEFAULT_OWNER_COLOR = "var(--calendar-google-blue)";

export function normalizeOwner(owner: ApiCalendarOwner): CalendarOwner {
  const colorKey = isEventColorKey(owner.color_key) ? owner.color_key : null;
  return {
    staffId: owner.staff_id,
    userId: owner.user_id,
    staffCode: owner.staff_code,
    name: owner.name,
    primaryEmail: owner.primary_email,
    colorKey,
    color: colorKey ? eventColorVar(colorKey) : DEFAULT_OWNER_COLOR,
    isSelf: owner.is_self,
  };
}
