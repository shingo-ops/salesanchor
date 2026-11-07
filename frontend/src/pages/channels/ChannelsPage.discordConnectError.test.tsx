import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import i18n from "../../i18n";
import { queryClient } from "../../lib/query/apiQuery";
import ChannelsPage from "./ChannelsPage";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }));

const mockGet = () => {
  vi.mocked(api.get).mockImplementation(async (path: string) => {
    if (path === "/meta/channels") return { channels: [] };
    if (path === "/admin/discord-config") {
      return { guild_id: null, connected_at: null, connected_by_staff_name: null };
    }
    return {};
  });
};
const mockPerms = () => {
  vi.mocked(usePermissions).mockReturnValue({
    loading: false, hasPermission: () => true, hasAny: () => true,
  } as unknown as ReturnType<typeof usePermissions>);
};
const view = () => render(<MemoryRouter><ChannelsPage /></MemoryRouter>);

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  mockPerms();
  mockGet();
});
afterEach(() => { cleanup(); queryClient.clear(); });

it("shows the plain sentence for invalid_state when returning from Discord", async () => {
  window.history.pushState({}, "", "/channels?discord_status=error&reason=invalid_state");
  view();
  await screen.findByText(i18n.t("discordConnect.error.stateExpired"));
});

it("shows the same sentence as the own-server panel for guild_already_registered", async () => {
  window.history.pushState({}, "", "/channels?discord_status=error&reason=guild_already_registered");
  view();
  await screen.findByText(i18n.t("discordConnect.error.serverAlreadyRegistered"));
});

it("shows the plain sentence when starting the connection fails", async () => {
  window.history.pushState({}, "", "/channels");
  vi.mocked(api.post).mockRejectedValue(
    Object.assign(new ApiError("x", 403, null), { responseDetail: { reason: "permission_denied" } }),
  );
  view();
  fireEvent.click(await screen.findByText(i18n.t("channels.discordAddBot")));
  await screen.findByText(i18n.t("discordConnect.error.permissionDenied"));
});
