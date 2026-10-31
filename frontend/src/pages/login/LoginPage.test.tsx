import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const mock = vi.hoisted(() => ({
  self: false,
  passkey: false,
  selfPasskeyLogin: vi.fn(),
  signInWithEmailAndPassword: vi.fn(),
  sendPasswordResetEmail: vi.fn(),
}));

vi.mock("../../lib/firebase", () => ({ auth: { currentUser: null } }));
vi.mock("../../lib/firebase-auth", () => ({
  onAuthStateChanged: (_auth: unknown, cb: (u: null) => void) => {
    queueMicrotask(() => cb(null));
    return () => {};
  },
  signInWithEmailAndPassword: mock.signInWithEmailAndPassword,
  sendPasswordResetEmail: mock.sendPasswordResetEmail,
  signOut: vi.fn(),
}));
vi.mock("../../lib/auth/provider", () => ({ isSelfAuth: () => mock.self }));
vi.mock("../../lib/auth/passkey", async (orig) => ({
  ...(await orig<typeof import("../../lib/auth/passkey")>()),
  passkeySupported: () => mock.passkey,
  selfPasskeyLogin: mock.selfPasskeyLogin,
}));

import { AuthProvider } from "../../contexts/AuthContext";
import { SelfAuthError, expireSession } from "../../lib/auth/selfAuth";
import LoginPage from "./LoginPage";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
let fetchMock: ReturnType<typeof vi.fn>;

function renderLogin() {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

async function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText(tr("login.email")), { target: { value: "a@example.com" } });
  fireEvent.change(screen.getByLabelText(tr("login.password")), { target: { value: "secret-password-1" } });
  fireEvent.click(screen.getByRole("button", { name: tr("login.signIn") }));
}

beforeEach(async () => {
  window.history.pushState({}, "", "/login");
  mock.self = false;
  mock.passkey = false;
  mock.selfPasskeyLogin.mockReset();
  mock.signInWithEmailAndPassword.mockReset().mockResolvedValue({});
  mock.sendPasswordResetEmail.mockReset().mockResolvedValue(undefined);
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  expireSession();
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  expireSession();
});

describe("LoginPage (Firebase default)", () => {
  it("sign-in calls the Firebase function and not /api/v1/auth/login", async () => {
    renderLogin();

    await fillAndSubmit();

    await waitFor(() => expect(mock.signInWithEmailAndPassword).toHaveBeenCalledTimes(1));
    expect(mock.signInWithEmailAndPassword.mock.calls[0].slice(1)).toEqual(["a@example.com", "secret-password-1"]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forgot-password and back-to-login are TextLink components", () => {
    renderLogin();

    const forgot = screen.getByRole("button", { name: tr("login.forgotPassword") });
    expect(forgot.className).toContain("comp-text-link");

    fireEvent.click(forgot);
    const back = screen.getByRole("button", { name: tr("login.backToLogin") });
    expect(back.className).toContain("comp-text-link");
  });

  it("reset email is sent through the Firebase function", async () => {
    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: tr("login.forgotPassword") }));
    fireEvent.change(screen.getByLabelText(tr("login.email")), { target: { value: "a@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: tr("login.sendResetEmail") }));

    await waitFor(() => expect(mock.sendPasswordResetEmail).toHaveBeenCalledTimes(1));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("LoginPage (self login)", () => {
  beforeEach(() => {
    mock.self = true;
  });

  it("sign-in calls /api/v1/auth/login and not the Firebase function", async () => {
    // 起動時の refresh は 401、ログインは成功
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/v1/auth/login"
          ? new Response(JSON.stringify({ access_token: "a.b.c", token_type: "bearer", expires_in: 900 }), { status: 200 })
          : new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 }),
      ),
    );
    renderLogin();

    await fillAndSubmit();

    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => u === "/api/v1/auth/login")).toBe(true));
    expect(mock.signInWithEmailAndPassword).not.toHaveBeenCalled();
  });

  it("login 401 shows one message without distinguishing the reason", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 })),
    );
    renderLogin();

    await fillAndSubmit();

    expect(await screen.findByText(tr("authError.invalidCredentials"))).toBeTruthy();
  });

  it("forgot-password calls the reset request endpoint", async () => {
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/v1/auth/password-reset/request"
          ? new Response(JSON.stringify({ status: "accepted" }), { status: 200 })
          : new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 }),
      ),
    );
    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: tr("login.forgotPassword") }));
    fireEvent.change(screen.getByLabelText(tr("login.email")), { target: { value: "a@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: tr("login.sendResetEmail") }));

    expect(await screen.findByText(tr("login.resetEmailSent"))).toBeTruthy();
    expect(mock.sendPasswordResetEmail).not.toHaveBeenCalled();
  });
});

describe("LoginPage (passkey button)", () => {
  beforeEach(() => {
    mock.self = true;
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 })),
    );
  });

  it("is shown only when the device supports passkeys", () => {
    mock.passkey = false;
    renderLogin();
    expect(screen.queryByRole("button", { name: tr("login.signInWithPasskey") })).toBeNull();

    cleanup();
    mock.passkey = true;
    renderLogin();
    expect(screen.getByRole("button", { name: tr("login.signInWithPasskey") })).toBeTruthy();
  });

  it("calls selfPasskeyLogin once through AuthProvider and disables both buttons while running", async () => {
    mock.passkey = true;
    let finish!: () => void;
    mock.selfPasskeyLogin.mockReturnValue(new Promise<void>((resolve) => { finish = resolve; }));
    renderLogin();

    fireEvent.click(screen.getByRole("button", { name: tr("login.signInWithPasskey") }));

    await waitFor(() => expect(mock.selfPasskeyLogin).toHaveBeenCalledTimes(1));
    const buttons = screen.getAllByRole("button").filter((b) => b.getAttribute("type") !== null);
    expect(buttons.filter((b) => (b as HTMLButtonElement).disabled).length).toBeGreaterThanOrEqual(2);
    finish();
  });

  it("cancelled shows the cancelled message", async () => {
    mock.passkey = true;
    const cancelled = new Error("cancelled");
    cancelled.name = "NotAllowedError";
    mock.selfPasskeyLogin.mockRejectedValue(cancelled);
    renderLogin();

    fireEvent.click(screen.getByRole("button", { name: tr("login.signInWithPasskey") }));

    expect(await screen.findByText(tr("authError.passkeyCancelled"))).toBeTruthy();
  });

  it("401 shows the passkey message, not the password message", async () => {
    mock.passkey = true;
    mock.selfPasskeyLogin.mockRejectedValue(new SelfAuthError(401, "invalid_credentials"));
    renderLogin();

    fireEvent.click(screen.getByRole("button", { name: tr("login.signInWithPasskey") }));

    expect(await screen.findByText(tr("authError.passkeyFailed"))).toBeTruthy();
    expect(screen.queryByText(tr("authError.invalidCredentials"))).toBeNull();
  });
});
