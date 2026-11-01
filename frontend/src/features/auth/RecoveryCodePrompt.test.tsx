import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("../../lib/api", () => ({ api }));
vi.mock("../../lib/auth/provider", () => ({ isSelfAuth: () => true }));
vi.mock("../../lib/firebase", () => ({ auth: { currentUser: null } }));

import { adoptAccessToken, expireSession } from "../../lib/auth/selfAuth";
import RecoveryCodePrompt, { clearRecoveryPromptMarks, recoveryPromptKey } from "./RecoveryCodePrompt";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));

function jwt(claims: Record<string, unknown>): string {
  const enc = (o: unknown) => btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  return `${enc({ alg: "HS256" })}.${enc(claims)}.sig`;
}

function renderPrompt() {
  render(
    <I18nextProvider i18n={instance}>
      <RecoveryCodePrompt />
    </I18nextProvider>,
  );
}

beforeEach(async () => {
  localStorage.clear();
  api.get.mockReset();
  api.post.mockReset();
  adoptAccessToken(jwt({ sub: "7", email: "a@example.com", sid: "fam-1" }), 900);
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(() => {
  cleanup();
  expireSession();
  localStorage.clear();
});

describe("RecoveryCodePrompt", () => {
  it("asks once when no recovery code remains, and remembers it per user and session", async () => {
    api.get.mockResolvedValue({ remaining: 0 });
    renderPrompt();
    await screen.findByText(tr("accountSettings.recoveryCodes.promptBody"));
    expect(localStorage.getItem(recoveryPromptKey("7", "fam-1"))).not.toBeNull();

    cleanup();
    api.get.mockClear();
    renderPrompt();
    expect(api.get).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("does not ask when codes remain", async () => {
    api.get.mockResolvedValue({ remaining: 3 });
    renderPrompt();
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows the created codes once", async () => {
    api.get.mockResolvedValue({ remaining: 0 });
    api.post.mockResolvedValue({ codes: ["AAAA-BBBBB-CCCCC"] });
    renderPrompt();
    fireEvent.click(await screen.findByRole("button", { name: tr("accountSettings.recoveryCodes.promptCreate") }));
    await screen.findByText("AAAA-BBBBB-CCCCC");
  });

  it("uses the user id alone as the key for an old token without sid", () => {
    expect(recoveryPromptKey("7", null)).toBe("recoveryPrompt:7:");
  });

  it("clears every mark of the user on sign-in or sign-out", () => {
    localStorage.setItem(recoveryPromptKey("7", "a"), "1");
    localStorage.setItem(recoveryPromptKey("7", "b"), "1");
    localStorage.setItem(recoveryPromptKey("8", "a"), "1");
    clearRecoveryPromptMarks("7");
    expect(localStorage.getItem(recoveryPromptKey("7", "a"))).toBeNull();
    expect(localStorage.getItem(recoveryPromptKey("7", "b"))).toBeNull();
    expect(localStorage.getItem(recoveryPromptKey("8", "a"))).not.toBeNull();
  });
});
