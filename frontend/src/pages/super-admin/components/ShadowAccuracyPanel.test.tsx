import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import i18n from "../../../i18n";
import { ShadowAccuracyPanel } from "./ShadowAccuracyPanel";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn() },
  ApiError: class extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

const zeroSignals = { S1: 0, S2: 0, S3: 0, S4: 0, S5: 0, S6: 0 };

const summary = {
  days: 7,
  supplier_id: null,
  totals: {
    blocks: 40,
    needs_review_count: 10,
    auto_confirmed: 30,
    auto_confirmed_ratio: 0.75,
    matched: 31,
    ambiguous: 4,
    unmatched: 5,
    price_fixed: 36,
    quantity_fixed: 35,
    sold_out: 3,
    pre_order: 2,
  },
  signals: { ...zeroSignals, S1: 7, S4: 2 },
  conditions: [{ condition: "Sealed box", blocks: 25 }],
  by_supplier: [
    {
      supplier_id: 5,
      supplier_name: "Supplier A",
      blocks: 40,
      needs_review_count: 10,
      needs_review_ratio: 0.25,
      signals: { ...zeroSignals, S1: 7, S4: 2 },
    },
  ],
};

const posts = {
  items: [
    {
      job_id: "job-1",
      run_id: "run-1",
      supplier_id: 5,
      supplier_name: "Supplier A",
      posted_at: "2026-09-30T00:00:00Z",
      blocks: 2,
      needs_review_count: 1,
      signals: { ...zeroSignals, S1: 1 },
    },
  ],
  total: 1,
  offset: 0,
  limit: 20,
};

const detail = {
  job_id: "job-1",
  run: {
    id: "run-1",
    prompt_key: "raw_copy_extraction",
    engine_version: "v7",
    requested_model: "gemini-x",
    status: "completed",
    started_at: "2026-09-30T00:00:00Z",
    finished_at: null,
  },
  supplier_id: 5,
  supplier_name: "Supplier A",
  posted_at: "2026-09-30T00:00:00Z",
  raw_text: "Heading line\nProduct 1 sold out\nProduct 2",
  blocks: [
    {
      id: "b1",
      block_index: 0,
      line_start: 2,
      line_end: 2,
      heading_line_start: 1,
      heading_line_end: 1,
      raw_product_name: "Product 1",
      raw_price: "1500",
      raw_unit: "BOX",
      raw_quantity: "sold out",
      raw_state: "none",
      raw_ship: "none",
      raw_multi: null,
      product_id: 9,
      product_name: "Matched Product",
      product_mark: "M",
      match_status: "matched",
      needs_review: false,
      status: "In Stock",
      condition_canonical: "Sealed box",
      price_normalized: 1500,
      quantity_normalized: 1,
      ship_offer_type: null,
      ship_timing: null,
      exclusion: null,
      evidence: { basis: "RAWCODE" },
      review_items: [],
      signals: { ...zeroSignals, S1: true },
    },
  ],
};

const calls = () => vi.mocked(api.get).mock.calls.map((c) => String(c[0]));

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(api.get).mockImplementation((path: string) => {
    if (path.includes("/tcg/shadow-accuracy/summary")) return Promise.resolve(summary);
    if (path.includes("/tcg/shadow-accuracy/posts/job-1")) return Promise.resolve(detail);
    if (path.includes("/tcg/shadow-accuracy/posts")) return Promise.resolve(posts);
    return Promise.reject(new Error(`unexpected ${path}`));
  });
});

afterEach(() => cleanup());

it("fetches the 7-day summary on open and renders the totals and the signal counts", async () => {
  render(<ShadowAccuracyPanel />);
  await waitFor(() => expect(calls()).toContain("/tcg/shadow-accuracy/summary?days=7"));
  await screen.findByText("30 (75%)");
  expect(screen.getByText("S1 Missed sold-out")).toBeTruthy();
  expect(screen.getByRole("button", { name: /Show posts with S1/ }).textContent).toBe("7");
});

it("states that signals are candidates and not errors", async () => {
  render(<ShadowAccuracyPanel />);
  await screen.findByText(/candidates for errors, not errors themselves/);
});

it("changing the period refetches the summary with the new days", async () => {
  render(<ShadowAccuracyPanel />);
  await screen.findByText("30 (75%)");
  fireEvent.change(screen.getByLabelText("Period"), { target: { value: "0" } });
  await waitFor(() => expect(calls()).toContain("/tcg/shadow-accuracy/summary?days=0"));
});

it("choosing a supplier refetches with supplier_id and keeps the supplier choices", async () => {
  render(<ShadowAccuracyPanel />);
  await screen.findByText("30 (75%)");
  fireEvent.change(screen.getByLabelText("Supplier"), { target: { value: "5" } });
  await waitFor(() => expect(calls()).toContain("/tcg/shadow-accuracy/summary?days=7&supplier_id=5"));
  expect(within(screen.getByLabelText("Supplier")).getByText("Supplier A")).toBeTruthy();
});

it("pressing a signal count opens Post comparison filtered by that signal", async () => {
  render(<ShadowAccuracyPanel />);
  await screen.findByText("30 (75%)");
  fireEvent.click(screen.getByRole("button", { name: /Show posts with S4/ }));
  await waitFor(() =>
    expect(calls().some((c) => c.startsWith("/tcg/shadow-accuracy/posts?") && c.includes("signal=S4"))).toBe(true),
  );
  expect((screen.getByLabelText("Signal") as HTMLSelectElement).value).toBe("S4");
});

it("selecting a post loads the detail and highlights the block and heading ranges in the source", async () => {
  render(<ShadowAccuracyPanel />);
  fireEvent.click(await screen.findByText("Post comparison"));
  fireEvent.click(await within(await screen.findByRole("table")).findByText("Supplier A"));
  await waitFor(() => expect(calls()).toContain("/tcg/shadow-accuracy/posts/job-1"));
  await screen.findByText("Product 1 sold out");
  expect(screen.getByText("Copied")).toBeTruthy();
  expect(screen.getByText("Judgement")).toBeTruthy();
  expect(screen.getByText("Reason and evidence")).toBeTruthy();
  expect(screen.getByText("S1 Sold out")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "Show in source" }));
  const block = document.querySelector('[data-line-number="2"]');
  const heading = document.querySelector('[data-line-number="1"]');
  const other = document.querySelector('[data-line-number="3"]');
  expect(block?.getAttribute("data-range")).toBe("block");
  expect(heading?.getAttribute("data-range")).toBe("heading");
  expect(other?.getAttribute("data-range")).toBeNull();
});

it("shows the super-admin-only message when the API answers 403", async () => {
  const { ApiError } = await import("../../../lib/api");
  vi.mocked(api.get).mockRejectedValue(new ApiError("forbidden", 403, null));
  render(<ShadowAccuracyPanel />);
  await screen.findByRole("alert");
  expect(screen.getByRole("alert").textContent).toBe(i18n.t("superAdmin.supplierQuality.superAdminOnly"));
});

it("renders in Japanese with the same keys", async () => {
  await i18n.changeLanguage("ja");
  render(<ShadowAccuracyPanel />);
  await screen.findByText(i18n.t("shadowAccuracy.tabs.summary"));
  expect(screen.getByText(i18n.t("shadowAccuracy.tabs.posts"))).toBeTruthy();
  expect(i18n.t("shadowAccuracy.tabs.summary")).not.toBe("shadowAccuracy.tabs.summary");
});
