import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import { DiscordOwnServerPanel } from "./DiscordOwnServerPanel";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }));

const GUILD = "222222222222222222";
const SNAPSHOT_PATH = "/admin/discord/own-server/snapshot";

const mockConfig = (guildId: string | null) => {
  vi.mocked(api.get).mockImplementation(async (path: string) =>
    path === "/admin/discord-config/own" ? { guild_id: guildId, connected_at: null } : {},
  );
};
const mockPerms = (allowed: (key: string) => boolean) => {
  vi.mocked(usePermissions).mockReturnValue({
    loading: false, hasPermission: allowed, hasAny: () => true,
  } as unknown as ReturnType<typeof usePermissions>);
};
const view = () => render(<MemoryRouter><DiscordOwnServerPanel /></MemoryRouter>);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  mockPerms(() => true);
  mockConfig(GUILD);
});
afterEach(() => { cleanup(); queryClient.clear(); });

it("posts the snapshot request and shows the counts", async () => {
  vi.mocked(api.post).mockResolvedValue({ snapshot_id: 1, role_count: 3, channel_count: 2 });
  view();
  fireEvent.click(await screen.findByText("Read the current server"));
  await screen.findByText("Read the server (3 roles, 2 channels)");
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(api.post).toHaveBeenCalledWith(SNAPSHOT_PATH, {});
});

it("shows an error message when the snapshot request fails", async () => {
  vi.mocked(api.post).mockRejectedValue(new Error("boom"));
  view();
  fireEvent.click(await screen.findByText("Read the current server"));
  await screen.findByText("Could not read the server");
});

it("hides the button without edit permission", async () => {
  mockPerms((key) => key !== "tenant.profile.edit");
  view();
  await screen.findByText(GUILD);
  await waitFor(() => expect(screen.queryByText("Read the current server")).toBeNull());
});

it("hides the button when no server is registered", async () => {
  mockConfig(null);
  view();
  await screen.findByText("Not connected");
  expect(screen.queryByText("Read the current server")).toBeNull();
});

const PLAN_PATH = "/admin/discord/own-server/plan";
const emptyPlan = { plan_digest: "d".repeat(64), changes: [], blocked: [], delete_candidates: [], app_roles: [] };
const mockPlan = (plan: unknown) => {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/admin/discord-config/own") return { guild_id: GUILD, connected_at: null };
    if (path === PLAN_PATH) return plan;
    return {};
  });
};

it("shows changes, blocked rows and delete candidates after Check", async () => {
  mockPlan({
    plan_digest: "d".repeat(64),
    changes: [
      { kind: "create_role", key: "r1", name: "NewRole", field: null, before: null, after: "name=NewRole" },
    ],
    blocked: [
      { kind: "update_role", key: "r2", name: "BlockedRole", field: "name", before: "a", after: "b", reason: "role_above_bot" },
    ],
    delete_candidates: [
      { kind: "channel", discord_id: "55", name: "old-channel", parent_name: "OldCat", target: null },
    ],
    app_roles: [],
  });
  view();
  fireEvent.click(await screen.findByText("Check"));
  await screen.findByText("Changes (1)");
  await screen.findByText("Not allowed (1, will not run)");
  await screen.findByText("Delete candidates (1)");
  expect(api.get).toHaveBeenCalledWith(PLAN_PATH);
  expect(screen.getByText("Create role")).toBeTruthy();
  expect(screen.getByText("BlockedRole")).toBeTruthy();
  expect(screen.getByText("The role is at or above the bot's role")).toBeTruthy();
  expect(screen.getByText("old-channel")).toBeTruthy();
  expect(screen.getByText("OldCat")).toBeTruthy();
  expect(screen.getByText("Delete candidates are never deleted automatically.")).toBeTruthy();
});

it("shows None for each empty group", async () => {
  mockPlan(emptyPlan);
  view();
  fireEvent.click(await screen.findByText("Check"));
  await screen.findByText("Changes (0)");
  expect(await screen.findAllByText("None")).toHaveLength(4);
});

it("shows app roles with their state and reason after Check", async () => {
  mockPlan({
    plan_digest: "f".repeat(64),
    changes: [],
    blocked: [],
    delete_candidates: [],
    app_roles: [
      { role_id: 1, name: "Sales", state: "create", reason: null },
      { role_id: 2, name: "Office", state: "blocked", reason: "ambiguous" },
    ],
  });
  view();
  fireEvent.click(await screen.findByText("Check"));
  await screen.findByText("App roles (2)");
  expect((await screen.findAllByText("Sales")).length).toBeGreaterThanOrEqual(1);
  expect((await screen.findAllByText("Office")).length).toBeGreaterThanOrEqual(1);
  expect((await screen.findAllByText("Create")).length).toBeGreaterThanOrEqual(1);
  expect((await screen.findAllByText("Cannot")).length).toBeGreaterThanOrEqual(1);
  expect((await screen.findAllByText("More than one item has this name")).length).toBeGreaterThanOrEqual(1);
});

it("shows an error message when the check fails", async () => {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/admin/discord-config/own") return { guild_id: GUILD, connected_at: null };
    throw new Error("boom");
  });
  view();
  fireEvent.click(await screen.findByText("Check"));
  await screen.findByText("Could not check");
});

it("hides Check without edit permission", async () => {
  mockPerms((key) => key !== "tenant.profile.edit");
  view();
  await screen.findByText(GUILD);
  await waitFor(() => expect(screen.queryByText("Check")).toBeNull());
});

it("disables Apply when there are no changes", async () => {
  mockPlan(emptyPlan);
  view();
  fireEvent.click(await screen.findByText("Check"));
  await screen.findByText("Changes (0)");
  const apply = screen.getByRole("button", { name: "Apply" }) as HTMLButtonElement;
  expect(apply.disabled).toBe(true);
});

const APPLY_PATH = "/admin/discord/own-server/apply";
const twoChangesPlan = {
  plan_digest: "e".repeat(64),
  changes: [
    { kind: "create_role", key: "r1", name: "NewRole", field: null, before: null, after: "name=NewRole" },
    { kind: "create_channel", key: "c1", name: "news", field: null, before: null, after: "name=news" },
  ],
  blocked: [],
  delete_candidates: [],
  app_roles: [],
};
const checkAndOpenApply = async () => {
  view();
  fireEvent.click(await screen.findByText("Check"));
  await screen.findByText("Changes (2)");
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  await screen.findByText("2 changes will be applied. Delete candidates are not deleted.");
  const applyButtons = screen.getAllByText("Apply");
  fireEvent.click(applyButtons[applyButtons.length - 1]);
};

it("applies after confirmation and shows the result table", async () => {
  mockPlan(twoChangesPlan);
  vi.mocked(api.post).mockResolvedValue({
    run_id: 1,
    success_count: 1,
    blocked_count: 0,
    failed_count: 1,
    results: [
      { kind: "create_role", key: "r1", name: "NewRole", field: null, status: "success", reason: null, discord_id: "900", discord_status: null },
      { kind: "create_channel", key: "c1", name: "news", field: null, status: "failed", reason: "discord_error", discord_id: null, discord_status: 403 },
    ],
  });
  await checkAndOpenApply();
  await screen.findByText("Applied (1 succeeded, 0 not allowed, 1 failed)");
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(api.post).toHaveBeenCalledWith(APPLY_PATH, { plan_digest: twoChangesPlan.plan_digest });
  expect(await screen.findByText("Succeeded")).toBeTruthy();
  expect(screen.getByText("Failed")).toBeTruthy();
  expect(screen.getByText("Discord rejected the request")).toBeTruthy();
});

it("tells the user to check again when apply returns 409", async () => {
  mockPlan(twoChangesPlan);
  vi.mocked(api.post).mockRejectedValue(Object.assign(new ApiError("conflict", 409, null), { status: 409 }));
  await checkAndOpenApply();
  await screen.findByText("Could not apply. Press Check again, then apply");
});

it("hides Apply without edit permission", async () => {
  mockPerms((key) => key !== "tenant.profile.edit");
  view();
  await screen.findByText(GUILD);
  await waitFor(() => expect(screen.queryByText("Apply")).toBeNull());
});

it("shows the plain sentence for the reason when returning from Discord", async () => {
  window.history.pushState({}, "", "/admin/discord-config?tab=own&discord_status=error&reason=invalid_state");
  view();
  await screen.findByText(i18n.t("discordConnect.error.stateExpired"));
});

it("shows the plain sentence when starting the invite fails", async () => {
  mockConfig(null);
  vi.mocked(api.post).mockRejectedValue(
    Object.assign(new ApiError("x", 503, null), { responseDetail: { reason: "redis_error" } }),
  );
  view();
  fireEvent.click(await screen.findByText("Invite the bot to your own server"));
  await screen.findByText(i18n.t("discordConnect.error.serviceUnavailable"));
});
