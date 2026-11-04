/**
 * 単体試験用の開発ログイン。test-setup.ts が毎回の試験の前に登録する（今までの「開発中は偽ログイン」と同じ振る舞い）。
 * 自社ログインの動きを試す試験は、beforeEach で registerDevSession(null) を呼ぶ。
 */
import { vi } from "vitest";
import { registerDevSession, type DevSessionAdapter, type DevSessionUser } from "../lib/auth/devSessionSlot";

export const TEST_DEV_USER: DevSessionUser = {
  uid: "e2e-test-user-uid",
  email: "review@salesanchor.jp",
  displayName: "E2E Test User",
  emailVerified: true,
};

export function registerTestDevSession(overrides: Partial<DevSessionAdapter> = {}): DevSessionAdapter {
  const adapter: DevSessionAdapter = {
    getUser: () => (window.location.pathname === "/login" ? null : TEST_DEV_USER),
    subscribe: () => () => {},
    signIn: vi.fn(async () => undefined),
    signOut: vi.fn(async () => undefined),
    getAccessToken: async () => {
      const { default: i18n } = await import("../i18n");
      throw new Error(i18n.t("common.notAuthenticated"));
    },
    hasSession: () => false,
    ...overrides,
  };
  registerDevSession(adapter);
  return adapter;
}
