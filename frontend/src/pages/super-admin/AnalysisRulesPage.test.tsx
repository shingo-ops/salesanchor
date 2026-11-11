import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import AnalysisRulesPage from "./AnalysisRulesPage";

vi.mock("../../lib/api", () => ({ api: { get: vi.fn(), getBlob: vi.fn() } }));
vi.mock("../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
});
afterEach(() => cleanup());

function Where() {
  const loc = useLocation();
  return <output data-testid="where">{loc.pathname + loc.search}</output>;
}

// K6: the masters moved to the global settings hub, so the old ?section=<master> URL moves there.
it.each([
  "product-master",
  "supplier-master",
  "weight-classes-master",
])("moves ?section=%s to the global settings master screen", (key) => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  render(
    <MemoryRouter initialEntries={[`/super-admin/analysis-rules?section=${key}`]}>
      <Routes>
        <Route path="/super-admin/analysis-rules" element={<AnalysisRulesPage />} />
        <Route path="/super-admin/settings/masters/:key" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByTestId("where").textContent).toBe(`/super-admin/settings/masters/${key}`);
  expect(api.get).not.toHaveBeenCalled();
});

// K5: the master group is gone from the sidebar; the rule screens for status and unit stay.
it("has no master management group in the sidebar and keeps the condition and unit rules", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockResolvedValue({});
  render(
    <MemoryRouter initialEntries={["/super-admin/analysis-rules?section=conditions-master"]}>
      <AnalysisRulesPage />
    </MemoryRouter>,
  );
  expect(screen.queryByText(i18n.t("analysisRules.sidebar.groupMasterManagement"))).toBeNull();
  for (const key of [
    "product-master", "product-categories-master", "product-kinds-master", "type-master",
    "product-lines-master", "product-formats-master", "supplier-master", "note-master",
    "quantity-units-master", "condition-defs-master", "weight-classes-master",
  ]) {
    expect(screen.queryByTestId(`analysis-subnav-${key}`)).toBeNull();
  }
  expect(screen.getByTestId("analysis-subnav-conditions-master")).toBeTruthy();
  expect(screen.getByTestId("analysis-subnav-unit-master")).toBeTruthy();
});

it("shows only the super-admin-only message and loads nothing for a non-admin", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false });
  render(
    <MemoryRouter initialEntries={["/super-admin/analysis-rules"]}>
      <AnalysisRulesPage />
    </MemoryRouter>,
  );
  expect(screen.getByText(i18n.t("superAdmin.supplierQuality.superAdminOnly"))).toBeTruthy();
  expect(api.get).not.toHaveBeenCalled();
});

// AY-2i: the sold-out results screen now lives in the LINE analysis sidebar.
it("selects the sold-out results menu item and renders its panel for a super admin on ?section=sold-out-results", async () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockResolvedValue({ total: 0, offset: 0, limit: 50, as_of: "2026-09-14T00:00:00Z", items: [] });
  render(
    <MemoryRouter initialEntries={["/super-admin/analysis-rules?section=sold-out-results"]}>
      <AnalysisRulesPage />
    </MemoryRouter>,
  );
  expect(screen.getByTestId("analysis-subnav-sold-out-results").className).toContain("active");
  expect(await screen.findByText("No matching analysis results.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Search" })).toBeTruthy();
});
