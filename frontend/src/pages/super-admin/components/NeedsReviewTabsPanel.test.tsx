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

const view = () => render(<MemoryRouter><NeedsReviewTabsPanel /></MemoryRouter>);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockImplementation(() => Promise.resolve(productionResponse));
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

it("shows only the production and posts tabs", async () => {
  view();
  await waitFor(() => expect(api.get).toHaveBeenCalled());
  expect(screen.getAllByRole("tab")).toHaveLength(2);
  expect(screen.queryByText("Shadow run review")).toBeNull();
  expect(screen.queryByText("Bottlenecks")).toBeNull();
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
