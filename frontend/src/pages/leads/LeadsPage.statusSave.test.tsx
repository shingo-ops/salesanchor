/**
 * ADR-1091 §4-2: リード一覧の編集の保存で、段階（status）は選び直したときだけ送る試験。
 * 開いている間に自動で既存顧客になった人を、開いた時点の古い段階で戻さないため。
 * 新規作成の選択肢に「既存顧客」が無いことも見る。試験の題は英語（lint の決まり local/no-japanese-literal）。
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import ja from "../../locales/ja.json";
import LeadsPage from "./LeadsPage";
import { api } from "../../lib/api";
import { queryClient } from "../../lib/query/apiQuery";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock("../../api/closeReasons", () => ({ getCloseReasons: vi.fn(async () => []), closeReasonsPath: () => "/close-reasons?type=lost" }));
vi.mock("../../hooks/useSSE", () => ({ useSSE: vi.fn() }));
vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({ hasPermission: () => true }),
}));

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

afterEach(() => {
  cleanup();
  queryClient.clear();
  vi.mocked(api.patch).mockReset();
});

const lead = {
  id: 7,
  customer_name: "customer-7",
  company_name: null,
  email: null,
  phone: null,
  status: "negotiating",
  type: null,
  notes: null,
  country: null,
  temperature: null,
  prospect_rank: null,
};

async function openDrawer() {
  vi.mocked(api.get).mockImplementation(async (url: string) =>
    url.startsWith("/close-reasons") ? [] : [lead],
  );
  vi.mocked(api.patch).mockResolvedValue({});
  render(
    <MemoryRouter>
      <LeadsPage />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.getAllByText("customer-7").length).toBeGreaterThan(0));
  fireEvent.click(screen.getAllByText("customer-7")[0]);
  await waitFor(() => expect(screen.getByDisplayValue("customer-7")).toBeTruthy());
}

function saveButton() {
  return screen.getAllByRole("button").find((b) => b.getAttribute("type") === "submit") as HTMLElement;
}

describe("LeadsPage edit drawer status save (ADR-1091)", () => {
  it("does not send status when the stage was not re-selected", async () => {
    await openDrawer();
    fireEvent.change(screen.getByDisplayValue("customer-7"), { target: { value: "customer-7b" } });
    fireEvent.click(saveButton());
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    const [path, payload] = vi.mocked(api.patch).mock.calls[0] as [string, Record<string, unknown>];
    expect(path).toBe("/leads/7");
    expect(payload.customer_name).toBe("customer-7b");
    expect("status" in payload).toBe(false);
  });

  it("sends status when the stage was re-selected", async () => {
    await openDrawer();
    const statusSelect = screen.getByDisplayValue(ja.leads.statusCode.negotiating) as HTMLSelectElement;
    fireEvent.change(statusSelect, { target: { value: "follow_up_short" } });
    fireEvent.click(saveButton());
    await waitFor(() => expect(api.patch).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(payload.status).toBe("follow_up_short");
  });

  it("does not offer existing_customer in the create form", async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) =>
      url.startsWith("/close-reasons") ? [] : [lead],
    );
    render(
      <MemoryRouter>
        <LeadsPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getAllByText("customer-7").length).toBeGreaterThan(0));
    fireEvent.click(screen.getByText(ja.leads.newLead));
    await screen.findAllByRole("dialog");
    // 編集のドロワーではなく、新規作成のダイアログを探す
    const dialog = screen.getAllByRole("dialog").find((d) => d.getAttribute("data-testid") !== "supplier-drawer") as HTMLElement;
    const options = within(dialog).getAllByRole("option").map((o) => (o as HTMLOptionElement).value);
    expect(options).toContain("lead");
    expect(options).not.toContain("existing_customer");
  });
});
