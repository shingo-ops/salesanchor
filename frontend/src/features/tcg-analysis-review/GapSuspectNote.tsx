/**
 * 「Gemini取りこぼし疑い」の件に、間の行番号と商品の候補を出す（段2a PR-B）。
 * 値の出どころは backend の gap_suspect（extraction_jobs.system_review_detail）。商品は自動で当てず、人が見て決める。
 * 部品は Stack だけ。文字列はすべて t()。
 */
import { useTranslation } from "react-i18next";
import { Stack } from "../../components/Stack";
import type { ReviewReasonDetail } from "./reviewReasonLabel";

export const GAP_SUSPECT_CODE = "gemini_gap_suspect";

export type GapSuspectData = {
  gap_lines: number[];
  candidates: { product_id: string; name: string }[];
};

/** 理由に gemini_gap_suspect があり、gap_suspect の値があるときだけ値を返す（それ以外は null） */
export function gapSuspectOf(item: {
  review_reason_details?: ReviewReasonDetail[];
  gap_suspect?: GapSuspectData | null;
}): GapSuspectData | null {
  const hasReason = (item.review_reason_details ?? []).some((detail) => detail.code === GAP_SUSPECT_CODE);
  return hasReason && item.gap_suspect ? item.gap_suspect : null;
}

export function GapSuspectNote({ gapLines, candidates }: { gapLines: number[]; candidates: GapSuspectData["candidates"] }) {
  const { t } = useTranslation();
  const separator = t("reviewReason.separator");
  const lines = gapLines.map((n) => t("reviewItem.gapLineNumber", { n })).join(separator);
  const names = candidates.map((candidate) => candidate.name || candidate.product_id).join(separator);
  return (
    <Stack gap="1">
      {gapLines.length > 0 && <span>{t("reviewItem.gapLines", { lines })}</span>}
      {candidates.length > 0 && <span>{t("reviewItem.gapCandidates", { names })}</span>}
    </Stack>
  );
}
