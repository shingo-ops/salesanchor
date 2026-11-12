/* eslint-disable local/no-japanese-literal -- 試験用の状態の名前（DB の name_ja の見本） */
/** 試験用の customer_statuses の4行（GET /customer-statuses の偽の返事。値は docs/handoff/status-ssot-contact-company/insert-customer-statuses.sql と同じ形）。 */
import type { CustomerStatusRow } from "../lib/customerStatuses";

export const CUSTOMER_STATUS_TEST_ROWS: CustomerStatusRow[] = [
  { code: "active", name_ja: "有効", name_en: "Active", sort_order: 10, is_active: true, selectable_on_create: true },
  { code: "inactive", name_ja: "無効", name_en: "Inactive", sort_order: 20, is_active: true, selectable_on_create: true },
  { code: "archived", name_ja: "アーカイブ", name_en: "Archived", sort_order: 30, is_active: true, selectable_on_create: true },
  { code: "pending_dedup_review", name_ja: "重複確認待ち", name_en: "Pending duplicate check", sort_order: 40, is_active: true, selectable_on_create: false },
];
