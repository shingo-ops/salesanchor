import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../../lib/api";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import i18n from "../../../i18n";
import NeedsReviewTabsPanel from "./NeedsReviewTabsPanel";

vi.mock("../../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("../../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

const productionResponse = {
  items: [],
  total: 0,
  item_total: 0,
  offset: 0,
  limit: 20,
  providers: [],
  works: [],
};

const shadowResponse = {
  items: [
    {
      id: "shadow-1",
      block_text: "Product A 1500yen",
      raw_product_name: "Product A",
      raw_price: "1500yen",
      raw_unit: "pcs",
      raw_quantity: "1",
      raw_state: "unused",
      raw_ship: "none",
      match_status: "ambiguous",
      product_id: null,
      work_id: null,
      needs_review: true,
      review_items: [
        { item: "product", reason: "2 candidates", candidates: [{ product_id: 1, product_name: "Product X" }] },
      ],
      supplier_id: 5,
      supplier_name: "Supplier A",
      created_at: "2026-09-28T00:00:00Z",
    },
  ],
  total: 1,
  offset: 0,
  limit: 20,
};

const bottlenecksResponse = {
  days: 7,
  by_supplier: [
    { supplier_id: 5, supplier_name: "Supplier A", total: 10, matched: 6, needs_review_count: 4, matched_ratio: 0.6 },
  ],
  by_item: [{ supplier_id: 5, supplier_name: "Supplier A", item: "product", count: 3 }],
};

const view = () => render(<MemoryRouter><NeedsReviewTabsPanel /></MemoryRouter>);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockImplementation((path: string) => {
    if (path.includes("/tcg/shadow-results/bottlenecks")) {
      return Promise.resolve(bottlenecksResponse);
    }
    if (path.includes("/tcg/shadow-results")) {
      return Promise.resolve(shadowResponse);
    }
    return Promise.resolve(productionResponse);
  });
});

afterEach(() => cleanup());

it("never fetches when not super admin", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false });
  view();
  expect(api.get).not.toHaveBeenCalled();
});

it("fetches production review results on the default tab", async () => {
  view();
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("status_tab=NEEDS_REVIEW"))
  );
});

it("switching to the shadow tab fetches shadow-results and renders rows", async () => {
  view();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  fireEvent.click(screen.getByText("Shadow run review"));
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/tcg/shadow-results?"))
  );
  await screen.findByText("Supplier A");
});

it("switching to the bottlenecks tab fetches bottlenecks and renders the breakdown", async () => {
  view();
  fireEvent.click(screen.getByText("Bottlenecks"));
  await waitFor(() =>
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/tcg/shadow-results/bottlenecks?days=7"))
  );
  await screen.findByText("60%");
});

const productionItem = (id: string, details: { code: string; source: "gemini" | "system" | null; fix_stage: "extraction" | "analysis" | null }[]) => ({
  extraction_item_id: id,
  source_message_id: `msg-${id}`,
  provider: `Supplier ${id}`,
  raw_text: "",
  gemini: { name: `Product ${id}`, span: "" },
  system: {},
  review_issues: [],
  condition_review: null,
  review_reason_details: details,
});

it("shows the source column and translated reasons on the production tab", async () => {
  vi.mocked(api.get).mockImplementation(() => Promise.resolve({
    ...productionResponse,
    items: [
      productionItem("g", [{ code: "gemini_unsure", source: "gemini", fix_stage: "extraction" }]),
      productionItem("s", [{ code: "pid_unresolved", source: "system", fix_stage: "analysis" }]),
      productionItem("b", [
        { code: "pid_unresolved", source: "system", fix_stage: "analysis" },
        { code: "gemini_unsure", source: "gemini", fix_stage: "extraction" },
        { code: "no_such_code", source: null, fix_stage: null },
      ]),
      productionItem("n", [{ code: "no_such_code", source: null, fix_stage: null }]),
    ],
    total: 4,
    item_total: 4,
  }));
  view();
  await screen.findByText("Supplier g");
  expect(screen.getByText("Source")).toBeTruthy();
  const rowOf = (name: string) => screen.getByText(name).closest("tr") as HTMLElement;
  const cells = (name: string) => Array.from(rowOf(name).querySelectorAll("td")).map((td) => td.textContent);
  expect(cells("Supplier g")).toEqual(expect.arrayContaining(["Gemini", "Gemini reported it is unsure"]));
  expect(cells("Supplier s")).toEqual(expect.arrayContaining(["System", "Product not identified"]));
  expect(cells("Supplier b")).toEqual(expect.arrayContaining([
    "Gemini, System",
    "Product not identified, Gemini reported it is unsure, Unregistered reason (no_such_code)",
  ]));
  expect(cells("Supplier n")).toEqual(expect.arrayContaining(["—", "Unregistered reason (no_such_code)"]));
});
