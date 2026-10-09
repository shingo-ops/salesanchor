// react-i18next の t と、画面側の薄い t の両方を受ける最小の型
type TFunction = (key: string, options?: Record<string, unknown>) => string;

/** 要確認の理由コードの訳（唯一の置き場所: ja/en.json の reviewReason.<code>）。design.md §12 */
export type ReviewReasonSource = "gemini" | "system";
export type ReviewReasonDetail = {
  code: string;
  source: ReviewReasonSource | null;
  fix_stage: "extraction" | "analysis" | null;
};

// reviewReason 名前空間のうち、理由コードではない鍵
const RESERVED_KEYS = new Set(["unknown", "source", "separator"]);
// 出どころの並び順（Gemini が先）
const SOURCE_ORDER: ReviewReasonSource[] = ["gemini", "system"];

export function reviewReasonLabel(t: TFunction, code: string): string {
  const unknown = t("reviewReason.unknown", { code });
  if (RESERVED_KEYS.has(code)) return unknown;
  return t(`reviewReason.${code}`, { defaultValue: unknown });
}

/** カンマ区切りの理由（analysis_results.review_reasons 等）を訳して結ぶ。空なら null */
export function reviewReasonsText(t: TFunction, reasons: string | null | undefined): string | null {
  const codes = (reasons ?? "").split(",").map((code) => code.trim()).filter(Boolean);
  if (codes.length === 0) return null;
  return codes.map((code) => reviewReasonLabel(t, code)).join(t("reviewReason.separator"));
}

/** 理由ごとの出どころを重複なし・gemini→system の順に並べて訳す。分からなければ null */
export function reviewSourceLabel(t: TFunction, details: ReviewReasonDetail[] | undefined): string | null {
  const present = new Set((details ?? []).map((detail) => detail.source));
  const labels = SOURCE_ORDER.filter((source) => present.has(source)).map((source) => t(`reviewReason.source.${source}`));
  return labels.length > 0 ? labels.join(t("reviewReason.separator")) : null;
}
