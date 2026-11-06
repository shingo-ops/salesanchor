import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { registerDevSession } from "../lib/auth/devSessionSlot";
import en from "../locales/en.json";
import { registerTestDevSession } from "../test-utils/devSession";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("../lib/api", () => ({ api }));

vi.mock("../hooks/usePermissions", () => ({ usePermissions: vi.fn(() => ({ isTenantOwner: false })) }));

import { usePermissions } from "../hooks/usePermissions";
import NoticeBell from "./NoticeBell";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));

const REQUEST = {
  id: "req-1",
  label: "iPhone · Safari",
  location: "Tokyo, JP",
  created_at: new Date().toISOString(),
  expires_at: null,
  candidates: ["12", "34", "56"],
};
const notice = (id: number) => ({
  id,
  kind: "discord_outside_ticket_post",
  actor_name: `user${id}`,
  channel_name: "general",
  link_url: null,
  created_at: new Date().toISOString(),
  read_at: null,
});

function Where() {
  return <div data-testid="where">{useLocation().pathname}</div>;
}

function renderBell(variant: "floating" | "tab" = "tab") {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route
            path="*"
            element={
              <>
                <NoticeBell variant={variant} />
                <Where />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

function mockApi(pending: () => Promise<unknown>) {
  api.get.mockImplementation((path: string) => {
    if (path === "/notices") return Promise.resolve({ items: [notice(1), notice(2)], unread_count: 2 });
    if (path === "/login-approvals/pending") return pending();
    return Promise.reject(new Error("unexpected"));
  });
}

beforeEach(async () => {
  registerDevSession(null);
  api.get.mockReset();
  api.post.mockReset().mockResolvedValue({ unread_count: 0 });
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(() => cleanup());

describe("NoticeBell login requests", () => {
  it("counts the request with unread notices and puts its row first", async () => {
    mockApi(() => Promise.resolve({ items: [REQUEST] }));
    renderBell();
    await waitFor(() => expect(screen.getByText("3")).toBeTruthy());
    fireEvent.click(screen.getByTestId("notice-bell"));
    const rows = await screen.findAllByRole("button", { name: /Login request|posted in/ });
    expect(rows.length).toBe(3);
    expect(rows[0].textContent).toContain("iPhone · Safari");
    // 行そのものが button 1つだけ（行の中に別の button は無い）
    expect(rows[0].querySelectorAll("button").length).toBe(0);
  });

  it("opens a centered dialog on click without changing the URL or marking anything read", async () => {
    mockApi(() => Promise.resolve({ items: [REQUEST] }));
    renderBell();
    await waitFor(() => expect(screen.getByText("3")).toBeTruthy());
    fireEvent.click(screen.getByTestId("notice-bell"));
    const row = await screen.findByRole("button", { name: /iPhone · Safari/ });
    fireEvent.click(row);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(tr("login.deviceApproval.detail.title"))).toBeTruthy();
    await within(dialog).findByRole("button", { name: tr("login.deviceApproval.detail.itsMe") });
    expect(screen.getByTestId("where").textContent).toBe("/");
    expect(api.post).not.toHaveBeenCalled();
  });

  it("gives the unread badge the count size class", async () => {
    mockApi(() => Promise.resolve({ items: [REQUEST] }));
    renderBell("floating");
    await waitFor(() => expect(screen.getByText("3")).toBeTruthy());
    expect(screen.getByText("3").className).toContain("comp-badge--count");
  });

  it("still shows notices when the pending request call fails", async () => {
    mockApi(() => Promise.reject(new Error("boom")));
    renderBell();
    await waitFor(() => expect(screen.getByText("2")).toBeTruthy());
    fireEvent.click(screen.getByTestId("notice-bell"));
    const rows = await screen.findAllByRole("button", { name: /posted in/ });
    expect(rows.length).toBe(2);
  });

  it("does not call the pending endpoint outside self login", async () => {
    registerTestDevSession();
    mockApi(() => Promise.resolve({ items: [REQUEST] }));
    renderBell();
    await waitFor(() => expect(api.get).toHaveBeenCalledWith("/notices"));
    expect(api.get).not.toHaveBeenCalledWith("/login-approvals/pending");
  });
});

describe("NoticeBell staff login requests (company owner)", () => {
  const STAFF = {
    id: "staff-1",
    full_name: "Sato",
    email: "sato@example.com",
    created_at: new Date().toISOString(),
  };
  const mockOwnerApi = () => {
    api.get.mockImplementation((path: string) => {
      if (path === "/notices") return Promise.resolve({ items: [], unread_count: 0 });
      if (path === "/login-approvals/pending") return Promise.resolve({ items: [] });
      if (path === "/tenant/login-requests") return Promise.resolve({ items: [STAFF] });
      return Promise.reject(new Error("unexpected"));
    });
  };
  afterEach(() => {
    vi.mocked(usePermissions).mockReturnValue({ isTenantOwner: false } as never);
  });

  it("B1 adds the staff request to the count and shows the name", async () => {
    vi.mocked(usePermissions).mockReturnValue({ isTenantOwner: true } as never);
    mockOwnerApi();
    renderBell();
    await waitFor(() => expect(screen.getByText("1")).toBeTruthy());
    fireEvent.click(screen.getByTestId("notice-bell"));
    expect(await screen.findByText(/Sato/)).toBeTruthy();
  });

  it("B2 clicking the staff request goes to the management center page", async () => {
    vi.mocked(usePermissions).mockReturnValue({ isTenantOwner: true } as never);
    mockOwnerApi();
    renderBell();
    await waitFor(() => expect(screen.getByText("1")).toBeTruthy());
    fireEvent.click(screen.getByTestId("notice-bell"));
    fireEvent.click(await screen.findByRole("button", { name: /Sato/ }));
    await waitFor(() => expect(screen.getByTestId("where").textContent).toBe("/management-center/login-requests"));
  });

  it("B3 does not call the tenant endpoint for a non owner", async () => {
    vi.mocked(usePermissions).mockReturnValue({ isTenantOwner: false } as never);
    mockApi(() => Promise.resolve({ items: [REQUEST] }));
    renderBell();
    await waitFor(() => expect(screen.getByText("3")).toBeTruthy());
    expect(api.get).not.toHaveBeenCalledWith("/tenant/login-requests");
  });
});
