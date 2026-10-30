import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import ja from "../../locales/ja.json";
import LeadsPage from "./LeadsPage";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock("../../api/closeReasons", () => ({ getCloseReasons: vi.fn(async () => []) }));
vi.mock("../../hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({ hasPermission: () => true }),
}));

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

afterEach(() => {
  cleanup();
});

const row = (id: number, temperature: string | null) => ({
  id,
  customer_name: `customer-${id}`,
  company_name: null,
  status: "new",
  temperature,
  prospect_rank: null,
});

describe("LeadsPage temperature column", () => {
  it("shows the translated temperature for a stored Hot value and a dash for null", async () => {
    vi.mocked(api.get).mockResolvedValue([row(1, "Hot"), row(2, null)]);
    render(
      <MemoryRouter>
        <LeadsPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getAllByText("customer-1").length).toBeGreaterThan(0));
    expect(screen.getAllByText(ja.leads.temperature_hot).length).toBeGreaterThan(0);
    expect(screen.queryByText("Hot")).toBeNull();
    expect(screen.getAllByText("-").length).toBeGreaterThan(0);
  });
});
