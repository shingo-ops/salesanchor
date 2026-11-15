import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import DutyRulesPage from "./DutyRulesPage";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn(), delete: vi.fn() },
  ApiError: class extends Error {
    status: number;
    responseDetail: unknown;
    constructor(message: string, status: number, responseDetail: unknown) {
      super(message);
      this.status = status;
      this.responseDetail = responseDetail;
    }
  },
}));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }));
// 国の選択は自分で /countries を取りに行く部品なので、ここでは金型の文字の欄（TextFieldControl）に差し替える
// （生の input は UI の決まりの点検 check-ui-governance が止める。ADR-144）
vi.mock("../../components/CountryCombobox", async () => {
  const { TextFieldControl } = await vi.importActual<typeof import("../../components/TextField")>(
    "../../components/TextField",
  );
  return {
    CountryCombobox: ({ id, value, onChange }: { id: string; value: string; onChange: (v: string) => void }) => (
      <TextFieldControl id={id} value={value} onChange={(e) => onChange(e.target.value)} />
    ),
  };
});

const RULE = {
  id: 7,
  destination_country_code: "US",
  carrier: "fedex",
  label: "US DDP FedEx",
  effective_from: "2026-01-01",
  effective_to: null,
  source_url: "https://www.fedex.com/en-us/billing/duty-tax.html",
  note: null,
  is_active: true,
  components: [
    { id: 1, sort_order: 0, label: "Duty", base: "subtotal", rate_pct: "15.0000",
      min_amount: null, max_amount: null, amount_currency: null },
  ],
};
const OPTIONS = {
  duty_incoterms: "DDP",
  currencies: ["JPY", "USD"],
  bases: ["subtotal", "subtotal_shipping", "subtotal_shipping_prior"],
};

const mockGets = (options: object, rules: object[]) => {
  vi.mocked(api.get).mockImplementation(async (path: string) =>
    path === "/admin/duty-rules/options" ? options : rules,
  );
};
const mockCanEdit = (canEdit: boolean) =>
  vi.mocked(usePermissions).mockReturnValue({
    loading: false,
    hasPermission: (p: string) => (p === "tenant.profile.edit" ? canEdit : true),
    hasAny: () => true,
  } as unknown as ReturnType<typeof usePermissions>);
const view = () => render(<MemoryRouter><DutyRulesPage /></MemoryRouter>);
const callsTo = (path: string) => vi.mocked(api.get).mock.calls.filter((c) => c[0] === path).length;

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  mockCanEdit(true);
  mockGets(OPTIONS, [RULE]);
});
afterEach(() => { cleanup(); queryClient.clear(); });

it("shows the current terms read-only with a link to the tenant policy page and lists the rules", async () => {
  view();
  await screen.findByText("US DDP FedEx");
  expect(screen.getByText("Current duty terms: DDP")).toBeTruthy();
  expect(screen.getByText("The terms are DDP, so these amounts are added to invoices.")).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "Change the terms on the Tenant Policy page" }).getAttribute("href"),
  ).toBe("/management-center/tenant-policy");
  expect(screen.getByText("fedex")).toBeTruthy();
  expect(screen.getByText("2026-01-01 - No end")).toBeTruthy();
  expect(screen.getByText("Duty: 15.0000% of Subtotal")).toBeTruthy();
  expect(screen.getByText(RULE.source_url)).toBeTruthy();
});

it("says duty is not billed now when the terms are not DDP", async () => {
  mockGets({ ...OPTIONS, duty_incoterms: "DAP" }, [{ ...RULE, carrier: null }]);
  view();
  await screen.findByText("Current duty terms: DAP");
  expect(
    screen.getByText("Duty is not billed now. These amounts are added to invoices only when the terms are DDP."),
  ).toBeTruthy();
  expect(screen.getByText("Any carrier")).toBeTruthy();
});

it("hides add, edit and delete for a view-only user", async () => {
  mockCanEdit(false);
  view();
  await screen.findByText("US DDP FedEx");
  expect(screen.queryByRole("button", { name: "Add rule" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Edit US DDP FedEx" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Delete US DDP FedEx" })).toBeNull();
});

it("adds a rule with an empty carrier sent as null and reloads the list", async () => {
  mockGets(OPTIONS, []);
  vi.mocked(api.post).mockResolvedValue(RULE);
  view();
  fireEvent.click(await screen.findByRole("button", { name: "Add rule" }));
  const dialog = await screen.findByRole("dialog");
  const save = within(dialog).getByRole("button", { name: "Save" }) as HTMLButtonElement;
  expect(save.disabled).toBe(true);
  fireEvent.change(within(dialog).getByLabelText(/^Destination country/), { target: { value: "US" } });
  fireEvent.change(within(dialog).getByLabelText(/^Name on invoice/), { target: { value: "US DDP" } });
  fireEvent.change(within(dialog).getByLabelText(/^Start date/), { target: { value: "2026-01-01" } });
  fireEvent.change(within(dialog).getByLabelText(/^Source URL/), { target: { value: RULE.source_url } });
  fireEvent.change(within(dialog).getByLabelText(/^Component 1 name/), { target: { value: "Duty" } });
  fireEvent.change(within(dialog).getByLabelText(/^Rate \(%\)/), { target: { value: "15" } });
  expect(save.disabled).toBe(false);
  const listCalls = callsTo("/admin/duty-rules");
  fireEvent.click(save);
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  expect(vi.mocked(api.post).mock.calls[0][0]).toBe("/admin/duty-rules");
  expect(vi.mocked(api.post).mock.calls[0][1]).toEqual({
    destination_country_code: "US",
    carrier: null,
    label: "US DDP",
    effective_from: "2026-01-01",
    effective_to: null,
    source_url: RULE.source_url,
    note: null,
    is_active: true,
    components: [
      { label: "Duty", base: "subtotal", rate_pct: "15", min_amount: null, max_amount: null, amount_currency: null },
    ],
  });
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(callsTo("/admin/duty-rules")).toBeGreaterThan(listCalls));
});

it("keeps the form open and explains an overlap when the server answers 409", async () => {
  vi.mocked(api.put).mockRejectedValue(new ApiError("conflict", 409, { code: "duty_rule_overlap", rule_ids: [8] }));
  view();
  fireEvent.click(await screen.findByRole("button", { name: "Edit US DDP FedEx" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
  await within(dialog).findByText(
    "Another rule for the same country and carrier overlaps this period. Check the period or the carrier.",
  );
  expect(vi.mocked(api.put).mock.calls[0][0]).toBe("/admin/duty-rules/7");
  expect(screen.getByRole("dialog")).toBeTruthy();
});

it("deletes a rule after confirmation", async () => {
  vi.mocked(api.delete).mockResolvedValue(undefined);
  view();
  fireEvent.click(await screen.findByRole("button", { name: "Delete US DDP FedEx" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "Delete" }));
  await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/admin/duty-rules/7"));
});
