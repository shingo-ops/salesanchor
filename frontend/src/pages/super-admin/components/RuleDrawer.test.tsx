/**
 * RuleDrawer / RuleManagementPanel テスト（予約の手がかりの行を、一覧に出せる・編集で壊さない）
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import i18n from "../../../i18n";
import { RuleDrawer, type RuleEntry } from "./RuleDrawer";
import { RuleManagementPanel } from "./RuleManagementPanel";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), getBlob: vi.fn() },
  ApiError: class extends Error {},
}));

const base = { enabled: true, note: "", exclude_pattern: "", created_at: "", updated_at: "" };
const heading: RuleEntry = {
  ...base, id: 5, status_id: "ST0005", canonical: "Pre-order", search_pattern: "HEAD-WORD", priority: 10,
  match_type: "REGEX", effect: "HEADING",
};
const release: RuleEntry = {
  ...base, id: 6, status_id: "ST0006", canonical: "Pre-order", search_pattern: "", priority: 10,
  match_type: "RELEASE", effect: "RELEASE_AHEAD",
};
const soldOut: RuleEntry = {
  ...base, id: 1, status_id: "ST0001", canonical: "Sold out", search_pattern: "SOLD-WORD", priority: 1,
  match_type: "LITERAL", effect: "EXCLUDE",
};

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path.startsWith("/super-admin/status-master")) return [soldOut, heading, release];
    return [
      { canonical: "Pre-order", effect: "OUTPUT" },
      { canonical: "Pre-order", effect: "HEADING" },
    ];
  });
  vi.mocked(api.patch).mockResolvedValue({});
  vi.mocked(api.post).mockResolvedValue({ matched: true, detail: "" });
});

afterEach(() => cleanup());

it("lists context rows under their own tab without failing on the new values", async () => {
  render(<MemoryRouter><RuleManagementPanel /></MemoryRouter>);
  await screen.findByText("SOLD-WORD");
  fireEvent.click(screen.getByRole("tab", { name: /Pre-order clues/ }));
  await screen.findByText("HEAD-WORD");
  expect(screen.queryByText("SOLD-WORD")).toBeNull();
  expect(screen.getAllByText("Release date").length).toBeGreaterThan(0);
});

it("keeps match_type and effect of a context row when it is edited", async () => {
  render(<RuleDrawer open onClose={vi.fn()} onSaved={vi.fn()} editRule={heading} />);
  fireEvent.change(await screen.findByTestId("rule-drawer-test-input"), { target: { value: "HEAD-WORD x" } });
  fireEvent.click(screen.getByTestId("rule-drawer-test-button"));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith(
    "/super-admin/status-master/preview", { match_type: "REGEX", search_pattern: "HEAD-WORD", input_text: "HEAD-WORD x" },
  ));
  await waitFor(() => expect((screen.getByTestId("rule-drawer-submit-btn") as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(screen.getByTestId("rule-drawer-submit-btn"));
  await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/super-admin/status-master/5", expect.objectContaining({
    match_type: "REGEX", effect: "HEADING", canonical: "Pre-order",
  })));
});

it("does not require a pattern test for a release-date rule", async () => {
  render(<RuleDrawer open onClose={vi.fn()} onSaved={vi.fn()} editRule={release} />);
  const submit = (await screen.findByTestId("rule-drawer-submit-btn")) as HTMLButtonElement;
  expect(submit.disabled).toBe(false);
  fireEvent.click(submit);
  await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/super-admin/status-master/6", expect.objectContaining({
    match_type: "RELEASE", effect: "RELEASE_AHEAD",
  })));
});

it("shows one canonical option even when the same canonical comes back with different effects", async () => {
  const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  render(<RuleDrawer open onClose={vi.fn()} onSaved={vi.fn()} editRule={heading} />);
  const select = (await screen.findByTestId("rule-drawer-canonical")) as HTMLSelectElement;
  await waitFor(() => expect(
    Array.from(select.options).filter((o) => o.value === "Pre-order").length,
  ).toBe(1));
  expect(errorSpy.mock.calls.some((c) => String(c[0]).includes("same key"))).toBe(false);
  errorSpy.mockRestore();
});
