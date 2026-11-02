import { api } from "../lib/api";

export interface CloseReasonResponse {
  id: number;
  type: "won" | "lost";
  label: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

/** 失注・成約の理由の一覧の path（画面の写しの名前もここで決まる・ADR-1054） */
export function closeReasonsPath(type: "won" | "lost" = "lost") {
  return `/close-reasons?${new URLSearchParams({ type }).toString()}`;
}

export function getCloseReasons(type: "won" | "lost" = "lost") {
  return api.get<CloseReasonResponse[]>(closeReasonsPath(type));
}
