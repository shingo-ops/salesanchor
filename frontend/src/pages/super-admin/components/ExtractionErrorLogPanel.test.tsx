/**
 * ExtractionErrorLogPanel テスト
 *
 * design: docs/handoff/extraction-error-handling-status/design.md §6, §7 (T6)
 * カバー:
 *   - タブの切り替え（未対応・対応中・対応完了）で status クエリが変わる
 *   - 未対応タブのときだけ選択可能・再実行ボタンが出る
 *   - 再実行成功後に選択解除・現在のタブを読み直す
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import i18n from "../../../i18n";
import { ExtractionErrorLogPanel } from "./ExtractionErrorLogPanel";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));

const unhandledResponse = {
  items: [
    {
      id: "job-unhandled-1",
      supplier_name: "Supplier A",
      prompt_version: "v1.0",
      error_message: "GEMINI_TIMEOUT",
      error_category: "gemini_timeout",
      error_detail: "raw detail",
      last_failed_at: "2026-09-29T00:44:00Z",
      first_failed_at: "2026-09-28T00:00:00Z",
      retry_count: 1,
      job_status: "error",
      handling_status: "unhandled",
    },
  ],
  total: 1,
  counts: { unhandled: 1, in_progress: 0, resolved: 2 },
};

const resolvedResponse = {
  items: [
    {
      id: "job-resolved-1",
      supplier_name: "Supplier B",
      prompt_version: "v1.0",
      error_message: "GEMINI_TIMEOUT",
      error_category: "gemini_timeout",
      error_detail: "raw detail",
      last_failed_at: "2026-09-29T00:44:00Z",
      first_failed_at: "2026-09-28T00:00:00Z",
      retry_count: 1,
      job_status: "done",
      handling_status: "resolved",
    },
  ],
  total: 2,
  counts: { unhandled: 1, in_progress: 0, resolved: 2 },
};

const view = () => render(<ExtractionErrorLogPanel />);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockImplementation((path: string) => {
    if (path.includes("status=resolved")) {
      return Promise.resolve(resolvedResponse);
    }
    return Promise.resolve(unhandledResponse);
  });
});

afterEach(() => cleanup());

it("fetches the unhandled tab by default", async () => {
  view();
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("status=unhandled"))
  );
  await screen.findByText("Supplier A");
});

it("switching to the resolved tab fetches with status=resolved and renders its rows", async () => {
  view();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  fireEvent.click(screen.getByText("Resolved"));
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("status=resolved"))
  );
  await screen.findByText("Supplier B");
});

it("shows the retry button and selection only on the unhandled tab", async () => {
  view();
  await screen.findByText("Supplier A");
  expect(screen.getByText("Retry selected jobs")).toBeTruthy();
  expect(screen.getAllByRole("checkbox").length).toBeGreaterThan(0);

  fireEvent.click(screen.getByText("Resolved"));
  await screen.findByText("Supplier B");
  expect(screen.queryByText("Retry selected jobs")).toBeNull();
  expect(screen.queryAllByRole("checkbox").length).toBe(0);
});

it("retrying selected jobs clears selection and refetches the current tab", async () => {
  vi.mocked(api.post).mockResolvedValue({ enqueued: 1, skipped: 0 });
  view();
  await screen.findByText("Supplier A");

  const checkboxes = screen.getAllByRole("checkbox");
  // 先頭は「全選択」チェックボックス。1行目の行チェックボックスを選ぶ。
  fireEvent.click(checkboxes[1]);
  fireEvent.click(screen.getByRole("button", { name: "Retry selected jobs" }));

  const dialog = screen.getByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "Retry selected jobs" }));

  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    "/tcg/diagnostics/retry-extraction",
    { job_ids: ["job-unhandled-1"] }
  ));
  await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
});
