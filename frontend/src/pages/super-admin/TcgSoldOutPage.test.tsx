import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import { ROUTE_TITLE_KEYS } from "../../config/routeTitles";
import type { SoldOutItem } from "../../features/tcg-sold-out/soldOutApi";
import TcgSoldOutPage from "./TcgSoldOutPage";
vi.mock("../../lib/api", () => ({ api: { get: vi.fn() }, ApiError: class extends Error {} }));
vi.mock("../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));
const item: SoldOutItem = {
  analysis_result_id: "a1", extraction_item_id: "i1", source_message_id: "s1", supplier_id: null, product_id: null,
  provider: "Supplier", product_title: "", raw_product_name: "Shared", raw_quantity: "", raw_unit: "BOX", raw_price: "1200",
  raw_state: "sold out", raw_memo: "Possibly more tomorrow", raw_text: "Header\n<script>private</script>\nSlot 2 available",
  status: "Sold out", source_is_active: false, line_posted_at: null, line_start: 2, line_end: 2,
};
const response = { total: 51, offset: 0, limit: 50, as_of: "2026-09-14T00:00:00Z", items: [item] };
const view = () => render(<MemoryRouter><TcgSoldOutPage /></MemoryRouter>);
const params = () => new URL(String(vi.mocked(api.get).mock.calls.slice(-1)[0]?.[0]), "http://test").searchParams;
beforeEach(async () => {
  vi.resetAllMocks(); await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
  vi.mocked(api.get).mockResolvedValue(response);
});
afterEach(() => cleanup());
it("denies direct URL and never fetches while unauthorized or permission is pending", () => {
  for (const loading of [true, false]) {
    vi.mocked(useSuperAdmin).mockReturnValue({ loading, isSuperAdmin: false }); view();
    expect(api.get).not.toHaveBeenCalled(); expect(screen.queryByRole("button", { name: "Search" })).toBeNull(); cleanup();
  }
});
it("shows saved decisions, blank raw quantity, historical source, absent date and safely highlighted text", async () => {
  view(); await screen.findByText("Analysis results: 51");
  expect(screen.getByText(/does not show current stock/)).toBeTruthy();
  expect(screen.getByText("Posting date not recorded")).toBeTruthy();
  const cells = within(screen.getAllByRole("row")[1]).getAllByRole("cell");
  expect(cells[3].textContent).toBe("BOX");
  expect(cells[0].textContent).toContain("(original name)");
  expect(cells[6].textContent).toBe("Past sources");
  const detail = document.querySelector("details")!;
  expect(detail.open).toBe(false);
  fireEvent.click(screen.getByText("View source", { selector: "summary" }));
  expect(document.querySelector("mark")?.textContent).toBe("<script>private</script>");
  expect(detail.querySelector("script")).toBeNull();
  expect(screen.getByText("Possibly more tomorrow")).toBeTruthy();
});
it("confirms search once, treats wildcards literally, resets paging and filters history", async () => {
  view(); await screen.findByText("Analysis results: 51");
  expect(params().get("source_scope")).toBe("all");
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => expect(params().get("offset")).toBe("50"));
  const calls = vi.mocked(api.get).mock.calls.length;
  fireEvent.change(screen.getByLabelText("Search product or supplier name"), { target: { value: "  %_\\  " } });
  expect(vi.mocked(api.get).mock.calls.length).toBe(calls);
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(params().get("q")).toBe("%_\\"));
  expect(params().get("offset")).toBe("0");
  fireEvent.change(screen.getByLabelText("Source scope"), { target: { value: "history" } });
  await waitFor(() => expect(params().get("source_scope")).toBe("history"));
});
it("rejects stale responses and shows explicit retrieval failure without old counts", async () => {
  let finish!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  view();
  fireEvent.change(screen.getByLabelText("Search product or supplier name"), { target: { value: "new" } });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  await screen.findByText("Analysis results: 51");
  await act(async () => finish({ ...response, total: 999 }));
  expect(screen.queryByText("Analysis results: 999")).toBeNull();
  vi.mocked(api.get).mockRejectedValue(new Error("PRIVATE SOURCE"));
  fireEvent.click(screen.getByRole("button", { name: "Reload" }));
  expect((await screen.findByRole("alert")).textContent).toBe("Results could not be retrieved. Please reload.");
  expect(screen.queryByText("Analysis results: 51")).toBeNull();
  expect(screen.queryByText("PRIVATE SOURCE")).toBeNull();
});
it("preserves separate same-name rows, displays null source and invalid span without highlight", async () => {
  vi.mocked(api.get).mockResolvedValue({ ...response, total: 2, items: [
    { ...item, line_start: 0, line_end: 99, source_is_active: null },
    { ...item, analysis_result_id: "a2", raw_unit: "case", line_start: null, line_end: null },
  ] });
  view(); await screen.findByText("Analysis results: 2");
  expect(screen.getAllByRole("row")).toHaveLength(3);
  expect(screen.getByText("Unknown source state")).toBeTruthy();
  expect(document.querySelector("mark")).toBeNull();
  expect(screen.getAllByText(/Invalid source position/)).toHaveLength(2);
});
it("keeps Japanese and English navigation and title aligned and formats date in JST", async () => {
  expect(ROUTE_TITLE_KEYS["/super-admin/tcg-sold-out"]).toBe("nav.superAdminTcgSoldOut");
  vi.mocked(api.get).mockResolvedValue({ ...response, items: [{ ...item, line_posted_at: "2026-09-13T15:30:00Z" }] });
  view(); await screen.findByText("Analysis results: 51");
  expect(screen.getByRole("heading", { name: "Sold-out rules" })).toBeTruthy();
  expect(screen.getByText(/14\/09\/2026, 00:30/)).toBeTruthy();
  await act(async () => { await i18n.changeLanguage("ja"); });
  expect(screen.getByRole("heading", { name: i18n.t("nav.superAdminTcgSoldOut") })).toBeTruthy();
});
it("shows zero only after a successful response and allows returning from an empty out-of-range page", async () => {
  vi.mocked(api.get).mockResolvedValueOnce(response).mockResolvedValue({ ...response, total: 3, offset: 50, items: [] });
  view(); await screen.findByText("Analysis results: 51");
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("Analysis results: 3");
  expect(screen.getByText("No matching analysis results.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "First page" }));
  await waitFor(() => expect(params().get("offset")).toBe("0"));
});

vi.mock("../../contexts/AuthContext", () => ({ useAuth: () => ({ user: { email: "fixture@example.test" }, signOut: vi.fn() }) }));
vi.mock("../../contexts/LocaleContext", () => ({ useLocale: () => ({ locale: "en", changeLanguage: vi.fn() }) }));
vi.mock("../../contexts/ThemeContext", () => ({ useTheme: () => ({ theme: "light", changeTheme: vi.fn() }) }));
vi.mock("../../contexts/UiPrefsContext", () => ({ useUiPrefs: () => ({ prefs: { show_chat_menu: false, show_sales_menu: false }, loading: false, staffName: "Fixture" }) }));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: () => ({ hasPermission: () => false, hasAny: () => false, loading: false }) }));
vi.mock("../../hooks/useSSE", () => ({ useSSE: () => undefined }));
vi.mock("../../lib/messages", () => ({ listConversations: async () => ({ conversations: [] }) }));
it("shows analysis management menu item only for SaaS administrators", async () => {
  const { default: DesktopShell } = await import("../../components/DesktopShell");
  const shell = () => render(<MemoryRouter><DesktopShell /></MemoryRouter>);
  shell();
  fireEvent.click(screen.getByRole("button", { name: i18n.t("nav.saasAdmin") }));
  const analysisLink = screen.getByRole("link", { name: "Analysis Management" });
  expect(analysisLink.getAttribute("href")).toBe("/super-admin/analysis-rules");
  cleanup(); vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false }); shell();
  expect(screen.queryByRole("button", { name: i18n.t("nav.saasAdmin") })).toBeNull();
  expect(screen.queryByRole("link", { name: "Analysis Management" })).toBeNull();
});

