import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const mock = vi.hoisted(() => ({
  supported: true,
  get: vi.fn(),
  delete: vi.fn(),
  registerPasskey: vi.fn(),
}));

vi.mock("@simplewebauthn/browser", () => ({ browserSupportsWebAuthn: () => mock.supported }));
vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  api: { get: mock.get, delete: mock.delete },
}));
vi.mock("../../lib/auth/passkey", async (orig) => ({
  ...(await orig<typeof import("../../lib/auth/passkey")>()),
  registerPasskey: mock.registerPasskey,
}));

import { ApiError } from "../../lib/api";
import PasskeySection from "./PasskeySection";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));

const ITEMS = [
  { id: 1, label: "work iPhone", created_at: "2026-10-01T00:00:00Z", last_used_at: null },
  { id: 2, label: null, created_at: "2026-10-02T00:00:00Z", last_used_at: "2026-10-30T00:00:00Z" },
];

beforeEach(async () => {
  mock.supported = true;
  mock.get.mockReset().mockResolvedValue({ items: ITEMS });
  mock.delete.mockReset().mockResolvedValue(undefined);
  mock.registerPasskey.mockReset().mockResolvedValue(undefined);
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  render(<I18nextProvider i18n={instance}><PasskeySection /></I18nextProvider>);
});
afterEach(() => {
  cleanup();
});

describe("PasskeySection", () => {
  it("lists passkeys with fallback texts for missing name and last use", async () => {
    expect(await screen.findByText("work iPhone")).toBeTruthy();
    expect(screen.getByText(tr("accountSettings.passkeyUnnamed"))).toBeTruthy();
    expect(screen.getByText(tr("accountSettings.passkeyNeverUsed"))).toBeTruthy();
  });

  it("shows the empty state for zero passkeys", async () => {
    cleanup();
    mock.get.mockResolvedValue({ items: [] });
    render(<I18nextProvider i18n={instance}><PasskeySection /></I18nextProvider>);

    expect(await screen.findByText(tr("accountSettings.passkeyEmpty"))).toBeTruthy();
  });

  it("adds a passkey with the typed name and reloads the list", async () => {
    await screen.findByText("work iPhone");
    fireEvent.change(screen.getByLabelText(tr("accountSettings.passkeyLabel")), { target: { value: "my laptop" } });
    fireEvent.click(screen.getByRole("button", { name: tr("accountSettings.passkeyAdd") }));

    await waitFor(() => expect(mock.registerPasskey).toHaveBeenCalledWith("my laptop"));
    expect(await screen.findByText(tr("accountSettings.passkeyAdded"))).toBeTruthy();
    expect(mock.get).toHaveBeenCalledTimes(2);
  });

  it("deletes through the confirm dialog", async () => {
    await screen.findByText("work iPhone");
    fireEvent.click(screen.getAllByRole("button", { name: tr("accountSettings.passkeyDelete") })[0]);
    expect(screen.getByText(tr("accountSettings.passkeyDeleteMessage"))).toBeTruthy();
    expect(mock.delete).not.toHaveBeenCalled();

    const buttons = screen.getAllByRole("button", { name: tr("accountSettings.passkeyDelete") });
    fireEvent.click(buttons[buttons.length - 1]);

    await waitFor(() => expect(mock.delete).toHaveBeenCalledWith("/auth/passkeys/1"));
  });

  it("maps 409 limit and exists, and InvalidStateError, to their messages", async () => {
    await screen.findByText("work iPhone");
    const add = () => fireEvent.click(screen.getByRole("button", { name: tr("accountSettings.passkeyAdd") }));

    mock.registerPasskey.mockRejectedValueOnce(new ApiError("passkey_limit", 409, "passkey_limit"));
    add();
    expect(await screen.findByText(tr("authError.passkeyLimit"))).toBeTruthy();

    mock.registerPasskey.mockRejectedValueOnce(new ApiError("passkey_exists", 409, "passkey_exists"));
    add();
    expect(await screen.findByText(tr("authError.passkeyExists"))).toBeTruthy();

    cleanup();
    render(<I18nextProvider i18n={instance}><PasskeySection /></I18nextProvider>);
    await screen.findByText("work iPhone");
    mock.registerPasskey.mockRejectedValueOnce(Object.assign(new Error("x"), { name: "InvalidStateError" }));
    add();
    expect(await screen.findByText(tr("authError.passkeyExists"))).toBeTruthy();
  });

  it("shows the unsupported text instead of the add button when the browser lacks WebAuthn", () => {
    cleanup();
    mock.supported = false;
    render(<I18nextProvider i18n={instance}><PasskeySection /></I18nextProvider>);

    expect(screen.getByText(tr("accountSettings.passkeyUnsupported"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: tr("accountSettings.passkeyAdd") })).toBeNull();
  });
});
