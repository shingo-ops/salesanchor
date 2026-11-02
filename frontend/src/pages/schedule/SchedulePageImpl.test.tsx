import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import SchedulePage from "./SchedulePageImpl";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { uid: "user-a" } }),
}));

const answers = vi.hoisted(() => ({
  isTenantAdmin: false,
  connected: false,
}));

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(async (path: string) => {
      if (path === "/me/permissions") return { permissions: [], is_tenant_admin: answers.isTenantAdmin };
      if (path === "/google-calendar/status") return { connected: answers.connected };
      if (path === "/google-calendar/connect/start") return { auth_url: "https://accounts.example/auth" };
      return [];
    }),
    post: vi.fn(async () => ({})),
    patch: vi.fn(async () => ({})),
    put: vi.fn(async () => ({})),
    delete: vi.fn(async () => ({})),
  },
}));

import { api } from "../../lib/api";
const mockGet = vi.mocked(api.get);

const originalLocation = window.location;
const hrefSetter = vi.fn();

beforeEach(async () => {
  await i18n.changeLanguage("ja");
  answers.isTenantAdmin = false;
  answers.connected = false;
  hrefSetter.mockReset();
  const fake = { ...window.location } as Record<string, unknown>;
  Object.defineProperty(fake, "href", { configurable: true, get: () => "http://localhost/", set: hrefSetter });
  Object.defineProperty(window, "location", { configurable: true, value: fake });
});

afterEach(() => {
  Object.defineProperty(window, "location", { configurable: true, value: originalLocation });
  cleanup();
  vi.clearAllMocks();
  queryClient.clear();
});

const view = () => render(<MemoryRouter><SchedulePage /></MemoryRouter>);

describe("SchedulePage Google calendar connect button", () => {
  it("shows an enabled button to a tenant admin and starts the connect flow on click", async () => {
    answers.isTenantAdmin = true;
    view();
    const btn = await screen.findByRole("button", { name: i18n.t("schedule.connectBtn") });
    await waitFor(() => expect((btn as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(btn);
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/google-calendar/connect/start"));
    await waitFor(() => expect(hrefSetter).toHaveBeenCalledWith("https://accounts.example/auth"));
  });

  it("shows a disabled connected label when already connected", async () => {
    answers.isTenantAdmin = true;
    answers.connected = true;
    view();
    const btn = await screen.findByRole("button", { name: i18n.t("schedule.connectBtnConnected") });
    expect((btn as HTMLButtonElement).disabled).toBe(true);
  });

  it("hides the button and never asks for status when not a tenant admin", async () => {
    answers.isTenantAdmin = false;
    view();
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/me/permissions"));
    await waitFor(() => expect(mockGet.mock.calls.length).toBeGreaterThan(1));
    expect(screen.queryByRole("button", { name: i18n.t("schedule.connectBtn") })).toBeNull();
    expect(mockGet).not.toHaveBeenCalledWith("/google-calendar/status");
  });
});
