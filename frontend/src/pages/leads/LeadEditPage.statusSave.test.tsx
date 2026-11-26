/**
 * ADR-1091 §4-2: リードの編集画面の保存で、段階（status）は選び直したときだけ送る試験。
 * 直し始めた後に取り直しで段階が existing_customer に変わっても、選び直さない保存の PATCH に status を入れない。
 * 試験の題は英語（lint の決まり local/no-japanese-literal）。
 */
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import ja from "../../locales/ja.json";
import LeadEditPage from "./LeadEditPage";
import { api } from "../../lib/api";
import { queryClient } from "../../lib/query/apiQuery";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock("../../api/closeReasons", () => ({ getCloseReasons: vi.fn(async () => []), closeReasonsPath: () => "/close-reasons?type=lost" }));
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "uid-A" }, loading: false }),
}));
vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({ hasPermission: () => true }),
}));
vi.mock("../../components/CountryCombobox", () => ({
  CountryCombobox: ({ id }: { id: string }) => <div data-testid={id} />,
}));

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

afterEach(() => {
  cleanup();
  queryClient.clear();
  vi.mocked(api.patch).mockReset();
});

const baseLead = {
  id: 5,
  customer_name: "edit-5",
  company_name: null,
  email: null,
  phone: null,
  channel_type: null,
  initiative: null,
  type: null,
  status: "negotiating",
  temperature: null,
  estimated_scale: null,
  customer_type: null,
  response_speed: null,
  monthly_forecast: null,
  notes: null,
  country: null,
};

function mountPage() {
  vi.mocked(api.get).mockImplementation(async (url: string) =>
    url.startsWith("/close-reasons") ? [] : url === "/leads/5" ? baseLead : [],
  );
  vi.mocked(api.patch).mockResolvedValue({});
  render(
    <MemoryRouter initialEntries={["/crm/leads/5/edit"]}>
      <Routes>
        <Route path="/crm/leads/:id/edit" element={<LeadEditPage />} />
        <Route path="/crm/leads" element={<div>list</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function submit() {
  const btn = screen.getAllByRole("button").find((b) => b.getAttribute("type") === "submit") as HTMLElement;
  fireEvent.click(btn);
}

describe("LeadEditPage status save (ADR-1091)", () => {
  it("does not send status when the stage was not re-selected", async () => {
    mountPage();
    await waitFor(() => expect(screen.getByDisplayValue("edit-5")).toBeTruthy());
    fireEvent.change(screen.getByDisplayValue("edit-5"), { target: { value: "edit-5b" } });
    submit();
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(payload.customer_name).toBe("edit-5b");
    expect("status" in payload).toBe(false);
  });

  it("sends status when the stage was re-selected", async () => {
    mountPage();
    await waitFor(() => expect(screen.getByDisplayValue("edit-5")).toBeTruthy());
    fireEvent.change(screen.getByDisplayValue(ja.leads.statusCode.negotiating), { target: { value: "lost" } });
    submit();
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(payload.status).toBe("lost");
  });

  it("does not send status when a refetch changes the stage to existing_customer after the user started editing", async () => {
    mountPage();
    await waitFor(() => expect(screen.getByDisplayValue("edit-5")).toBeTruthy());
    fireEvent.change(screen.getByDisplayValue("edit-5"), { target: { value: "edit-5c" } });
    // 直し始めた後に取り直しで段階が変わる
    vi.mocked(api.get).mockImplementation(async (url: string) =>
      url.startsWith("/close-reasons") ? [] : url === "/leads/5" ? { ...baseLead, status: "existing_customer" } : [],
    );
    await act(async () => {
      await queryClient.invalidateQueries();
    });
    submit();
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(payload.customer_name).toBe("edit-5c");
    expect("status" in payload).toBe(false);
  });
});
