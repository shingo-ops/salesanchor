import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
it("does not request or expose import for non-admin", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false }); view();
  expect(api.get).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "Import CSV" })).toBeNull();
});
it("shows total, pages through results and resets offset on search", async () => {
  vi.mocked(api.get).mockResolvedValue({ total: 51, items: [{ code: "PM51", japanese_title: "Fixture", keyword_count: 0 }] }); view();
  await screen.findByText("Products: 51");
  expect(screen.getByText("No search keywords")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "next page" }));
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.slice(-1)[0]?.[0]).toContain("offset=50"));
  fireEvent.change(screen.getByLabelText("Search by name or code"), { target: { value: "A & B" } });
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.slice(-1)[0]?.[0]).toContain("query=A+%26+B&limit=50&offset=0"));
});
it("discards an older response that arrives after a new search", async () => {
  let old!: (value: unknown) => void;
  vi.mocked(api.get).mockImplementationOnce(() => new Promise(resolve => { old = resolve; })).mockResolvedValue({ total: 0, items: [] }); view();
  fireEvent.change(screen.getByLabelText("Search by name or code"), { target: { value: "new" } });
  await screen.findByText("Products: 0"); old({ total: 99, items: [] });
  await waitFor(() => expect(screen.queryByText("Products: 99")).toBeNull());
});
