/**
 * サーバーが失敗の応答の detail に文字列で返す、画面に共通の理由コード → 文言キーの対応表（ADR-1071 便2）。
 *
 * frontend/src/lib/api.ts が、detail がこの表のコードのときだけ i18n の文を ApiError.message にする。
 * 表に無いコードは今までどおり detail をそのまま message にする（コードを比べている画面を壊さないため）。
 * 新しいコードを足すときは、この表に 1 行と、ja.json・en.json の apiError に文を足す。
 * 突き合わせの試験: apiErrorReason.test.ts（画面側）・backend/tests/test_api_error_reason_sync.py（サーバー側）。
 */
export const API_ERROR_REASON_KEYS: Readonly<Record<string, string>> = {
  no_fields_to_update: "apiError.noFieldsToUpdate",
  conflict_constraint: "apiError.conflictConstraint",
  role_not_editable_here: "apiError.roleNotEditableHere",
  role_not_deletable: "apiError.roleNotDeletable",
  role_permissions_edit_forbidden: "apiError.rolePermissionsEditForbidden",
  role_permissions_not_editable_here: "apiError.rolePermissionsNotEditableHere",
  role_page_keys_not_savable: "apiError.rolePageKeysNotSavable",
  role_not_assignable: "apiError.roleNotAssignable",
};

/** detail が表のコードなら文言キー、そうでなければ null */
export function apiErrorReasonKey(detail: unknown): string | null {
  if (typeof detail !== "string") return null;
  return Object.prototype.hasOwnProperty.call(API_ERROR_REASON_KEYS, detail)
    ? API_ERROR_REASON_KEYS[detail]
    : null;
}
