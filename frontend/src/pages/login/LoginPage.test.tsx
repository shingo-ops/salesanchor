import { StrictMode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const mock = vi.hoisted(() => ({
  passkey: false,
  selfPasskeyLogin: vi.fn(),
  getPasskeyPrompt: vi.fn(),
  conditionalCreateSupported: vi.fn(),
  autoRegisterPasskey: vi.fn(),
  skipPasskeyPrompt: vi.fn(),
  registerPasskey: vi.fn(),
  immediateGetSupported: vi.fn(),
  immediatePasskeyLogin: vi.fn(),
  passkeyAutofillSupported: vi.fn(),
  startPasskeyAutofill: vi.fn(),
  cancelPasskeyCeremony: vi.fn(),
}));

vi.mock("../../lib/auth/passkey", async (orig) => ({
  ...(await orig<typeof import("../../lib/auth/passkey")>()),
  immediateGetSupported: mock.immediateGetSupported,
  immediatePasskeyLogin: mock.immediatePasskeyLogin,
  passkeyAutofillSupported: mock.passkeyAutofillSupported,
  startPasskeyAutofill: mock.startPasskeyAutofill,
  cancelPasskeyCeremony: mock.cancelPasskeyCeremony,
  passkeySupported: () => mock.passkey,
  selfPasskeyLogin: mock.selfPasskeyLogin,
  getPasskeyPrompt: mock.getPasskeyPrompt,
  conditionalCreateSupported: mock.conditionalCreateSupported,
  autoRegisterPasskey: mock.autoRegisterPasskey,
  skipPasskeyPrompt: mock.skipPasskeyPrompt,
  registerPasskey: mock.registerPasskey,
}));

import { AuthProvider } from "../../contexts/AuthContext";
import { SelfAuthError, expireSession } from "../../lib/auth/selfAuth";
import { registerDevSession } from "../../lib/auth/devSessionSlot";
import { registerTestDevSession } from "../../test-utils/devSession";
import LoginPage from "./LoginPage";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
let fetchMock: ReturnType<typeof vi.fn>;

function renderLogin() {
  return render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

async function renderLoginWithHome() {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<div data-testid="after-login" />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </I18nextProvider>,
  );
  // 起動時の refresh（401）が終わる前にログインすると、その失効がログイン結果を消して user が立たない。終わるまで待つ
  await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => u === "/api/v1/auth/refresh")).toBe(true));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

async function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText(tr("login.email")), { target: { value: "a@example.com" } });
  fireEvent.change(screen.getByLabelText(tr("login.password")), { target: { value: "secret-password-1" } });
  fireEvent.click(screen.getByRole("button", { name: tr("login.signIn") }));
}

beforeEach(async () => {
  window.history.pushState({}, "", "/login");
  mock.passkey = false;
  mock.selfPasskeyLogin.mockReset();
  mock.getPasskeyPrompt.mockReset().mockResolvedValue({ can_auto: false, show_prompt: false });
  mock.conditionalCreateSupported.mockReset().mockResolvedValue(true);
  mock.autoRegisterPasskey.mockReset().mockResolvedValue("created");
  mock.skipPasskeyPrompt.mockReset().mockResolvedValue(undefined);
  mock.registerPasskey.mockReset().mockResolvedValue(undefined);
  mock.immediateGetSupported.mockReset().mockResolvedValue(false);
  mock.immediatePasskeyLogin.mockReset().mockResolvedValue(undefined);
  mock.passkeyAutofillSupported.mockReset().mockResolvedValue(false);
  mock.startPasskeyAutofill.mockReset().mockImplementation(() => new Promise<void>(() => {}));
  mock.cancelPasskeyCeremony.mockReset();
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

describe("LoginPage (dev session)", () => {
  it("sign-in goes to the dev session and not /api/v1/auth/login", async () => {
    const dev = registerTestDevSession();
    renderLogin();

    await fillAndSubmit();

    await waitFor(() => expect(dev.signIn).toHaveBeenCalledWith("a@example.com", "secret-password-1"));
    expect(fetchMock.mock.calls.some(([u]) => u === "/api/v1/auth/login")).toBe(false);
  });

  it("forgot-password and back-to-login are TextLink components", () => {
    renderLogin();

    const forgot = screen.getByRole("button", { name: tr("login.forgotPassword") });
    expect(forgot.className).toContain("comp-text-link");

    fireEvent.click(forgot);
    const back = screen.getByRole("button", { name: tr("login.backToLogin") });
    expect(back.className).toContain("comp-text-link");
  });

  it("reset email goes to the self reset request endpoint", async () => {
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
    expect(fetchMock.mock.calls.some(([u]) => u === "/api/v1/auth/password-reset/request")).toBe(true);
  });
});

describe("LoginPage (self login)", () => {
  beforeEach(() => {
    registerDevSession(null);
  });

  it("202 shows the waiting screen with the number and no navigation", async () => {
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/v1/auth/login"
          ? new Response(
              JSON.stringify({
                status: "device_approval_required",
                match_number: "73",
                expires_in: 600,
                has_trusted_device: true,
                has_recovery_codes: true,
              }),
              { status: 202 },
            )
          : new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 }),
      ),
    );
    await renderLoginWithHome();

    await fillAndSubmit();

    await waitFor(() => expect(screen.getByTestId("login-approval-number").textContent).toBe("73"));
    expect(screen.queryByTestId("after-login")).toBeNull();
    expect(screen.getByRole("button", { name: tr("login.deviceApproval.useRecoveryCode") })).toBeTruthy();
  });

  it("sign-in calls /api/v1/auth/login", async () => {
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
  });

  it("must_change_password=true goes to /password-change and not to the passkey prompt or home", async () => {
    mock.passkey = true;
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/v1/auth/login"
          ? new Response(
              JSON.stringify({ access_token: "a.b.c", token_type: "bearer", expires_in: 900, must_change_password: true }),
              { status: 200 },
            )
          : new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 }),
      ),
    );
    render(
      <I18nextProvider i18n={instance}>
        <MemoryRouter initialEntries={["/login"]}>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" element={<div data-testid="after-login" />} />
              <Route path="/password-change" element={<div data-testid="password-change" />} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </I18nextProvider>,
    );
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => u === "/api/v1/auth/refresh")).toBe(true));
    await new Promise((resolve) => setTimeout(resolve, 0));

    await fillAndSubmit();

    expect(await screen.findByTestId("password-change")).toBeTruthy();
    expect(screen.queryByTestId("after-login")).toBeNull();
    expect(mock.getPasskeyPrompt).not.toHaveBeenCalled();
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
  });
});

describe("LoginPage (ask company admin)", () => {
  beforeEach(() => {
    registerDevSession(null);
  });

  // 202 の待ち画面を出し、ask-admin と poll の返事を差し替えられるようにする
  async function openWaitingScreen(askRes: () => Response, pollRes?: () => Response) {
    fetchMock.mockImplementation((url: string) => {
      if (url === "/api/v1/auth/login") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              status: "device_approval_required",
              match_number: "73",
              expires_in: 600,
              has_trusted_device: false,
              has_recovery_codes: false,
            }),
            { status: 202 },
          ),
        );
      }
      if (url === "/api/v1/auth/login-requests/ask-admin") return Promise.resolve(askRes());
      if (url === "/api/v1/auth/login-requests/poll" && pollRes) return Promise.resolve(pollRes());
      return Promise.resolve(new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 }));
    });
    await renderLoginWithHome();
    await fillAndSubmit();
    await waitFor(() => expect(screen.getByTestId("login-approval-number").textContent).toBe("73"));
  }

  const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

  it("T1 requested shows the message and disables the button", async () => {
    await openWaitingScreen(() => json({ status: "requested" }));
    const button = screen.getByRole("button", { name: tr("login.deviceApproval.askAdmin") });

    fireEvent.click(button);

    expect(await screen.findByText(tr("login.deviceApproval.askAdminRequested"))).toBeTruthy();
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(true));
  });

  it("T2 no_owner shows the no-owner message", async () => {
    await openWaitingScreen(() => json({ status: "no_owner" }));

    fireEvent.click(screen.getByRole("button", { name: tr("login.deviceApproval.askAdmin") }));

    expect(await screen.findByText(tr("login.deviceApproval.askAdminNoOwner"))).toBeTruthy();
  });

  it("T3 expired leaves the waiting screen with the expired message", async () => {
    await openWaitingScreen(() => json({ status: "expired" }));

    fireEvent.click(screen.getByRole("button", { name: tr("login.deviceApproval.askAdmin") }));

    expect(await screen.findByText(tr("login.deviceApproval.expired"))).toBeTruthy();
    expect(screen.queryByTestId("login-approval-number")).toBeNull();
  });

  it("T4 409 not_pending then poll rejected shows the rejected message", async () => {
    await openWaitingScreen(
      () => json({ detail: "not_pending" }, 409),
      () => json({ status: "rejected" }),
    );

    fireEvent.click(screen.getByRole("button", { name: tr("login.deviceApproval.askAdmin") }));

    expect(await screen.findByText(tr("login.deviceApproval.rejected"))).toBeTruthy();
    expect(screen.queryByTestId("login-approval-number")).toBeNull();
  });
});

describe("LoginPage (passkey button)", () => {
  beforeEach(() => {
    registerDevSession(null);
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

const named = (name: string) => Object.assign(new Error(name), { name });
const flush = () =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
const advance = (ms: number) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });

describe("LoginPage (passkey immediate button)", () => {
  beforeEach(() => {
    registerDevSession(null);
    mock.passkey = true;
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 })),
    );
  });

  it("T4 NotAllowedError shows the not-on-device notice; the link runs the current path once", async () => {
    mock.immediateGetSupported.mockResolvedValue(true);
    mock.immediatePasskeyLogin.mockRejectedValue(named("NotAllowedError"));
    mock.selfPasskeyLogin.mockResolvedValue(undefined);
    renderLogin();
    await act(async () => {});

    fireEvent.click(screen.getByRole("button", { name: tr("login.signInWithPasskey") }));

    expect(await screen.findByText(tr("login.passkeyNotOnDevice"))).toBeTruthy();
    expect(mock.selfPasskeyLogin).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: tr("login.passkeyUseOtherDevice") }));
    await waitFor(() => expect(mock.selfPasskeyLogin).toHaveBeenCalledTimes(1));
  });

  it("T5 without immediate support the button uses the current path and not immediate", async () => {
    mock.immediateGetSupported.mockResolvedValue(false);
    mock.selfPasskeyLogin.mockResolvedValue(undefined);
    renderLogin();
    await act(async () => {});

    fireEvent.click(screen.getByRole("button", { name: tr("login.signInWithPasskey") }));

    await waitFor(() => expect(mock.selfPasskeyLogin).toHaveBeenCalledTimes(1));
    expect(mock.immediatePasskeyLogin).not.toHaveBeenCalled();
  });

  it("T6 immediate success goes to the original page and skips the current path", async () => {
    mock.immediateGetSupported.mockResolvedValue(true);
    mock.immediatePasskeyLogin.mockResolvedValue(undefined);
    await renderLoginWithHome();
    await act(async () => {});

    fireEvent.click(screen.getByRole("button", { name: tr("login.signInWithPasskey") }));

    expect(await screen.findByTestId("after-login")).toBeTruthy();
    expect(mock.immediatePasskeyLogin).toHaveBeenCalledTimes(1);
    expect(mock.selfPasskeyLogin).not.toHaveBeenCalled();
  });

  it("T7 sign-in email has autocomplete 'email webauthn'; the reset email stays 'email'", () => {
    renderLogin();
    expect(screen.getByLabelText(tr("login.email")).getAttribute("autocomplete")).toBe("email webauthn");
    fireEvent.click(screen.getByRole("button", { name: tr("login.forgotPassword") }));
    expect(screen.getByLabelText(tr("login.email")).getAttribute("autocomplete")).toBe("email");
  });
});

describe("LoginPage (passkey autofill)", () => {
  let visibility: DocumentVisibilityState;
  let visibilitySpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    registerDevSession(null);
    mock.passkey = true;
    mock.passkeyAutofillSupported.mockResolvedValue(true);
    visibility = "visible";
    visibilitySpy = vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibility);
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 })),
    );
  });
  afterEach(() => {
    visibilitySpy.mockRestore();
    vi.useRealTimers();
  });

  it("T8 starts once on open, stays silent on AbortError, and cancels on close", async () => {
    mock.startPasskeyAutofill.mockRejectedValue(named("AbortError"));
    const view = renderLogin();

    await waitFor(() => expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(1));
    await act(async () => {});
    expect(document.querySelector(".error-message")).toBeNull();
    mock.cancelPasskeyCeremony.mockClear();

    view.unmount();

    expect(mock.cancelPasskeyCeremony).toHaveBeenCalled();
  });

  it("T8 shows the passkey message only when verify failed", async () => {
    mock.startPasskeyAutofill.mockRejectedValue(new SelfAuthError(401, "invalid_credentials"));
    renderLogin();
    expect(await screen.findByText(tr("authError.passkeyFailed"))).toBeTruthy();
  });

  it("T9 restarts after 240s (cancel first) and stops after 15 restarts", async () => {
    vi.useFakeTimers();
    renderLogin();
    await flush();
    await flush();
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(1);

    await advance(240_000);

    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(2);
    const cancelOrder = mock.cancelPasskeyCeremony.mock.invocationCallOrder[0];
    const starts = mock.startPasskeyAutofill.mock.invocationCallOrder;
    expect(cancelOrder).toBeGreaterThan(starts[0]);
    expect(cancelOrder).toBeLessThan(starts[1]);

    for (let i = 0; i < 14; i++) await advance(240_000);
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(16);
    await advance(240_000);
    await advance(240_000);
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(16);
  });

  it("T10 does not restart while hidden; restarts once when visible again after 240s", async () => {
    vi.useFakeTimers();
    renderLogin();
    await flush();
    await flush();
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(1);

    document.dispatchEvent(new Event("visibilitychange"));
    await flush();
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(1);

    visibility = "hidden";
    await advance(240_000);
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(1);

    visibility = "visible";
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(2);
  });

  it("T11 does not restart while immediate is pending; restarts once after it ends in NotAllowedError", async () => {
    vi.useFakeTimers();
    mock.immediateGetSupported.mockResolvedValue(true);
    let fail!: (e: Error) => void;
    mock.immediatePasskeyLogin.mockReturnValue(new Promise<void>((_, reject) => { fail = reject; }));
    renderLogin();
    await flush();
    await flush();
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: tr("login.signInWithPasskey") }));
    await flush();
    await advance(1_500);
    expect(mock.immediatePasskeyLogin).toHaveBeenCalledTimes(1);

    await advance(240_000);
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(1);

    await act(async () => {
      fail(named("NotAllowedError"));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(2);
    expect(screen.getByText(tr("login.passkeyNotOnDevice"))).toBeTruthy();
  });

  it("T12 isStale is true after unmount; a newer call is not stale", async () => {
    vi.useFakeTimers();
    const view = renderLogin();
    await flush();
    await flush();
    await advance(240_000);
    expect(mock.startPasskeyAutofill).toHaveBeenCalledTimes(2);
    const first = mock.startPasskeyAutofill.mock.calls[0][0] as () => boolean;
    const second = mock.startPasskeyAutofill.mock.calls[1][0] as () => boolean;
    expect(first()).toBe(true);
    expect(second()).toBe(false);

    view.unmount();

    expect(second()).toBe(true);
  });

  it("T12 under StrictMode only the last call is live; earlier ones are stale", async () => {
    vi.useFakeTimers();
    render(
      <StrictMode>
        <I18nextProvider i18n={instance}>
          <MemoryRouter initialEntries={["/login"]}>
            <AuthProvider>
              <LoginPage />
            </AuthProvider>
          </MemoryRouter>
        </I18nextProvider>
      </StrictMode>,
    );
    await flush();
    await flush();

    const calls = mock.startPasskeyAutofill.mock.calls.map((c) => c[0] as () => boolean);
    expect(calls.length).toBeGreaterThanOrEqual(1);
    expect(calls[calls.length - 1]()).toBe(false);
    for (const isStale of calls.slice(0, -1)) expect(isStale()).toBe(true);
  });
});

describe("LoginPage (enroll after password sign-in)", () => {
  beforeEach(() => {
    registerDevSession(null);
    mock.passkey = true;
    // user を立てるため、sub と email を持つ読める JWT を返す（"a.b.c" だと user が null のままで守りを試せない）
    const jwt = `h.${btoa(JSON.stringify({ sub: "u1", email: "a@example.com" }))}.s`;
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/v1/auth/login"
          ? new Response(JSON.stringify({ access_token: jwt, token_type: "bearer", expires_in: 900 }), { status: 200 })
          : new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 }),
      ),
    );
  });

  it("L1 unsupported device: no prompt, goes on", async () => {
    mock.passkey = false;
    await renderLoginWithHome();
    await fillAndSubmit();
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => u === "/api/v1/auth/login")).toBe(true));
    expect(mock.getPasskeyPrompt).not.toHaveBeenCalled();
    expect(screen.queryByText(tr("login.passkeyPromptTitle"))).toBeNull();
    expect(await screen.findByTestId("after-login")).toBeTruthy();
  });

  it("L2 auto create succeeds: no prompt", async () => {
    mock.getPasskeyPrompt.mockResolvedValue({ can_auto: true, show_prompt: true });
    await renderLoginWithHome();
    await fillAndSubmit();
    await waitFor(() => expect(mock.autoRegisterPasskey).toHaveBeenCalledTimes(1));
    expect(screen.queryByText(tr("login.passkeyPromptTitle"))).toBeNull();
    expect(await screen.findByTestId("after-login")).toBeTruthy();
  });

  it("L3 not_allowed + show_prompt: prompt shown, skip records once", async () => {
    mock.getPasskeyPrompt.mockResolvedValue({ can_auto: true, show_prompt: true });
    mock.autoRegisterPasskey.mockResolvedValue("not_allowed");
    await renderLoginWithHome();
    await fillAndSubmit();
    expect(await screen.findByText(tr("login.passkeyPromptTitle"))).toBeTruthy();
    expect(screen.queryByTestId("after-login")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: tr("login.passkeyPromptSkip") }));
    await waitFor(() => expect(mock.skipPasskeyPrompt).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.queryByText(tr("login.passkeyPromptTitle"))).toBeNull());
    expect(await screen.findByTestId("after-login")).toBeTruthy();
  });

  it("L4 not_allowed + no show_prompt: no prompt", async () => {
    mock.getPasskeyPrompt.mockResolvedValue({ can_auto: true, show_prompt: false });
    mock.autoRegisterPasskey.mockResolvedValue("not_allowed");
    await renderLoginWithHome();
    await fillAndSubmit();
    await waitFor(() => expect(mock.autoRegisterPasskey).toHaveBeenCalledTimes(1));
    expect(screen.queryByText(tr("login.passkeyPromptTitle"))).toBeNull();
    expect(mock.skipPasskeyPrompt).not.toHaveBeenCalled();
    expect(await screen.findByTestId("after-login")).toBeTruthy();
  });

  it("L5 getPasskeyPrompt fails: no prompt, goes on", async () => {
    mock.getPasskeyPrompt.mockRejectedValue(new Error("down"));
    await renderLoginWithHome();
    await fillAndSubmit();
    await waitFor(() => expect(mock.getPasskeyPrompt).toHaveBeenCalledTimes(1));
    expect(screen.queryByText(tr("login.passkeyPromptTitle"))).toBeNull();
    expect(mock.autoRegisterPasskey).not.toHaveBeenCalled();
    expect(await screen.findByTestId("after-login")).toBeTruthy();
  });

  it("L6 register button calls registerPasskey once even when it fails", async () => {
    mock.getPasskeyPrompt.mockResolvedValue({ can_auto: false, show_prompt: true });
    mock.registerPasskey.mockRejectedValue(new Error("cancelled"));
    await renderLoginWithHome();
    await fillAndSubmit();
    expect(await screen.findByText(tr("login.passkeyPromptTitle"))).toBeTruthy();
    expect(screen.queryByTestId("after-login")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: tr("login.passkeyPromptRegister") }));
    await waitFor(() => expect(mock.registerPasskey).toHaveBeenCalledTimes(1));
    expect(mock.registerPasskey).toHaveBeenCalledWith("");
    await waitFor(() => expect(screen.queryByText(tr("login.passkeyPromptTitle"))).toBeNull());
    expect(await screen.findByTestId("after-login")).toBeTruthy();
  });

  it("L7 does not navigate away while getPasskeyPrompt is pending (!enrolling guard)", async () => {
    let resolvePrompt: (v: { can_auto: boolean; show_prompt: boolean }) => void = () => {};
    mock.getPasskeyPrompt.mockReturnValue(
      new Promise((resolve) => {
        resolvePrompt = resolve;
      }),
    );
    await renderLoginWithHome();
    await fillAndSubmit();
    await waitFor(() => expect(mock.getPasskeyPrompt).toHaveBeenCalledTimes(1));
    expect(screen.queryByTestId("after-login")).toBeNull();
    resolvePrompt({ can_auto: false, show_prompt: true });
    expect(await screen.findByText(tr("login.passkeyPromptTitle"))).toBeTruthy();
    expect(screen.queryByTestId("after-login")).toBeNull();
  });

  it("L8 auto create failed + show_prompt: prompt shown", async () => {
    mock.getPasskeyPrompt.mockResolvedValue({ can_auto: true, show_prompt: true });
    mock.autoRegisterPasskey.mockResolvedValue("failed");
    await renderLoginWithHome();
    await fillAndSubmit();
    expect(await screen.findByText(tr("login.passkeyPromptTitle"))).toBeTruthy();
    expect(screen.queryByTestId("after-login")).toBeNull();
  });

  it("L9 auto create exists: no prompt", async () => {
    mock.getPasskeyPrompt.mockResolvedValue({ can_auto: true, show_prompt: true });
    mock.autoRegisterPasskey.mockResolvedValue("exists");
    await renderLoginWithHome();
    await fillAndSubmit();
    await waitFor(() => expect(mock.autoRegisterPasskey).toHaveBeenCalledTimes(1));
    expect(screen.queryByText(tr("login.passkeyPromptTitle"))).toBeNull();
    expect(await screen.findByTestId("after-login")).toBeTruthy();
  });

  it("L10 auto create failed + no show_prompt: no prompt", async () => {
    mock.getPasskeyPrompt.mockResolvedValue({ can_auto: true, show_prompt: false });
    mock.autoRegisterPasskey.mockResolvedValue("failed");
    await renderLoginWithHome();
    await fillAndSubmit();
    await waitFor(() => expect(mock.autoRegisterPasskey).toHaveBeenCalledTimes(1));
    expect(screen.queryByText(tr("login.passkeyPromptTitle"))).toBeNull();
    expect(await screen.findByTestId("after-login")).toBeTruthy();
  });
});
