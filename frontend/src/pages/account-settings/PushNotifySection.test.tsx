import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import en from "../../locales/en.json";

const mock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  support: "supported" as "supported" | "ios_needs_home_screen" | "unsupported",
  currentSubscription: vi.fn(),
  subscribeThisDevice: vi.fn(),
  unsubscribeThisDevice: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  api: { get: mock.get, post: mock.post, delete: mock.delete },
}));
vi.mock("../../lib/webPush", () => ({
  pushSupport: () => mock.support,
  currentSubscription: mock.currentSubscription,
  subscribeThisDevice: mock.subscribeThisDevice,
  unsubscribeThisDevice: mock.unsubscribeThisDevice,
}));

import PushNotifySection from "./PushNotifySection";

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));

function setPermission(permission: NotificationPermission) {
  vi.stubGlobal("Notification", { permission, requestPermission: vi.fn() });
}

function setApi(opts: { publicKey: string | null; current: boolean }) {
  mock.get.mockImplementation(async (path: string) => {
    if (path === "/auth/push-public-key") return { public_key: opts.publicKey };
    if (path === "/auth/devices") return { items: [{ id: 1, is_current: opts.current }] };
    throw new Error("unexpected " + path);
  });
}

async function mount() {
  render(
    <I18nextProvider i18n={instance}>
      <PushNotifySection />
    </I18nextProvider>,
  );
}

beforeEach(async () => {
  mock.get.mockReset();
  mock.post.mockReset();
  mock.delete.mockReset();
  mock.currentSubscription.mockReset().mockResolvedValue(null);
  mock.subscribeThisDevice.mockReset();
  mock.unsubscribeThisDevice.mockReset();
  mock.support = "supported";
  setPermission("default");
  instance = createInstance();
  await instance.init({ lng: "en", resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("PushNotifySection", () => {
  it("renders nothing when public_key is null", async () => {
    setApi({ publicKey: null, current: true });
    await mount();
    await waitFor(() => expect(mock.get).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(tr("accountSettings.push.title"))).toBeNull();
    expect(screen.queryByRole("switch")).toBeNull();
  });

  it("shows the iOS hint and no switch on ios_needs_home_screen", async () => {
    mock.support = "ios_needs_home_screen";
    setApi({ publicKey: "pk", current: true });
    await mount();
    expect(await screen.findByText(tr("accountSettings.push.iosHint"))).toBeTruthy();
    expect(screen.queryByRole("switch")).toBeNull();
  });

  it("shows notTrusted and a disabled switch when this device is not the regular one", async () => {
    setApi({ publicKey: "pk", current: false });
    await mount();
    expect(await screen.findByText(tr("accountSettings.push.notTrusted"))).toBeTruthy();
    expect((screen.getByRole("switch") as HTMLInputElement).disabled).toBe(true);
  });

  it("shows denied and a disabled switch when permission is denied", async () => {
    setPermission("denied");
    setApi({ publicKey: "pk", current: true });
    await mount();
    expect(await screen.findByText(tr("accountSettings.push.denied"))).toBeTruthy();
    expect((screen.getByRole("switch") as HTMLInputElement).disabled).toBe(true);
  });

  it("lets a regular device press the switch when supported", async () => {
    setApi({ publicKey: "pk", current: true });
    await mount();
    const toggle = (await screen.findByRole("switch")) as HTMLInputElement;
    expect(toggle.disabled).toBe(false);
    expect(toggle.checked).toBe(false);
    expect(screen.queryByText(tr("accountSettings.push.notTrusted"))).toBeNull();
  });
});
