/**
 * FunnelSection unit tests — safety / UI polish
 *
 * テスト対象:
 *   - 修正1: new_customers.target === 0 のとき "/ 0" が表示されない
 *   - 修正1: new_customers.target === 0 のとき AchievementBar が表示されない
 *   - 修正1: new_customers.target === 0 のとき "目標未設定" が表示される
 *   - 修正1: new_customers.target > 0 のとき従来表示（target値と AchievementBar）が出る
 *   - 修正2: API エラー時にクラッシュせず説明文が表示される
 *   - 修正3: ActiveCard に activeNote の補足文が表示される
 */

import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { FunnelSection } from "./FunnelSection";
import type { FunnelResponse, RevenueSummaryResponse, FollowUpsResponse } from "../../api/funnel";

// ─── モック群 ────────────────────────────────────────────────────────────────

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const map: Record<string, string> = {
        "funnel.sectionTitle": "ファネルダッシュボード",
        "funnel.leads": "リード獲得",
        "funnel.conversion": "商談化率",
        "funnel.active": "進行中商談",
        "funnel.activeNote": "当月開始の進行中商談",
        "funnel.closed": "成約・失注",
        "funnel.target": "目標",
        "funnel.converted": "商談化",
        "funnel.unitDeal": "件",
        "funnel.unitCompany": "社",
        "funnel.coverageOfRemaining": "残り目標カバー率",
        "funnel.bottleneck": "ボトルネック",
        "funnel.wonRate": "成約率",
        "funnel.won": "成約",
        "funnel.lost": "失注",
        "funnel.revenueTitle": "売上目標対比",
        "funnel.pace_on_track": "ペース正常",
        "funnel.pace_ahead": "ペース良好",
        "funnel.pace_behind": "ペース遅延",
        "funnel.newRevenue": "新規",
        "funnel.repeatRevenue": "リピート",
        "funnel.grossMargin": "粗利",
        "funnel.newCustomers": "新規顧客獲得",
        "funnel.activeExisting": "アクティブ既存顧客",
        "funnel.noTarget": "目標未設定",
        "funnel.errorFetch": "ファネルデータを取得できませんでした。時間をおいて再読み込みしてください。",
        "funnel.followUpTitle": "要フォロー顧客",
        "funnel.viewAll": "詳細を見る",
        "funnel.segOrderStopped": "発注停止",
        "funnel.segNoRepeat": "初回後未フォロー",
        "funnel.segWonNoOrder": "成約後未発注",
        "common.loading": "読み込み中...",
        "common.errorLoad": "読み込みに失敗しました",
      };
      if (opts && typeof opts.count === "number") return `${opts.count}件 仕入コスト未入力`;
      return map[key] ?? key;
    },
  }),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("../../api/funnel", () => ({
  getFunnel: vi.fn(),
  getRevenueSummary: vi.fn(),
  getFollowUps: vi.fn(),
}));

import { getFunnel, getRevenueSummary, getFollowUps } from "../../api/funnel";

// ─── フィクスチャ ─────────────────────────────────────────────────────────────

const FUNNEL: FunnelResponse = {
  month: "2026-06",
  month_elapsed_pct: 50,
  leads: { target: 10, actual: 7 },
  conversion: { target_rate: 30, actual_rate: 25, converted: 3 },
  active: { count: 5, amount: 1_500_000, coverage_pct_of_remaining_target: 60 },
  closed: { won_target: 5, won: 3, won_rate: 60, lost: 1 },
};

const REVENUE_WITH_TARGET: RevenueSummaryResponse = {
  revenue: { target: 5_000_000, actual: 3_000_000, pace: "on_track" },
  split: { new: 1_000_000, repeat: 2_000_000 },
  new_customers: { target: 3, actual: 2 },
  active_existing_customers: 8,
  gross_margin: { amount: 900_000, uncosted_orders: 0 },
};

const REVENUE_NO_TARGET: RevenueSummaryResponse = {
  ...REVENUE_WITH_TARGET,
  new_customers: { target: 0, actual: 2 },
};

const FOLLOW_UPS: FollowUpsResponse = {
  items: [
    {
      customer_id: 1,
      name: "テスト顧客",
      segment: "order_stopped",
      days: 30,
      last_order_at: "2026-05-01",
      last_contact_at: "2026-05-15",
      assignee: "担当A",
    },
  ],
};

function renderSection(revenue: RevenueSummaryResponse) {
  vi.mocked(getFunnel).mockResolvedValue(FUNNEL);
  vi.mocked(getRevenueSummary).mockResolvedValue(revenue);
  vi.mocked(getFollowUps).mockResolvedValue(FOLLOW_UPS);
  return render(
    <MemoryRouter>
      <FunnelSection month="2026-06" viewMode="management" />
    </MemoryRouter>
  );
}

async function waitForLoaded() {
  await waitFor(() => expect(screen.queryByText("読み込み中...")).toBeFalsy());
}

// ─── テスト ──────────────────────────────────────────────────────────────────

describe("FunnelSection — 修正1: new_customers target=0", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("target === 0 のとき「/ 0」が表示されない", async () => {
    renderSection(REVENUE_NO_TARGET);
    await waitForLoaded();
    // サイドカード内に "/ 0" のテキストが存在しない
    expect(screen.queryByText(/\/ 0/)).toBeFalsy();
  });

  it("target === 0 のとき「目標未設定」が表示される", async () => {
    renderSection(REVENUE_NO_TARGET);
    await waitForLoaded();
    expect(screen.getByText("目標未設定")).toBeTruthy();
  });

  it("target === 0 のとき AchievementBar（fn-progress-wrap）がサイドカード内にない", async () => {
    const { container } = renderSection(REVENUE_NO_TARGET);
    await waitForLoaded();
    const sideCards = container.querySelector(".fn-side-cards");
    expect(sideCards).toBeTruthy();
    expect(sideCards?.querySelector(".fn-progress-wrap")).toBeFalsy();
  });

  it("target > 0 のとき target の値が表示される", async () => {
    renderSection(REVENUE_WITH_TARGET);
    await waitForLoaded();
    // "/ 3" が存在する（target=3）
    expect(screen.getAllByText(/\/\s*3/).length).toBeGreaterThan(0);
  });

  it("target > 0 のとき AchievementBar がサイドカード内に表示される", async () => {
    const { container } = renderSection(REVENUE_WITH_TARGET);
    await waitForLoaded();
    const sideCards = container.querySelector(".fn-side-cards");
    expect(sideCards?.querySelector(".fn-progress-wrap")).toBeTruthy();
  });

  it("target > 0 のとき「目標未設定」は表示されない", async () => {
    renderSection(REVENUE_WITH_TARGET);
    await waitForLoaded();
    expect(screen.queryByText("目標未設定")).toBeFalsy();
  });
});

describe("FunnelSection — 修正2: API エラー表示", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("API エラー時にクラッシュせず説明文が表示される", async () => {
    vi.mocked(getFunnel).mockRejectedValue(new Error("Network Error"));
    vi.mocked(getRevenueSummary).mockRejectedValue(new Error("Network Error"));
    vi.mocked(getFollowUps).mockRejectedValue(new Error("Network Error"));
    render(
      <MemoryRouter>
        <FunnelSection month="2026-06" viewMode="management" />
      </MemoryRouter>
    );
    await waitFor(() =>
      expect(
        screen.getByText("ファネルデータを取得できませんでした。時間をおいて再読み込みしてください。")
      ).toBeTruthy()
    );
  });

  it("API エラー時に section が残る（セクション全体がクラッシュしない）", async () => {
    vi.mocked(getFunnel).mockRejectedValue(new Error("500 Internal Server Error"));
    vi.mocked(getRevenueSummary).mockResolvedValue(REVENUE_WITH_TARGET);
    vi.mocked(getFollowUps).mockResolvedValue(FOLLOW_UPS);
    const { container } = render(
      <MemoryRouter>
        <FunnelSection month="2026-06" viewMode="management" />
      </MemoryRouter>
    );
    await waitForLoaded();
    expect(container.querySelector(".fn-section")).toBeTruthy();
    expect(container.querySelector(".fn-error")).toBeTruthy();
  });
});

describe("FunnelSection — 修正3: ActiveCard に補足文", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("ActiveCard に「当月開始の進行中商談」の補足文が表示される", async () => {
    renderSection(REVENUE_WITH_TARGET);
    await waitForLoaded();
    expect(screen.getByText("当月開始の進行中商談")).toBeTruthy();
  });
});
