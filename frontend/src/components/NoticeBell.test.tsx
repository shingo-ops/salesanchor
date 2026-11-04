import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { registerDevSession } from "../lib/auth/devSessionSlot";
import en from "../locales/en.json";
import { registerTestDevSession } from "../test-utils/devSession";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("../lib/api", () => ({ api }));

import NoticeBell from "./NoticeBell";

let instance = createInstance();

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

function renderBell() {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route
            path="*"
            element={
              <>
                <NoticeBell variant="tab" />
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

  it("navigates to the detail page on click without marking anything read", async () => {
    mockApi(() => Promise.resolve({ items: [REQUEST] }));
    renderBell();
    await waitFor(() => expect(screen.getByText("3")).toBeTruthy());
    fireEvent.click(screen.getByTestId("notice-bell"));
    const row = await screen.findByRole("button", { name: /iPhone · Safari/ });
    fireEvent.click(row);
    await waitFor(() => expect(screen.getByTestId("where").textContent).toBe("/account/login-requests/req-1"));
    expect(api.post).not.toHaveBeenCalled();
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
