import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
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
