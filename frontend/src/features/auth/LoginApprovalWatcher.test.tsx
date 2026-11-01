import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
const provider = vi.hoisted(() => ({ self: true }));
vi.mock("../../lib/api", () => ({ api }));
vi.mock("../../lib/auth/provider", () => ({ isSelfAuth: () => provider.self }));

import LoginApprovalWatcher from "./LoginApprovalWatcher";

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

function renderWatcher() {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter>
        <LoginApprovalWatcher />
      </MemoryRouter>
    </I18nextProvider>,
  );
}

beforeEach(async () => {
  provider.self = true;
  api.get.mockReset();
  api.post.mockReset().mockResolvedValue({});
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(() => cleanup());

describe("LoginApprovalWatcher", () => {
  it("shows nothing when there is no pending request", async () => {
    api.get.mockResolvedValue({ items: [] });
    renderWatcher();
    await waitFor(() => expect(api.get).toHaveBeenCalledWith("/login-approvals/pending"));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("does nothing outside self login", () => {
    provider.self = false;
    renderWatcher();
    expect(api.get).not.toHaveBeenCalled();
  });

  it("shows the device and three numbers, and approves with the chosen one", async () => {
    api.get.mockResolvedValue({ items: [REQUEST] });
    renderWatcher();
    await screen.findByText("iPhone · Safari");
    expect(screen.getByText("Tokyo, JP")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "34" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/auth/login-requests/req-1/approve", { number: "34" }),
    );
  });

  it("rejects with 'not me' and offers a password change", async () => {
    api.get.mockResolvedValueOnce({ items: [REQUEST] }).mockResolvedValue({ items: [] });
    renderWatcher();
    await screen.findByText("iPhone · Safari");
    fireEvent.click(screen.getByRole("button", { name: tr("login.deviceApproval.watcher.notMe") }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/auth/login-requests/req-1/reject", {}));
    await screen.findByText(tr("login.deviceApproval.watcher.rejectedBody"));
  });
});
