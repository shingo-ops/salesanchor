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
