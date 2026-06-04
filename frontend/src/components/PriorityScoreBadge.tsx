/**
 * ADR-107 (ADR-SA-14): 顧客優先度スコアバッジ（読み取り専用）。
 *
 * 表示規則:
 *   - is_cold_start=true → 「暫定」バッジ（データ不足を明示）
 *   - score=null → 「未評価」バッジ
 *   - 通常 → 要観察 / 有望 / 最有望 の3段階バッジ
 *
 * 信頼保護: スコアは社内専用・顧客には表示しない。
 * このコンポーネントは UI の読み取り表示のみ（派生値を手入力させない）。
 */

import { useTranslation } from "react-i18next";

export interface CustomerScoreData {
  tier: "要観察" | "有望" | "最有望";
  score: number;
  confidence: number;
  is_cold_start: boolean;
  sample_size: number;
  signal_summary: {
    total_messages: number;
    price_focus_count: number;
    substance_talk_count: number;
    self_disclosure_count: number;
    early_purchase_signal_count: number;
  };
}

interface Props {
  score: CustomerScoreData | null | undefined;
}

const TIER_CLASS: Record<string, string> = {
  "要観察": "priority-watching",
  "有望": "priority-promising",
  "最有望": "priority-top",
};

export default function PriorityScoreBadge({ score }: Props) {
  const { t } = useTranslation();

  if (!score) {
    return (
      <span className="badge priority-none" title={t("priority.noDataTooltip")}>
        {t("priority.noData")}
      </span>
    );
  }

  if (score.is_cold_start) {
    return (
      <span
        className="badge priority-provisional"
        title={t("priority.coldStartTooltip")}
      >
        {t("priority.provisional")}
      </span>
    );
  }

  const scorePercent = Math.round(score.score * 100);
  const confPercent = Math.round(score.confidence * 100);
  const tooltip = t("priority.tooltipFormat", {
    score: scorePercent,
    confidence: confPercent,
    sample: score.sample_size,
  });

  return (
    <span
      className={`badge ${TIER_CLASS[score.tier] ?? ""}`}
      title={tooltip}
    >
      {t(`priority.tier.${score.tier}`)}
    </span>
  );
}
