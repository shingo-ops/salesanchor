import { ApiError } from "../../../lib/api";

/** API エラー → i18n キー（401/403 は SaaS 管理者のみの案内、それ以外は取得失敗）。 */
export function errorKeyOf(error: unknown): string {
  return error instanceof ApiError && (error.status === 401 || error.status === 403)
    ? "superAdmin.supplierQuality.superAdminOnly"
    : "common.fetchError";
}
