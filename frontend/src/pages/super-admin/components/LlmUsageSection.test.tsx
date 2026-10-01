/**
 * LlmUsageSection テスト
 *
 * カバー:
 *   - NULL 値（thoughts_tokens 等）が「記録なし」として表示される
 *   - 使いみちラベルが i18n 経由で表示される
 *   - 費用が USD 通貨フォーマットで表示される
 *   - 使いみち別の合計列は computed_total_tokens を表示する
 *   - total_mismatch_calls > 0 のとき不一致メモが表示される
 *   - 日次・月次の使いみち別グラフがレンダリングされる
 *   - 呼び出し回数ラベルが「応答が返った回数」系の文言に変わっている
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import i18n from "../../../i18n";
import { formatCompactNumber, LlmUsageSection } from "./LlmUsageSection";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));

const response = {
  total: {
    calls: 3,
    prompt_tokens: 900,
    cached_content_tokens: null,
    candidates_tokens: 300,
    thoughts_tokens: null,
    tool_use_prompt_tokens: null,
    total_tokens: null,
    cost_usd: 0.0021,
    computed_total_tokens: 1200,
    total_mismatch_calls: 0,
  },
  by_purpose: [
    {
      purpose: "line_extraction",
      calls: 3,
      prompt_tokens: 900,
      cached_content_tokens: null,
      candidates_tokens: 300,
      thoughts_tokens: null,
      tool_use_prompt_tokens: null,
      total_tokens: null,
      cost_usd: 0.0021,
      computed_total_tokens: 1200,
      total_mismatch_calls: 0,
    },
  ],
  by_model: [{ model: "gemini-3.1-flash-lite", calls: 3, cost_usd: 0.0021 }],
  daily: [
    {
      date: "2026-10-01",
      calls: 3,
      cost_usd: 0.0021,
      prompt_tokens: 900,
      candidates_tokens: 300,
      thoughts_tokens: null,
    },
  ],
  daily_by_purpose: [
    { date: "2026-10-01", purpose: "line_extraction", cost_usd: 0.0021, calls: 3 },
  ],
  monthly_by_purpose: [
    { month: "2026-10", purpose: "line_extraction", calls: 3, cost_usd: 0.0021 },
  ],
  daily_requests: [
    { date: "2026-10-01", attempts: 5, completed: 3, failed: 1, success_rate: 0.75 },
  ],
  daily_errors: [
    { date: "2026-10-01", error_code: "TIMEOUT", count: 1 },
  ],
  daily_by_model: [
    {
      date: "2026-10-01",
      model: "gemini-3.1-flash-lite",
      calls: 3,
      prompt_tokens: 900,
      output_tokens: 300,
      cost_usd: 0.0021,
    },
  ],
};

const view = () => render(<LlmUsageSection days={30} t={i18n.t.bind(i18n)} />);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockResolvedValue(response);
  // recharts の ResponsiveContainer は要素サイズを測って描画するため、
  // jsdom ではサイズを明示しないと子要素が描画されない。
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
    configurable: true,
    value: 600,
  });
  Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
    configurable: true,
    value: 240,
  });
});

afterEach(() => cleanup());

it("fetches usage with the given days and shows the purpose label", async () => {
  view();
  await screen.findByText("LINE Extraction");
  expect(api.get).toHaveBeenCalledWith("/tcg/analysis-dashboard/llm-usage?days=30");
});

it("shows Not reported for null values (thoughts_tokens / cached_content_tokens)", async () => {
  view();
  await screen.findByText("LINE Extraction");
  expect(screen.getAllByText("Not reported").length).toBeGreaterThan(0);
});

it("formats cost as a USD currency string", async () => {
  view();
  await screen.findByText("LINE Extraction");
  expect(screen.getAllByText(/\$0\.0021/).length).toBeGreaterThan(0);
});

it("falls back to the raw purpose code for an unknown purpose", async () => {
  vi.mocked(api.get).mockResolvedValue({
    ...response,
    by_purpose: [{ ...response.by_purpose[0], purpose: "some_new_purpose" }],
  });
  view();
  await screen.findByText("some_new_purpose");
});

it("shows computed_total_tokens (not the raw total_tokens) in the colTotal column", async () => {
  view();
  await screen.findByText("LINE Extraction");
  // total_tokens is null (not reported), but computed_total_tokens=1200 is shown
  expect(screen.getAllByText("1,200").length).toBeGreaterThan(0);
});

it("does not show a mismatch note when total_mismatch_calls is 0", async () => {
  view();
  await screen.findByText("LINE Extraction");
  expect(screen.queryByText(/do not match the total Google returned/)).toBeNull();
});

it("shows a mismatch note when total_mismatch_calls > 0", async () => {
  vi.mocked(api.get).mockResolvedValue({
    ...response,
    total: { ...response.total, total_mismatch_calls: 2 },
  });
  view();
  await screen.findByText("2 call(s) do not match the total Google returned");
});

it("uses the 'Calls with response' label instead of the old 'Call Count' label", async () => {
  view();
  await screen.findByText("LINE Extraction");
  expect(screen.getAllByText("Calls with response").length).toBeGreaterThan(0);
  expect(screen.queryByText("Call Count")).toBeNull();
});

it("mentions that failed calls without a response are excluded", async () => {
  view();
  await screen.findByText(/Failed calls with no response are not included/);
});

it("renders the daily and monthly by-purpose charts with legend entries", async () => {
  view();
  await screen.findByText("Daily Cost by Purpose");
  await screen.findByText("Monthly Cost by Purpose");
  expect(screen.getAllByText("LINE Extraction").length).toBeGreaterThanOrEqual(1);
});

it("shows the empty state for the by-purpose charts when there is no data", async () => {
  vi.mocked(api.get).mockResolvedValue({
    ...response,
    daily_by_purpose: [],
    monthly_by_purpose: [],
  });
  view();
  await screen.findByText("Daily Cost by Purpose");
  expect(screen.getAllByText("No data available").length).toBeGreaterThanOrEqual(2);
});

it("renders the requests & success rate chart and the errors-by-type chart", async () => {
  view();
  await screen.findByText("Overview (LINE Extraction)");
  await screen.findByText("Requests & Success Rate");
  await screen.findByText("Errors by Type");
});

it("shows the empty state for the errors chart when there are no errors", async () => {
  vi.mocked(api.get).mockResolvedValue({
    ...response,
    daily_errors: [],
  });
  view();
  await screen.findByText("Errors by Type");
  expect(screen.getAllByText("No data available").length).toBeGreaterThan(0);
});

it("renders the per-model trend charts (input tokens / output tokens / requests)", async () => {
  view();
  await screen.findByText("Overview (LINE Extraction)");
  expect(screen.getAllByText("Input Tokens").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Output Tokens").length).toBeGreaterThan(0);
  expect(screen.getAllByText("gemini-3.1-flash-lite").length).toBeGreaterThan(0);
});

it("shows the success rate rounded to 1 decimal in the note (overview section)", async () => {
  view();
  await screen.findByText(/Success rate is completed calls divided by completed \+ failed/);
});

it("shows a single summary card at the top with hero cost and 5 stats", async () => {
  const { container } = render(<LlmUsageSection days={30} t={i18n.t.bind(i18n)} />);
  await screen.findByText("LINE Extraction");
  const summary = container.querySelector(".llm-usage-summary");
  expect(summary).not.toBeNull();
  const text = summary?.textContent ?? "";
  expect(text).toContain("Total Cost");
  expect(text).toContain("$0.0021");
  expect(text).toContain("Calls with response");
  expect(text).toContain("3");
  expect(text).toContain("Input Tokens");
  expect(text).toContain("900");
  expect(text).toContain("Output Tokens");
  expect(text).toContain("300");
  expect(text).toContain("Success Rate (LINE Extraction)");
  // completed=3, failed=1 -> 3 / (3+1) = 75.0%
  expect(text).toContain("75.0%");
  expect(text).toContain("Error Count (LINE Extraction)");
});

it("shows Not reported for the summary success rate when daily_requests is empty", async () => {
  vi.mocked(api.get).mockResolvedValue({ ...response, daily_requests: [] });
  const { container } = render(<LlmUsageSection days={30} t={i18n.t.bind(i18n)} />);
  await screen.findByText("LINE Extraction");
  const summary = container.querySelector(".llm-usage-summary");
  expect(summary?.textContent).toContain("Not reported");
});

it("removes the old 4 separate metric cards (consolidated into the summary card)", async () => {
  const { container } = render(<LlmUsageSection days={30} t={i18n.t.bind(i18n)} />);
  await screen.findByText("LINE Extraction");
  expect(container.querySelector(".analysis-dashboard-metrics")).toBeNull();
});

it("consolidates all 7 charts into a single charts card (no per-chart Card wrappers)", async () => {
  const { container } = render(<LlmUsageSection days={30} t={i18n.t.bind(i18n)} />);
  await screen.findByText("LINE Extraction");

  const chartsCard = container.querySelector(".llm-usage-charts");
  expect(chartsCard).not.toBeNull();
  const text = chartsCard?.textContent ?? "";
  expect(screen.queryByText("Charts")).toBeNull();
  // カード見出しは「グラフ」ではなく行1タイトル「概要（LINE抽出）」。重複表示はしない
  expect(screen.getAllByText("Overview (LINE Extraction)").length).toBe(1);
  expect(text).toContain("Requests & Success Rate");
  expect(text).toContain("Errors by Type");
  expect(text).toContain("Input Tokens");
  expect(text).toContain("Output Tokens");
  expect(text).toContain("Requests");
  expect(text).toContain("Daily Cost by Purpose");
  expect(text).toContain("Monthly Cost by Purpose");

  // 各グラフは __item 内にあり、ネストした Card（.analysis-dashboard-chart-card）を持たない
  expect(chartsCard?.querySelectorAll(".llm-usage-charts__item").length).toBeGreaterThanOrEqual(7);
  expect(chartsCard?.querySelector(".analysis-dashboard-chart-card")).toBeNull();

  // サマリーカードと表（段2〜4）はそのまま存在する
  expect(container.querySelector(".llm-usage-summary")).not.toBeNull();
  const chartCards = container.querySelectorAll(".analysis-dashboard-chart-card");
  expect(chartCards.length).toBe(3); // byPurposeTitle / dailyTitle / byModelTitle の表カードのみ
});

describe("formatCompactNumber", () => {
  it("abbreviates large numbers for chart y-axis ticks", () => {
    expect(formatCompactNumber(29766307, "en")).toBe("30M");
    expect(formatCompactNumber(388393, "en")).toBe("388K");
  });

  it("returns the raw number when it is small enough to need no abbreviation", () => {
    expect(formatCompactNumber(3, "en")).toBe("3");
  });
});
