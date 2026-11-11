import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Navigate, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useSuperAdmin } from "../../../hooks/useSuperAdmin";
import i18n from "../../../i18n";
import ComingSoonPage from "../../coming-soon/ComingSoonPage";
import SettingsHubPage from "./SettingsHubPage";
import { SETTINGS_MASTER_ITEMS, SETTINGS_MONEY_ITEMS } from "./settingsNav";

vi.mock("../../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

function renderHub(entry: string) {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/super-admin/settings" element={<SettingsHubPage />}>
          <Route index element={<Navigate to="fx-rate" replace />} />
          <Route path="fx-rate" element={<div data-testid="fx-body" />} />
          <Route
            path="tax-rates"
            element={<ComingSoonPage title={i18n.t("nav.superAdminTaxRates")} description={i18n.t("superAdmin.settings.comingSoon")} />}
          />
          <Route
            path="sa-products"
            element={<ComingSoonPage title={i18n.t("nav.superAdminSaProducts")} description={i18n.t("superAdmin.settings.comingSoon")} />}
          />
          <Route path="masters/:key" element={<div data-testid="master-body" />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
});
afterEach(() => cleanup());

// K2: groups, 3 money items + 11 masters, and the index opens the FX screen.
it("shows the money group (3) and master group (11) in the small menu and opens FX first", () => {
  renderHub("/super-admin/settings");
  expect(screen.getByText(i18n.t("superAdmin.settings.groupMoney"))).toBeTruthy();
  expect(screen.getByText(i18n.t("analysisRules.sidebar.groupMasterManagement"))).toBeTruthy();
  expect(SETTINGS_MONEY_ITEMS).toHaveLength(3);
  expect(SETTINGS_MASTER_ITEMS).toHaveLength(11);
  for (const item of [...SETTINGS_MONEY_ITEMS, ...SETTINGS_MASTER_ITEMS]) {
    expect(screen.getByRole("link", { name: i18n.t(item.labelKey) })).toBeTruthy();
  }
  expect(screen.getByTestId("fx-body")).toBeTruthy();
  expect(screen.getByRole("link", { name: i18n.t("nav.superAdminFxRate") }).className).toContain("comp-subnav__item--active");
});

// K3: tax rates and products & plans are placeholders.
it.each(["tax-rates", "sa-products"])("shows the coming soon text on %s", (key) => {
  renderHub(`/super-admin/settings/${key}`);
  expect(screen.getAllByText(i18n.t("superAdmin.settings.comingSoon")).length).toBeGreaterThan(0);
});

it("marks the opened master as active in the small menu", () => {
  renderHub("/super-admin/settings/masters/note-master");
  expect(screen.getByTestId("master-body")).toBeTruthy();
  expect(screen.getByRole("link", { name: i18n.t("analysisRules.sidebar.noteMaster") }).className).toContain("comp-subnav__item--active");
});

// K9: a non super admin gets no body and no menu.
it("shows access denied and renders no outlet for a non super admin", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false });
  renderHub("/super-admin/settings/fx-rate");
  expect(screen.getByText(i18n.t("superAdmin.accessDenied"))).toBeTruthy();
  expect(screen.queryByTestId("fx-body")).toBeNull();
  expect(screen.queryByRole("link", { name: i18n.t("nav.superAdminFxRate") })).toBeNull();
});
