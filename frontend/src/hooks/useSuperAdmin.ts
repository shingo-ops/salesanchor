/**
 * 現在のユーザーが is_super_admin かどうかを判定するフック。
 *
 * spec.md v1.1 F2 (Sprint 2):
 *   /api/v1/me/permissions レスポンスに is_super_admin を含めて返す。
 *   そのレスポンスを再利用して /super-admin/masters への導線判定に使用。
 *
 * 変更履歴:
 *   2026-05-21: 初版（Sprint 2）
 *   2026-11-01: 写しの置き場（useApiQuery）に載せた（ADR-1054）。usePermissions と同じ写しを読む。戻った時は前の判定を先に出し、裏で取り直す。
 */
import { useApiQuery } from "../lib/query/apiQuery";

interface MePermissionsResponse {
  permissions: string[];
  is_super_admin: boolean;
}

export function useSuperAdmin() {
  const { data, isPending } = useApiQuery<MePermissionsResponse>("/me/permissions");

  // 取得に失敗した時は data が無いので false（運営者ではない扱い・今と同じ）
  return { isSuperAdmin: Boolean(data?.is_super_admin), loading: isPending };
}
