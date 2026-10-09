import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
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

// AY-2g: the standalone product master page (which had its own admin check) was
// removed, so the admin check on AnalysisRulesPage is what keeps non-admins out.
it("shows only the super-admin-only message and loads nothing for a non-admin on ?section=product-master", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false });
  render(
    <MemoryRouter initialEntries={["/super-admin/analysis-rules?section=product-master"]}>
      <AnalysisRulesPage />
    </MemoryRouter>,
  );
  expect(screen.getByText(i18n.t("superAdmin.supplierQuality.superAdminOnly"))).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Export update CSV" })).toBeNull();
  expect(api.get).not.toHaveBeenCalled();
});
