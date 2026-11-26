/**
 * ADR-109: Lead status immutable codes (SSOT).
 *
 * All status comparisons, filters, and display labels MUST go through these
 * constants and the `leads.statusCode.*` i18n keys. Never hardcode Japanese
 * status strings.
 */

export const LEAD_STATUS_CODES = [
  "lead",
  "negotiating",
  "existing_customer",
  "follow_up_short",
  "follow_up_long",
  "lost",
  "out_of_scope",
] as const;

export type LeadStatusCode = (typeof LEAD_STATUS_CODES)[number];

/**
 * ADR-1090: 手で選べる段階。「既存顧客」は登録・会社・支払いの 3 つがそろうと自動で付くので、手では選べない。
 */
export const MANUAL_LEAD_STATUS_CODES: LeadStatusCode[] = LEAD_STATUS_CODES.filter(
  (c) => c !== "existing_customer",
);
