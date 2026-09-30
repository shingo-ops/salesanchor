/**
 * LlmUsageSection テスト
 *
 * カバー:
 *   - NULL 値（thoughts_tokens 等）が「記録なし」として表示される
 *   - 使いみちラベルが i18n 経由で表示される
 *   - 費用が USD 通貨フォーマットで表示される
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import i18n from "../../../i18n";
import { LlmUsageSection } from "./LlmUsageSection";

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
};

const view = () => render(<LlmUsageSection days={30} t={i18n.t.bind(i18n)} />);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockResolvedValue(response);
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
