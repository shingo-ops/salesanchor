import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "i18next";
import "./i18n";
import { ViewerApiError } from "./api";
import ViewerApp from "./ViewerApp";

const apiMock = vi.hoisted(() => ({ signup: vi.fn() }));
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

const openSignup = () => {
  render(<ViewerApp />);
  fireEvent.click(screen.getByTestId("viewer-login-signup"));
};

const fillAndSubmit = () => {
  typeInto(k("viewer.login.email"), "  a@x.com ");
  typeInto(k("viewer.signup.lineName"), " Taro ");
  typeInto(k("viewer.signup.inventoryIssue"), "stock issue");
  fireEvent.submit(screen.getByTestId("viewer-signup"));
};

beforeEach(() => {
  apiMock.signup.mockReset();
  window.localStorage.clear();
  window.history.replaceState(null, "", "/");
});
afterEach(() => cleanup());

describe("signup", () => {
  it("switches from the login screen to the signup screen", () => {
    openSignup();
    expect(screen.getByTestId("viewer-signup")).toBeTruthy();
  });

  it("sends email, line_name, inventory_issue and website", async () => {
    apiMock.signup.mockResolvedValue({ signup_code: "ABCD-EFGH-JKMN-PQRS", expires_at: "2026-10-24T00:00:00+00:00", invite_url: null });
    openSignup();
    fillAndSubmit();
    await waitFor(() => expect(apiMock.signup).toHaveBeenCalledTimes(1));
    expect(apiMock.signup).toHaveBeenCalledWith({
      email: "a@x.com",
      line_name: "Taro",
      inventory_issue: "stock issue",
      website: "",
    });
  });

  it("shows the code and an invite button that opens a new tab", async () => {
    apiMock.signup.mockResolvedValue({
      signup_code: "ABCD-EFGH-JKMN-PQRS",
      expires_at: "2026-10-24T00:00:00+00:00",
      invite_url: "https://discord.gg/xyz",
    });
    openSignup();
    fillAndSubmit();
    expect((await screen.findByTestId("viewer-signup-code")).textContent).toBe("ABCD-EFGH-JKMN-PQRS");
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    fireEvent.click(screen.getByTestId("viewer-signup-invite"));
    expect(open).toHaveBeenCalledTimes(1);
    expect(open).toHaveBeenCalledWith("https://discord.gg/xyz", "_blank", "noopener,noreferrer");
    expect(screen.getByTestId("viewer-signup-invite-url").textContent).toBe("https://discord.gg/xyz");
    open.mockRestore();
    expect(screen.getByTestId("viewer-signup-done").textContent).toContain(k("viewer.signup.alreadyApplied"));
  });

  it("shows the failure text and no link when invite_url is null", async () => {
    apiMock.signup.mockResolvedValue({ signup_code: "ABCD-EFGH-JKMN-PQRS", expires_at: "2026-10-24T00:00:00+00:00", invite_url: null });
    openSignup();
    fillAndSubmit();
    expect((await screen.findByTestId("viewer-signup-invite-failed")).textContent).toBe(k("viewer.signup.inviteFailed"));
    expect(screen.queryByTestId("viewer-signup-invite")).toBeNull();
  });

  it("maps 422 and 429 to their messages", async () => {
    apiMock.signup.mockRejectedValueOnce(new ViewerApiError(422, "viewer_signup_invalid"));
    openSignup();
    fillAndSubmit();
    expect((await screen.findByTestId("viewer-signup-error")).textContent).toBe(k("viewer.error.validation"));
    apiMock.signup.mockRejectedValueOnce(new ViewerApiError(429, "viewer_too_many_attempts"));
    fireEvent.submit(screen.getByTestId("viewer-signup"));
    await waitFor(() =>
      expect(screen.getByTestId("viewer-signup-error").textContent).toBe(k("viewer.error.viewer_too_many_attempts")),
    );
  });

  it("goes back to login from the form and from the result", async () => {
    apiMock.signup.mockResolvedValue({ signup_code: "ABCD-EFGH-JKMN-PQRS", expires_at: "2026-10-24T00:00:00+00:00", invite_url: null });
    openSignup();
    fireEvent.click(screen.getByTestId("viewer-signup-back"));
    expect(screen.getByTestId("viewer-login")).toBeTruthy();
    fireEvent.click(screen.getByTestId("viewer-login-signup"));
    fillAndSubmit();
    fireEvent.click(await screen.findByTestId("viewer-signup-to-login"));
    expect(screen.getByTestId("viewer-login")).toBeTruthy();
  });
});

describe("ViewerApp #signup link", () => {
  it("opens the signup screen directly and removes the hash", async () => {
    window.history.replaceState(null, "", "/viewer/#signup");
    const spy = vi.spyOn(window.history, "replaceState");
    render(<ViewerApp />);
    expect(screen.getByTestId("viewer-signup")).toBeTruthy();
    expect(screen.queryByTestId("viewer-login")).toBeNull();
    await waitFor(() => expect(spy).toHaveBeenCalledWith(null, "", "/viewer/"));
    expect(window.location.hash).toBe("");
    spy.mockRestore();
  });

  it("shows the login screen when there is no hash", () => {
    render(<ViewerApp />);
    expect(screen.getByTestId("viewer-login")).toBeTruthy();
    expect(screen.queryByTestId("viewer-signup")).toBeNull();
  });
});
