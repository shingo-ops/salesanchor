import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

vi.mock("../../lib/firebase", () => ({ auth: { currentUser: null } }));

import ResetPasswordPage from "./ResetPasswordPage";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
let fetchMock: ReturnType<typeof vi.fn>;

function renderAt(url: string) {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/login" element={<div>login-page</div>} />
        </Routes>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

function submit(next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText(tr("resetPasswordPage.newPassword")), { target: { value: next } });
  fireEvent.change(screen.getByLabelText(tr("resetPasswordPage.confirmPassword")), { target: { value: confirm } });
  fireEvent.click(screen.getByRole("button", { name: tr("resetPasswordPage.submit") }));
}

beforeEach(async () => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ResetPasswordPage", () => {
  it("without a token only the notice is shown, not the form", () => {
    renderAt("/reset-password");

    expect(screen.getByText(tr("resetPasswordPage.missingTokenTitle"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: tr("resetPasswordPage.submit") })).toBeNull();
  });

  it("does not submit when the confirmation differs", () => {
    renderAt("/reset-password?token=abc");

    submit("a-long-enough-password-1", "a-long-enough-password-2");

    expect(screen.getByText(tr("resetPasswordPage.mismatch"))).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends the URL token and new password to confirm, then links to login (no auto login)", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ status: "password_updated" }), { status: 200 })),
    );
    renderAt("/reset-password?token=abc123");

    submit("a-long-enough-password-1", "a-long-enough-password-1");

    await waitFor(() => expect(screen.getByText(tr("resetPasswordPage.doneTitle"))).toBeTruthy());
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/auth/password-reset/confirm");
    expect(JSON.parse(init.body)).toEqual({ token: "abc123", new_password: "a-long-enough-password-1" });
    const link = screen.getByRole("link", { name: tr("resetPasswordPage.goToLogin") });
    expect(link.getAttribute("href")).toBe("/login");
  });

  it("400 (invalid or expired) shows the invalid link message", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ detail: "invalid_or_expired_token" }), { status: 400 })),
    );
    renderAt("/reset-password?token=expired");

    submit("a-long-enough-password-1", "a-long-enough-password-1");

    expect(await screen.findByText(tr("authError.resetLinkInvalid"))).toBeTruthy();
  });

  it("422 identifiers map to the password rule message", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ detail: "password_too_short" }), { status: 422 })),
    );
    renderAt("/reset-password?token=abc");

    submit("short", "short");

    expect(await screen.findByText(tr("authError.passwordTooShort"))).toBeTruthy();
  });
});
