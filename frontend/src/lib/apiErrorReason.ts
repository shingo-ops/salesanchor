import i18n from "../i18n";

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
  merge_target_archived: "apiError.mergeTargetArchived",
  bill_to_country: "apiError.billToCountry",
  recurrence_meet_not_allowed: "apiError.recurrenceMeetNotAllowed",
  recurrence_not_available: "apiError.recurrenceNotAvailable",
  recurrence_after_until: "apiError.recurrenceAfterUntil",
  recurrence_scope_not_allowed: "apiError.recurrenceScopeNotAllowed",
  recurrence_google_source: "apiError.recurrenceGoogleSource",
  recurrence_scope_required: "apiError.recurrenceScopeRequired",
  recurrence_occurrence_invalid: "apiError.recurrenceOccurrenceInvalid",
  recurrence_this_not_allowed: "apiError.recurrenceThisNotAllowed",
};

/** detail が表のコードなら文言キー、そうでなければ null */
export function apiErrorReasonKey(detail: unknown): string | null {
  if (typeof detail !== "string") return null;
  return Object.prototype.hasOwnProperty.call(API_ERROR_REASON_KEYS, detail)
    ? API_ERROR_REASON_KEYS[detail]
    : null;
}

/** サーバーの「見つからない」の detail の頭（ADR-1071 便3）。後ろに対象のコードが付く（例 not_found:lead） */
export const NOT_FOUND_PREFIX = "not_found:";

/**
 * 「見つからない」の対象 → 名前の文言キーの対応表（ADR-1071 便3・design §12-5）。
 * 新しい対象を足すときは、この表に 1 行と、ja.json・en.json の apiError.notFoundTarget に名前を足す。
 * 突き合わせの試験は API_ERROR_REASON_KEYS と同じ 2 つ。
 */
export const NOT_FOUND_TARGET_KEYS: Readonly<Record<string, string>> = {
  lead: "apiError.notFoundTarget.lead",
  order: "apiError.notFoundTarget.order",
  company: "apiError.notFoundTarget.company",
  condition: "apiError.notFoundTarget.condition",
  product: "apiError.notFoundTarget.product",
  contact: "apiError.notFoundTarget.contact",
  alias: "apiError.notFoundTarget.alias",
  invoice: "apiError.notFoundTarget.invoice",
  supplier_master: "apiError.notFoundTarget.supplier_master",
  team: "apiError.notFoundTarget.team",
  bot: "apiError.notFoundTarget.bot",
  my_staff_profile: "apiError.notFoundTarget.my_staff_profile",
  calendar_event: "apiError.notFoundTarget.calendar_event",
  quote: "apiError.notFoundTarget.quote",
  order_purchase: "apiError.notFoundTarget.order_purchase",
  payment_fee_setting: "apiError.notFoundTarget.payment_fee_setting",
  product_category: "apiError.notFoundTarget.product_category",
  supplier: "apiError.notFoundTarget.supplier",
  role: "apiError.notFoundTarget.role",
  status: "apiError.notFoundTarget.status",
  unit: "apiError.notFoundTarget.unit",
  order_financial: "apiError.notFoundTarget.order_financial",
  order_shipping: "apiError.notFoundTarget.order_shipping",
  staff: "apiError.notFoundTarget.staff",
  condition_definition: "apiError.notFoundTarget.condition_definition",
  product_format: "apiError.notFoundTarget.product_format",
  quantity_unit: "apiError.notFoundTarget.quantity_unit",
  distribution_target: "apiError.notFoundTarget.distribution_target",
  line_import_job: "apiError.notFoundTarget.line_import_job",
  calendar_owner: "apiError.notFoundTarget.calendar_owner",
  channel_master: "apiError.notFoundTarget.channel_master",
  goal: "apiError.notFoundTarget.goal",
  inventory_offer: "apiError.notFoundTarget.inventory_offer",
  message: "apiError.notFoundTarget.message",
  notice: "apiError.notFoundTarget.notice",
  notification_channel: "apiError.notFoundTarget.notification_channel",
  own_inventory: "apiError.notFoundTarget.own_inventory",
  product_master: "apiError.notFoundTarget.product_master",
  dex_entry: "apiError.notFoundTarget.dex_entry",
  knowledge_rule: "apiError.notFoundTarget.knowledge_rule",
  note_master: "apiError.notFoundTarget.note_master",
  product_kind: "apiError.notFoundTarget.product_kind",
  product_line: "apiError.notFoundTarget.product_line",
  tcg_series: "apiError.notFoundTarget.tcg_series",
  tcg_type: "apiError.notFoundTarget.tcg_type",
  tenant: "apiError.notFoundTarget.tenant",
  weight_class: "apiError.notFoundTarget.weight_class",
  archive_target: "apiError.notFoundTarget.archive_target",
  archive: "apiError.notFoundTarget.archive",
  badge: "apiError.notFoundTarget.badge",
  close_reason: "apiError.notFoundTarget.close_reason",
  deal: "apiError.notFoundTarget.deal",
  message_label: "apiError.notFoundTarget.message_label",
  meta_page: "apiError.notFoundTarget.meta_page",
  role_commission: "apiError.notFoundTarget.role_commission",
  purchase_order: "apiError.notFoundTarget.purchase_order",
  order_item: "apiError.notFoundTarget.order_item",
  user: "apiError.notFoundTarget.user",
  shift: "apiError.notFoundTarget.shift",
  shipping_zone: "apiError.notFoundTarget.shipping_zone",
  shipping_rate: "apiError.notFoundTarget.shipping_rate",
  staff_join_invite: "apiError.notFoundTarget.staff_join_invite",
  staff_report: "apiError.notFoundTarget.staff_report",
  discord_routing: "apiError.notFoundTarget.discord_routing",
  knowledge_link: "apiError.notFoundTarget.knowledge_link",
  team_member: "apiError.notFoundTarget.team_member",
};

/**
 * detail が `not_found:<対象>` なら画面の言語の文、そうでなければ null。
 * 表に無い対象は名前なしの文（apiError.notFoundUnknown）。コードの生の値は画面に出さない。
 * detail をそのまま i18n.t に渡さない（":" は i18next の名前空間の区切りのため）。
 */
export function notFoundMessage(detail: unknown): string | null {
  if (typeof detail !== "string" || !detail.startsWith(NOT_FOUND_PREFIX)) return null;
  const target = detail.slice(NOT_FOUND_PREFIX.length);
  if (!Object.prototype.hasOwnProperty.call(NOT_FOUND_TARGET_KEYS, target)) {
    return i18n.t("apiError.notFoundUnknown");
  }
  return i18n.t("apiError.notFound", { target: i18n.t(NOT_FOUND_TARGET_KEYS[target]) });
}

/** 共通の理由コード（便2）か「見つからない」（便3）なら画面の言語の文、どちらでもなければ null */
export function apiErrorReasonMessage(detail: unknown): string | null {
  const key = apiErrorReasonKey(detail);
  if (key) return i18n.t(key);
  return notFoundMessage(detail);
}
