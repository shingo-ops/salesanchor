import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import TaxRatesPage from "./TaxRatesPage";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } };
});
vi.mock("../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

const LIST = {
  today: "2026-11-12",
  rates: [
    { id: 2, rate_percent: "12.00", effective_from: "2027-04-01", created_at: "2026-11-12T00:00:00Z" },
    { id: 1, rate_percent: "10.00", effective_from: "2019-10-01", created_at: "2026-11-12T00:00:00Z" },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/super-admin/settings/tax-rates"]}>
      <Routes>
        <Route path="/super-admin/settings/tax-rates" element={<TaxRatesPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
});

afterEach(() => {
  cleanup();
});

it("shows access denied for a non super admin and does not call the API", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false });
  renderPage();
  expect((screen.getByRole("alert")).textContent).toContain(i18n.t("superAdmin.accessDenied"));
  expect(api.get).not.toHaveBeenCalled();
});

it("lists rates newest first and shows delete only for a rate that has not started", async () => {
  vi.mocked(api.get).mockResolvedValue(LIST);
  renderPage();
  expect((await screen.findByTestId("tax-rate-row-2")).textContent).toContain("12.00%");
  expect((screen.getByTestId("tax-rate-row-1")).textContent).toContain("10.00%");
  expect(screen.getByTestId("tax-rate-delete-2")).toBeTruthy();
  expect(screen.queryByTestId("tax-rate-delete-1")).toBeNull();
  expect(api.get).toHaveBeenCalledWith("/super-admin/tax-rates");
});

it("shows the empty state when there is no rate", async () => {
  vi.mocked(api.get).mockResolvedValue({ today: "2026-11-12", rates: [] });
  renderPage();
  expect(await screen.findByText(i18n.t("superAdmin.taxRates.noData"))).toBeTruthy();
});

it("sends the rate as a string and reloads after adding", async () => {
  vi.mocked(api.get).mockResolvedValue(LIST);
  vi.mocked(api.post).mockResolvedValue({ id: 3, rate_percent: "10.00", effective_from: "2028-01-01", created_at: "" });
  renderPage();
  await screen.findByTestId("tax-rate-row-2");
  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.taxRates.ratePercent"), { exact: false }), { target: { value: "10.00" } });
  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.taxRates.effectiveFrom"), { exact: false }), { target: { value: "2028-01-01" } });
  fireEvent.submit(screen.getByTestId("tax-rate-form"));
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith("/super-admin/tax-rates", { rate_percent: "10.00", effective_from: "2028-01-01" }),
  );
  expect((await screen.findByTestId("tax-rate-success")).textContent).toContain(i18n.t("superAdmin.taxRates.addSuccess"));
  expect(api.get).toHaveBeenCalledTimes(2);
});

it("shows the date rule message when the API answers effective_from_invalid", async () => {
  vi.mocked(api.get).mockResolvedValue(LIST);
  vi.mocked(api.post).mockRejectedValue(new ApiError("x", 422, "tax_rate.effective_from_invalid"));
  renderPage();
  await screen.findByTestId("tax-rate-row-2");
  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.taxRates.ratePercent"), { exact: false }), { target: { value: "10" } });
  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.taxRates.effectiveFrom"), { exact: false }), { target: { value: "2026-11-12" } });
  fireEvent.submit(screen.getByTestId("tax-rate-form"));
  expect((await screen.findByTestId("tax-rate-error")).textContent).toContain(i18n.t("superAdmin.taxRates.errorDateInvalid"));
});

it("deletes a future rate after confirmation", async () => {
  vi.mocked(api.get).mockResolvedValue(LIST);
  vi.mocked(api.delete).mockResolvedValue(undefined);
  renderPage();
  fireEvent.click(await screen.findByTestId("tax-rate-delete-2"));
  const confirmButtons = await screen.findAllByRole("button", { name: i18n.t("superAdmin.taxRates.deleteBtn") });
  fireEvent.click(confirmButtons[confirmButtons.length - 1]);
  await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/super-admin/tax-rates/2"));
  expect((await screen.findByTestId("tax-rate-success")).textContent).toContain(i18n.t("superAdmin.taxRates.deleteSuccess"));
});
