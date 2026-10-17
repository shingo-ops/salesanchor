import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "i18next";
import "./i18n";
import { ViewerApiError } from "./api";
import { PasswordChangeView } from "./PasswordChangeView";
import { PasswordResetView } from "./PasswordResetView";
import ViewerApp from "./ViewerApp";

const apiMock = vi.hoisted(() => ({
  changePassword: vi.fn(),
  requestPasswordReset: vi.fn(),
  confirmPasswordReset: vi.fn(),
}));
vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, ...apiMock };
});

const k = (key: string): string => i18n.t(key);

const typeInto = (label: string, value: string) => {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const input = screen.getByLabelText(new RegExp(`^${escaped}\\*?$`)) as HTMLInputElement;
  fireEvent.change(input, { target: { value } });
};

beforeEach(() => {
  apiMock.changePassword.mockReset();
  apiMock.requestPasswordReset.mockReset();
  apiMock.confirmPasswordReset.mockReset();
  window.localStorage.clear();
  window.history.replaceState(null, "", "/");
});
afterEach(() => cleanup());

describe("PasswordChangeView", () => {
  it("shows an error and does not call the API when the confirmation differs", async () => {
    render(<PasswordChangeView forced={false} onDone={() => undefined} onBack={() => undefined} onLogout={() => undefined} />);
    typeInto(k("viewer.passwordChange.current"), "old-password-0000");
    typeInto(k("viewer.passwordChange.new"), "new-password-1111-aaaa");
    typeInto(k("viewer.passwordChange.confirm"), "different-2222-bbbb");
    fireEvent.submit(screen.getByTestId("viewer-password-change"));
    expect((await screen.findByTestId("viewer-password-error")).textContent).toContain(k("viewer.passwordChange.mismatch"));
    expect(apiMock.changePassword).not.toHaveBeenCalled();
  });

  it("calls onDone with the new token on success", async () => {
    apiMock.changePassword.mockResolvedValue({ access_token: "NEW", must_change_password: false });
    const onDone = vi.fn();
    render(<PasswordChangeView forced={false} onDone={onDone} onBack={() => undefined} onLogout={() => undefined} />);
    typeInto(k("viewer.passwordChange.current"), "old-password-0000");
    typeInto(k("viewer.passwordChange.new"), "new-password-1111-aaaa");
    typeInto(k("viewer.passwordChange.confirm"), "new-password-1111-aaaa");
    fireEvent.submit(screen.getByTestId("viewer-password-change"));
    await waitFor(() => expect(onDone).toHaveBeenCalledWith("NEW"));
  });

  it("forced: shows the first-time notice and logout, hides back", () => {
    render(<PasswordChangeView forced onDone={() => undefined} onBack={() => undefined} onLogout={() => undefined} />);
    expect(screen.getByTestId("viewer-password-forced").textContent).toContain(k("viewer.passwordChange.forced"));
    expect(screen.getByTestId("viewer-password-logout")).toBeTruthy();
    expect(screen.queryByTestId("viewer-password-back")).toBeNull();
  });

  it("maps a 422 code to its message", async () => {
    apiMock.changePassword.mockRejectedValue(new ViewerApiError(422, "password_too_short"));
    render(<PasswordChangeView forced={false} onDone={() => undefined} onBack={() => undefined} onLogout={() => undefined} />);
    typeInto(k("viewer.passwordChange.current"), "old-password-0000");
    typeInto(k("viewer.passwordChange.new"), "short");
    typeInto(k("viewer.passwordChange.confirm"), "short");
    fireEvent.submit(screen.getByTestId("viewer-password-change"));
    expect((await screen.findByTestId("viewer-password-error")).textContent).toContain(k("viewer.error.password_too_short"));
  });
});

describe("PasswordResetView", () => {
  it("after a request, always shows the 30-minute mail notice", async () => {
    apiMock.requestPasswordReset.mockResolvedValue({ status: "accepted" });
    render(<PasswordResetView token={null} onToLogin={() => undefined} />);
    typeInto(k("viewer.login.email"), "a@example.com");
    fireEvent.submit(screen.getByTestId("viewer-reset-request"));
    const sent = await screen.findByTestId("viewer-reset-sent");
    expect(sent.textContent).toContain(k("viewer.reset.sentDescription"));
    expect(apiMock.requestPasswordReset).toHaveBeenCalledWith("a@example.com");
  });

  it("a 400 on confirm shows the invalid-link screen with a way to send again", async () => {
    apiMock.confirmPasswordReset.mockRejectedValue(new ViewerApiError(400, "viewer_reset_invalid_or_expired"));
    render(<PasswordResetView token="TKN" onToLogin={() => undefined} />);
    typeInto(k("viewer.passwordChange.new"), "new-password-1111-aaaa");
    typeInto(k("viewer.passwordChange.confirm"), "new-password-1111-aaaa");
    fireEvent.submit(screen.getByTestId("viewer-reset-new"));
    expect(await screen.findByTestId("viewer-reset-invalid")).toBeTruthy();
    expect(apiMock.confirmPasswordReset).toHaveBeenCalledWith("TKN", "new-password-1111-aaaa");
    fireEvent.click(screen.getByTestId("viewer-reset-again"));
    expect(screen.getByTestId("viewer-reset-request")).toBeTruthy();
  });

  it("success shows the done screen", async () => {
    apiMock.confirmPasswordReset.mockResolvedValue({ status: "ok" });
    render(<PasswordResetView token="TKN" onToLogin={() => undefined} />);
    typeInto(k("viewer.passwordChange.new"), "new-password-1111-aaaa");
    typeInto(k("viewer.passwordChange.confirm"), "new-password-1111-aaaa");
    fireEvent.submit(screen.getByTestId("viewer-reset-new"));
    expect(await screen.findByTestId("viewer-reset-done")).toBeTruthy();
  });
});

describe("ViewerApp reset link", () => {
  it("reads #reset= then removes the hash with history.replaceState", async () => {
    window.history.replaceState(null, "", "/viewer#reset=ABC123");
    const spy = vi.spyOn(window.history, "replaceState");
    render(<ViewerApp />);
    expect(screen.getByTestId("viewer-reset-new")).toBeTruthy();
    await waitFor(() => expect(spy).toHaveBeenCalledWith(null, "", "/viewer"));
    expect(window.location.hash).toBe("");
    spy.mockRestore();
  });
});
