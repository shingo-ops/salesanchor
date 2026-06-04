/**
 * ADR-107 (ADR-SA-14): PriorityScoreBadge コンポーネントテスト。
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PriorityScoreBadge, { type CustomerScoreData } from "./PriorityScoreBadge";

// react-i18next をモック（テスト環境に i18n 初期化不要）
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      // シンプルな翻訳マップ
      const map: Record<string, string> = {
        "priority.noData": "未評価",
        "priority.provisional": "暫定",
        "priority.tier.要観察": "要観察",
        "priority.tier.有望": "有望",
        "priority.tier.最有望": "最有望",
        "priority.coldStartTooltip": "データ不足",
        "priority.noDataTooltip": "スコア未計算",
        "priority.tooltipFormat": `スコア: ${opts?.score}% / 確信度: ${opts?.confidence}% / 母数: ${opts?.sample}件`,
      };
      return map[key] ?? key;
    },
  }),
}));

const baseScore: CustomerScoreData = {
  tier: "有望",
  score: 0.5,
  confidence: 0.8,
  is_cold_start: false,
  sample_size: 10,
  signal_summary: {
    total_messages: 10,
    price_focus_count: 2,
    substance_talk_count: 5,
    self_disclosure_count: 1,
    early_purchase_signal_count: 0,
  },
};

describe("PriorityScoreBadge", () => {
  it("score=null → 「未評価」を表示する", () => {
    render(<PriorityScoreBadge score={null} />);
    expect(screen.getByText("未評価")).toBeTruthy();
  });

  it("is_cold_start=true → 「暫定」を表示する", () => {
    render(<PriorityScoreBadge score={{ ...baseScore, is_cold_start: true }} />);
    expect(screen.getByText("暫定")).toBeTruthy();
  });

  it("tier=最有望 → priority-top クラスが付く", () => {
    render(<PriorityScoreBadge score={{ ...baseScore, tier: "最有望", score: 0.8 }} />);
    const badge = screen.getByText("最有望");
    expect(badge.className).toContain("priority-top");
  });

  it("tier=有望 → priority-promising クラスが付く", () => {
    render(<PriorityScoreBadge score={baseScore} />);
    const badge = screen.getByText("有望");
    expect(badge.className).toContain("priority-promising");
  });

  it("tier=要観察 → priority-watching クラスが付く", () => {
    render(<PriorityScoreBadge score={{ ...baseScore, tier: "要観察", score: 0.2 }} />);
    const badge = screen.getByText("要観察");
    expect(badge.className).toContain("priority-watching");
  });

  it("tooltip にスコア・確信度・母数が含まれる", () => {
    render(<PriorityScoreBadge score={{ ...baseScore, score: 0.5, confidence: 0.8, sample_size: 10 }} />);
    const badge = screen.getByTitle(/スコア.*確信度.*母数/);
    expect(badge).toBeTruthy();
  });
});
