import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import i18n from "../../../i18n";
import SettingsMasterPage from "./SettingsMasterPage";
import { SETTINGS_MASTER_ITEMS, isSettingsMasterKey, settingsMasterPath } from "./settingsNav";

// K4: each key shows its own panel. The panels are replaced by markers so only the key → panel table is checked.
vi.mock("../components/ProductMasterPanel", () => ({ ProductMasterPanel: () => <div data-testid="panel-product-master" /> }));
vi.mock("../components/ProductCategoriesMasterPanel", () => ({ ProductCategoriesMasterPanel: () => <div data-testid="panel-product-categories-master" /> }));
vi.mock("../components/ProductKindsMasterPanel", () => ({ ProductKindsMasterPanel: () => <div data-testid="panel-product-kinds-master" /> }));
vi.mock("../components/TypeMasterPanel", () => ({ TypeMasterPanel: () => <div data-testid="panel-type-master" /> }));
vi.mock("../components/ProductLinesMasterPanel", () => ({ ProductLinesMasterPanel: () => <div data-testid="panel-product-lines-master" /> }));
vi.mock("../components/ProductFormatsMasterPanel", () => ({ ProductFormatsMasterPanel: () => <div data-testid="panel-product-formats-master" /> }));
vi.mock("../components/SupplierMasterPanel", () => ({ SupplierMasterPanel: () => <div data-testid="panel-supplier-master" /> }));
vi.mock("../components/NoteMasterPanel", () => ({ NoteMasterPanel: () => <div data-testid="panel-note-master" /> }));
vi.mock("../components/QuantityUnitsMasterPanel", () => ({ QuantityUnitsMasterPanel: () => <div data-testid="panel-quantity-units-master" /> }));
vi.mock("../components/ConditionDefsMasterPanel", () => ({ ConditionDefsMasterPanel: () => <div data-testid="panel-condition-defs-master" /> }));
vi.mock("../components/WeightClassesMasterPanel", () => ({ WeightClassesMasterPanel: () => <div data-testid="panel-weight-classes-master" /> }));

function renderAt(entry: string) {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/super-admin/settings" element={<div data-testid="settings-home" />} />
        <Route path="/super-admin/settings/masters/:key" element={<SettingsMasterPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => cleanup());

it.each(SETTINGS_MASTER_ITEMS.map(i => [i.key, i.labelKey] as const))("shows the %s panel with its title", (key, labelKey) => {
  renderAt(settingsMasterPath(key));
  expect(screen.getByTestId(`panel-${key}`)).toBeTruthy();
  expect(screen.getByRole("heading", { name: i18n.t(labelKey) })).toBeTruthy();
});

it("goes back to the settings home for an unknown key", () => {
  renderAt("/super-admin/settings/masters/unit-master");
  expect(screen.getByTestId("settings-home")).toBeTruthy();
});

it("settingsNav recognizes exactly the 11 master keys", () => {
  expect(SETTINGS_MASTER_ITEMS).toHaveLength(11);
  expect(isSettingsMasterKey("product-master")).toBe(true);
  expect(isSettingsMasterKey("unit-master")).toBe(false);
  expect(isSettingsMasterKey("conditions-master")).toBe(false);
  expect(isSettingsMasterKey(null)).toBe(false);
});
