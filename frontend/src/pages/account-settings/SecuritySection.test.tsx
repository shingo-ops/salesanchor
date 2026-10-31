import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const mock = vi.hoisted(() => ({
  self: true,
  post: vi.fn(),
  get: vi.fn(),
  delete: vi.fn(),
  updatePassword: vi.fn(),
  reauthenticate: vi.fn(),
}));

vi.mock("../../lib/auth/provider", () => ({ isSelfAuth: () => mock.self }));
vi.mock("../../lib/firebase", () => ({ auth: { currentUser: { email: "me@example.com" } } }));
vi.mock("../../lib/firebase-auth", () => ({
  EmailAuthProvider: { credential: (email: string, password: string) => ({ email, password }) },
  reauthenticateWithCredential: mock.reauthenticate,
  updatePassword: mock.updatePassword,
}));
vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, api: { get: mock.get, post: mock.post, delete: mock.delete } };
});

import { ApiError } from "../../lib/api";
import { currentAccessToken, expireSession } from "../../lib/auth/selfAuth";
import SecuritySection from "./SecuritySection";

let instance = createInstance();
let view: ReturnType<typeof render>;
const tr =(key: string) => String(instance.t(key));

function submit(current: string, next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText(tr("accountSettings.currentPassword")), { target: { value: current } });
  fireEvent.change(screen.getByLabelText(tr("accountSettings.newPassword")), { target: { value: next } });
  fireEvent.change(screen.getByLabelText(tr("accountSettings.confirmPassword")), { target: { value: confirm } });
  fireEvent.click(screen.getByRole("button", { name: tr("accountSettings.changePassword") }));
}

beforeEach(async () => {
  mock.self = true;
  mock.post.mockReset();
  mock.get.mockReset().mockResolvedValue({ items: [] });
  mock.delete.mockReset();
  mock.updatePassword.mockReset().mockResolvedValue(undefined);
  mock.reauthenticate.mockReset().mockResolvedValue({});
  expireSession();
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  view = render(<I18nextProvider i18n={instance}><SecuritySection /></I18nextProvider>);
});
afterEach(() => {
  cleanup();
  expireSession();
});

describe("SecuritySection (self login)", () => {
  it("calls password/change and adopts the new token from the response", async () => {
    mock.post.mockResolvedValue({ status: "password_updated", access_token: "new.token.value", expires_in: 900 });

    submit("old-password", "a-long-enough-password-1", "a-long-enough-password-1");

    await waitFor(() => expect(screen.getByText(tr("accountSettings.passwordChanged"))).toBeTruthy());
    expect(mock.post).toHaveBeenCalledWith("/auth/password/change", {
      current_password: "old-password",
      new_password: "a-long-enough-password-1",
    });
    expect(currentAccessToken()).toBe("new.token.value");
    expect(mock.updatePassword).not.toHaveBeenCalled();
  });

  it("400 is the wrong-current-password message; 422 identifiers map to rule messages", async () => {
    mock.post.mockRejectedValueOnce(new ApiError("invalid_credentials", 400, "invalid_credentials"));
    submit("wrong", "a-long-enough-password-1", "a-long-enough-password-1");
    expect(await screen.findByText(tr("authError.currentPasswordWrong"))).toBeTruthy();

    mock.post.mockRejectedValueOnce(new ApiError("password_too_short", 422, "password_too_short"));
    submit("old-password", "short", "short");
    expect(await screen.findByText(tr("authError.passwordTooShort"))).toBeTruthy();
  });

  it("does not submit when the confirmation differs", () => {
    submit("old-password", "a-long-enough-password-1", "different-password-xx");

    expect(screen.getByText(tr("accountSettings.passwordMismatch"))).toBeTruthy();
    expect(mock.post).not.toHaveBeenCalled();
  });
});

describe("SecuritySection passkey section", () => {
  it("is a sibling frame after the security section, not nested, for self login", async () => {
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith("/auth/passkeys"));
    const sections = view.container.querySelectorAll(".account-settings-section");
    expect(sections).toHaveLength(4);
    expect(sections[0].contains(sections[3])).toBe(false);
    expect(sections[3].textContent).toContain(tr("accountSettings.passkeyTitle"));
  });

  it("is not shown with Firebase", () => {
    cleanup();
    mock.self = false;
    const rendered = render(<I18nextProvider i18n={instance}><SecuritySection /></I18nextProvider>);

    expect(rendered.container.querySelectorAll(".account-settings-section")).toHaveLength(1);
  });
});

describe("SecuritySection (Firebase)", () => {
  it("re-authenticates and updates through Firebase and does not call the self API", async () => {
    mock.self = false;

    submit("old-password", "long-enough-pw", "long-enough-pw");

    await waitFor(() => expect(mock.updatePassword).toHaveBeenCalledTimes(1));
    expect(mock.post).not.toHaveBeenCalled();
  });
});
