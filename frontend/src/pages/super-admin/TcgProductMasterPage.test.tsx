import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import TcgProductMasterPage from "./TcgProductMasterPage";
vi.mock("../../lib/api", () => ({ api: { get: vi.fn() } }));
vi.mock("../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));
beforeEach(async () => { vi.resetAllMocks(); await i18n.changeLanguage("en"); vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true }); });
afterEach(cleanup);
const view = () => render(<MemoryRouter><TcgProductMasterPage /></MemoryRouter>);
const works = [
  // eslint-disable-next-line local/no-japanese-literal -- DB value: Japanese alternate work name fixture
  { id: "00000000-0000-4000-8000-000000000001", code: "IP001", display_name: "Pokemon", alt_name: " ポケモン " },
  { id: "00000000-0000-4000-8000-000000000002", code: "IP002", display_name: "One Piece", alt_name: " " },
];
const empty = { total: 0, items: [], works };
const lastParams = () => new URL(String(vi.mocked(api.get).mock.calls.slice(-1)[0]?.[0]), "http://test").searchParams;
it("does not request or expose import for non-admin", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false }); view();
  expect(api.get).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "Import CSV" })).toBeNull();
});
it("shows total, pages through results and resets offset on search", async () => {
  vi.mocked(api.get).mockResolvedValue({ total: 51, works, items: [{ code: "PM51", japanese_title: "Fixture", keyword_count: 0 }] }); view();
  await screen.findByText("Products: 51");
  expect(screen.getByText("No search keywords")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "next page" }));
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.slice(-1)[0]?.[0]).toContain("offset=50"));
  fireEvent.change(screen.getByLabelText("Search by name or code"), { target: { value: "A & B" } });
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.slice(-1)[0]?.[0]).toContain("query=A+%26+B&limit=50&offset=0"));
});
it("discards an older response that arrives after a new search", async () => {
  let old!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementationOnce(() => new Promise(resolve => { old = resolve; })).mockResolvedValue(empty); view();
  fireEvent.change(screen.getByLabelText("Search by name or code"), { target: { value: "new" } });
  await screen.findByText("Products: 0"); await act(async () => old({ total: 99, items: [], works }));
  await waitFor(() => expect(screen.queryByText("Products: 99")).toBeNull());
});

it("AC6 combines work and search, resets page and omits work for All", async () => {
  vi.mocked(api.get).mockResolvedValue({ ...empty, total: 51 }); view();
  await screen.findByText("Products: 51");
  expect(lastParams().has("work_id")).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "next page" }));
  await waitFor(() => expect(lastParams().get("offset")).toBe("50"));
  fireEvent.click(screen.getByRole("tab", { name: "Pokemon" }));
  await waitFor(() => expect(lastParams().get("work_id")).toBe(works[0].id));
  expect(lastParams().get("offset")).toBe("0");
  fireEvent.change(screen.getByLabelText("Search by name or code"), { target: { value: "Shared" } });
  await waitFor(() => expect(lastParams().get("query")).toBe("Shared"));
  expect(lastParams().get("work_id")).toBe(works[0].id);
  await screen.findByText("Products: 51");
  fireEvent.click(screen.getByRole("button", { name: "next page" }));
  await waitFor(() => expect(lastParams().get("offset")).toBe("50"));
  expect(lastParams().get("query")).toBe("Shared");
  expect(lastParams().get("work_id")).toBe(works[0].id);
  fireEvent.click(screen.getByRole("tab", { name: "One Piece" }));
  await waitFor(() => expect(lastParams().get("work_id")).toBe(works[1].id));
  expect(lastParams().get("query")).toBe("Shared");
  expect(lastParams().get("offset")).toBe("0");
  fireEvent.click(screen.getByRole("tab", { name: "All" }));
  await waitFor(() => expect(lastParams().has("work_id")).toBe(false));
  expect(lastParams().get("query")).toBe("Shared");
  expect(screen.getByRole("tab", { name: "All" }).getAttribute("aria-selected")).toBe("true");
});

it.each(["success", "failure"] as const)("AC7 ignores late A success after B %s and retries B", async outcome => {
  let resolveA!: (value: unknown) => void;
  vi.mocked(api.get).mockResolvedValueOnce(empty)
    .mockImplementationOnce(() => new Promise(resolve => { resolveA = resolve; }));
  if (outcome === "success") vi.mocked(api.get).mockResolvedValueOnce({ ...empty, total: 2 });
  else vi.mocked(api.get).mockRejectedValueOnce(new Error("B failed"));
  view(); await screen.findByText("Products: 0");
  fireEvent.click(screen.getByRole("tab", { name: "Pokemon" }));
  expect(screen.getByRole("tab", { name: "One Piece" })).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: "One Piece" }));
  if (outcome === "success") await screen.findByText("Products: 2");
  else await screen.findByRole("alert");
  await act(async () => resolveA({ ...empty, total: 99 }));
  expect(screen.queryByText("Products: 99")).toBeNull();
  expect(screen.getByRole("tab", { name: "One Piece" }).getAttribute("aria-selected")).toBe("true");
  if (outcome === "failure") {
    expect(screen.getByRole("alert")).toBeTruthy();
    vi.mocked(api.get).mockResolvedValueOnce(empty);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText("Products: 0");
    expect(lastParams().get("work_id")).toBe(works[1].id);
  }
});

it("AC7 ignores stale failure and completion while the new request is pending", async () => {
  let rejectA!: (reason: Error) => void;
  let resolveB!: (value: unknown) => void;
  vi.mocked(api.get).mockResolvedValueOnce(empty)
    .mockImplementationOnce(() => new Promise((_, reject) => { rejectA = reject; }))
    .mockImplementationOnce(() => new Promise(resolve => { resolveB = resolve; }));
  view(); await screen.findByText("Products: 0");
  fireEvent.click(screen.getByRole("tab", { name: "Pokemon" }));
  fireEvent.click(screen.getByRole("tab", { name: "One Piece" }));
  await act(async () => rejectA(new Error("old")));
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.queryByRole("status")).toBeNull();
  await act(async () => resolveB(empty));
  await screen.findByText("Products: 0");
});

it.each([undefined, null, {}, [null], [{ id: "incomplete" }]])("AC7 reports malformed works (%j)", async value => {
  vi.mocked(api.get).mockResolvedValue({ total: 0, items: [], works: value });
  view(); await screen.findByRole("alert");
  expect(screen.getByRole("tab", { name: "All" })).toBeTruthy();
  expect(screen.queryByText("Products: 0")).toBeNull();
});

it("AC7 keeps candidates on empty/error and keeps a disappeared selected work", async () => {
  vi.mocked(api.get).mockResolvedValueOnce(empty).mockResolvedValueOnce({ ...empty, works: [works[1]] });
  view(); await screen.findByText("Products: 0");
  fireEvent.click(screen.getByRole("tab", { name: "Pokemon" }));
  await screen.findByText("Products: 0");
  expect(screen.getByRole("tab", { name: "Pokemon" }).getAttribute("aria-selected")).toBe("true");
  expect(lastParams().get("work_id")).toBe(works[0].id);
  vi.mocked(api.get).mockRejectedValueOnce(new Error("failed"));
  fireEvent.change(screen.getByLabelText("Search by name or code"), { target: { value: "absent" } });
  await screen.findByRole("alert");
  expect(screen.getByRole("tab", { name: "Pokemon" })).toBeTruthy();
  expect(screen.getByRole("tab", { name: "One Piece" })).toBeTruthy();
  vi.mocked(api.get).mockResolvedValueOnce(empty);
  fireEvent.click(screen.getByRole("tab", { name: "All" }));
  await screen.findByText("Products: 0");
  expect(lastParams().has("work_id")).toBe(false);
});

it("AC8 uses Japanese alternate name, English display name and unshifted DATE", async () => {
  vi.mocked(api.get).mockResolvedValue({ works, total: 1, items: [{ code: "A", japanese_title: "Date fixture", release_date: "2099-01-01", keyword_count: 1 }] });
  await i18n.changeLanguage("ja"); view();
  await screen.findByRole("tab", { name: works[0].alt_name.trim() });
  expect(screen.getByRole("tab", { name: "One Piece" })).toBeTruthy();
  expect(screen.getByRole("tab", { name: i18n.t("productCsv.allWorks") })).toBeTruthy();
  expect(screen.getByText("2099-01-01")).toBeTruthy();
  await act(async () => i18n.changeLanguage("en"));
  expect(screen.getByRole("tab", { name: "Pokemon" })).toBeTruthy();
  expect(screen.getByRole("tab", { name: "All" })).toBeTruthy();
});
