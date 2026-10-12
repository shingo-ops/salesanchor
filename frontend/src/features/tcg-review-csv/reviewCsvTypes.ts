import type { TFunction } from "i18next";

export interface ReviewCsvApply { line: number; extraction_item_id: string; kind: "product" | "ack"; product_code: string; name: string }
export interface ReviewCsvError { line: number; extraction_item_id: string; code: string; detail: string }
export interface ReviewCsvPreview { total_rows: number; applies: ReviewCsvApply[]; errors: ReviewCsvError[]; digest: string }
export interface ReviewCsvResult { saved: number; failed: ReviewCsvError[]; reanalyze_jobs: number; errors: ReviewCsvError[] }

export const MAX_CSV_BYTES = 2 * 1024 * 1024;

const KNOWN_CODES = new Set([
  "REVIEW_CSV_NOT_CSV", "REVIEW_CSV_EMPTY_FILE", "REVIEW_CSV_HEADER_MISMATCH", "REVIEW_CSV_DIGEST_MISMATCH",
  "PRODUCT_IMPORT_FILE_TOO_LARGE", "ROUNDTRIP_CSV_INVALID",
  "REVIEW_CSV_ROW_SHAPE", "REVIEW_CSV_NOT_NEEDS_REVIEW", "REVIEW_CSV_STALE_REVISION", "REVIEW_CSV_BOTH_INPUTS",
  "REVIEW_CSV_BAD_ACK_MARK", "REVIEW_CSV_NOT_V102", "REVIEW_CSV_PRODUCT_CODE_NOT_FOUND",
  "REVIEW_CSV_PRODUCT_CODE_AMBIGUOUS", "REVIEW_CSV_NO_ACKABLE_REASON", "REVIEW_CSV_REJECTED",
  "REVIEW_CSV_DUPLICATE_ITEM", "REVIEW_CSV_SAVE_FAILED",
]);

/** サーバーのエラーコードを画面の文言にする。知らないコードは汎用の文言。 */
export function reviewCsvMessage(code: string, t: TFunction): string {
  return KNOWN_CODES.has(code) ? t(`reviewCsv.errors.${code}`) : t("reviewCsv.errors.unknown");
}
