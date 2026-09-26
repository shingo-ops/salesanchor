import { api } from "../lib/api";

export interface CloseReasonResponse {
  id: number;
  type: "won" | "lost";
  label: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export function getCloseReasons(type: "won" | "lost" = "lost") {
  const params = new URLSearchParams({ type });
  return api.get<CloseReasonResponse[]>(`/close-reasons?${params.toString()}`);
}
