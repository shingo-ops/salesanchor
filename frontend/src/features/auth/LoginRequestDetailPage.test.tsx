import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("../../lib/api", () => ({ api }));

import LoginRequestDetailPage from "./LoginRequestDetailPage";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));

const REQUEST = {
  id: "req-1",
  label: "iPhone · Safari",
  location: "Tokyo, JP",
  created_at: "2026-11-01T01:00:00Z",
  expires_at: "2026-11-01T01:10:00Z",
  candidates: ["12", "34", "56"],
};

function renderPage(id = "req-1") {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={[`/account/login-requests/${id}`]}>
        <Routes>
          <Route path="/account/login-requests/:id" element={<LoginRequestDetailPage />} />
        </Routes>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

beforeEach(async () => {
  api.get.mockReset();
  api.post.mockReset().mockResolvedValue({ status: "approved" });
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(() => cleanup());

describe("LoginRequestDetailPage", () => {
  it("shows device, location, time and the two buttons, but no numbers yet", async () => {
    api.get.mockResolvedValue({ items: [REQUEST] });
    renderPage();
    await screen.findByText("iPhone · Safari");
    expect(screen.getByText("Tokyo, JP")).toBeTruthy();
    expect(screen.getAllByRole("definition").length).toBe(3);
    expect(screen.getByRole("button", { name: tr("login.deviceApproval.watcher.notMe") })).toBeTruthy();
    expect(screen.getByRole("button", { name: tr("login.deviceApproval.detail.itsMe") })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "34" })).toBeNull();
  });

  it("shows three numbers after 'This was me' and approves with the chosen one", async () => {
    api.get.mockResolvedValue({ items: [REQUEST] });
    renderPage();
    await screen.findByText("iPhone · Safari");
    fireEvent.click(screen.getByRole("button", { name: tr("login.deviceApproval.detail.itsMe") }));
    expect(screen.getByRole("button", { name: "12" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "34" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "56" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "34" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/auth/login-requests/req-1/approve", { number: "34" }),
    );
    await screen.findByText(tr("login.deviceApproval.detail.approvedTitle"));
  });

  it("shows the cancelled message when the number is wrong", async () => {
    api.get.mockResolvedValue({ items: [REQUEST] });
    api.post.mockResolvedValue({ status: "rejected", reason: "wrong_number" });
    renderPage();
    await screen.findByText("iPhone · Safari");
    fireEvent.click(screen.getByRole("button", { name: tr("login.deviceApproval.detail.itsMe") }));
    fireEvent.click(screen.getByRole("button", { name: "12" }));
    await screen.findByText(tr("login.deviceApproval.detail.wrongNumberBody"));
  });

  it("rejects with 'This wasn't me' and shows the rejected message", async () => {
    api.get.mockResolvedValueOnce({ items: [REQUEST] }).mockResolvedValue({ items: [] });
    api.post.mockResolvedValue({ status: "rejected" });
    renderPage();
    await screen.findByText("iPhone · Safari");
    fireEvent.click(screen.getByRole("button", { name: tr("login.deviceApproval.watcher.notMe") }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/auth/login-requests/req-1/reject", {}));
    await screen.findByText(tr("login.deviceApproval.watcher.rejectedTitle"));
  });

  it("shows 'ended' when the id is not in the pending list", async () => {
    api.get.mockResolvedValue({ items: [REQUEST] });
    renderPage("other-id");
    await screen.findByText(tr("login.deviceApproval.detail.closed"));
  });
});
