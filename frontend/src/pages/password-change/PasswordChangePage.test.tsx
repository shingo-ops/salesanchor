import { cleanup, render, screen } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const mock = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, api: { get: mock.get, post: mock.post } };
});

import { registerDevSession } from "../../lib/auth/devSessionSlot";
import { expireSession } from "../../lib/auth/selfAuth";
import { registerTestDevSession } from "../../test-utils/devSession";
import PasswordChangePage from "./PasswordChangePage";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));

beforeEach(async () => {
  mock.post.mockReset();
  mock.get.mockReset();
  expireSession();
  registerDevSession(null);
  registerTestDevSession();
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(() => {
  cleanup();
  expireSession();
  registerDevSession(null);
});

describe("PasswordChangePage", () => {
  it("shows the three password fields and the sign-out button, and calls no other API", () => {
    render(
      <I18nextProvider i18n={instance}>
        <MemoryRouter>
          <PasswordChangePage />
        </MemoryRouter>
      </I18nextProvider>,
    );

    expect(screen.getByLabelText(tr("accountSettings.currentPassword"))).toBeTruthy();
    expect(screen.getByLabelText(tr("accountSettings.newPassword"))).toBeTruthy();
    expect(screen.getByLabelText(tr("accountSettings.confirmPassword"))).toBeTruthy();
    expect(screen.getByRole("button", { name: tr("accountSettings.changePassword") })).toBeTruthy();
    expect(screen.getByRole("button", { name: tr("passwordChangePage.signOut") })).toBeTruthy();
    expect(mock.get).not.toHaveBeenCalled();
    expect(mock.post).not.toHaveBeenCalled();
  });
});
