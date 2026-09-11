import type { TFunction } from "i18next";

export function importMessage(code: string, t: TFunction): string {
  const exact: Record<string, string> = {
    CSV_EMPTY: "csvEmpty", CSV_HEADER_MISMATCH: "headerError",
    JAPANESE_TITLE_REQUIRED: "titleRequired", RELEASE_DATE_FORMAT: "dateError",
    MARK_EMPTY: "markEmpty", NO_SEARCH_KEYWORD: "noKeywords",
    PRODUCT_IMPORT_NOT_CSV: "notCsv", PRODUCT_IMPORT_EMPTY_FILE: "csvEmpty",
    PRODUCT_IMPORT_FILE_TOO_LARGE: "tooLarge", PRODUCT_IMPORT_NOT_UTF8: "utf8",
    PRODUCT_IMPORT_DIGEST_MISMATCH: "changed", PRODUCT_IMPORT_ALREADY_IMPORTED: "duplicateFile",
  };
  if (exact[code]) return t(`productCsv.messages.${exact[code]}`);
  const prefixes: [string, string][] = [
    ["CSV_COLUMN_COUNT_MISMATCH_ROW_", "columnCount"],
    ["DUPLICATE_IN_FILE_ROW_", "duplicateRow"],
    ["MARK_ALREADY_USED_BY_", "markUsed"],
    ["SHORT_KEYWORD_", "shortKeyword"],
    ["KEYWORD_ALSO_HITS_", "keywordShared"],
    ["DUPLICATE_CANDIDATE_", "duplicateCandidate"],
  ];
  for (const [prefix, key] of prefixes) {
    if (code.startsWith(prefix)) return t(`productCsv.messages.${key}`, { value: code.slice(prefix.length) });
  }
  for (const field of ["DIVISION_CODE", "WORK_CODE", "MANUFACTURER_CODE", "PRODUCT_CATEGORY_CODE"]) {
    if (code === `MISSING_${field}` || code.startsWith(`UNKNOWN_${field}_`)) {
      return t("productCsv.messages.referenceCode", { field: t(`productCsv.fields.${field}`) });
    }
  }
  return t("productCsv.messages.unknown");
}
