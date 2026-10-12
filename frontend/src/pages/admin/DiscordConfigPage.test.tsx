import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import i18n from "../../i18n";
import DiscordConfigPage from "./DiscordConfigPage";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
  ApiError: class extends Error {},
}));
vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }));

const GUILD = "1288437029213835356";
const CATEGORY = "1288437029213835357";
const BUTTON_CH = "1288437029213835358";

const connectedConfig = { guild_id: GUILD, role_member: "Member", role_partner: "Partner" };
const unconnectedConfig = { guild_id: null, role_member: "Member", role_partner: "Partner" };
const emptyTicket = {
  ticket_category_id: null, ticket_button_channel_id: null, staff_role_id: null,
  welcome_template: "Hello", small_channel_id: null, large_channel_id: null,
  small_role_name: "Member", large_role_name: "Partner",
};
const filledTicket = { ...emptyTicket, ticket_category_id: CATEGORY, ticket_button_channel_id: BUTTON_CH };

const mockGets = (config: object, ticket: object) => {
  vi.mocked(api.get).mockImplementation(async (path: string) =>
    path === "/admin/discord-config" ? config : ticket,
  );
};
const view = () => render(<MemoryRouter><DiscordConfigPage /></MemoryRouter>);
const callsTo = (path: string) => vi.mocked(api.get).mock.calls.filter((c) => c[0] === path).length;

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(usePermissions).mockReturnValue({
    loading: false, hasPermission: () => true, hasAny: () => true,
  } as unknown as ReturnType<typeof usePermissions>);
  mockGets(connectedConfig, filledTicket);
});
afterEach(() => cleanup());

it("shows connected state with read-only server ID and a Change button", async () => {
  view();
  await screen.findByText(GUILD);
  expect(screen.getByText("Connected")).toBeTruthy();
  expect(screen.queryByLabelText("Server ID")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Change" }));
  expect((screen.getByLabelText("Server ID") as HTMLInputElement).value).toBe(GUILD);
  expect(screen.getByRole("button", { name: "Cancel" })).toBeTruthy();
});

it("shows unconnected state with a form and disables auto setup with a reason", async () => {
  mockGets(unconnectedConfig, emptyTicket);
  view();
  await screen.findByText("Not connected");
  expect(screen.getByLabelText("Server ID")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Connect" })).toBeTruthy();
  expect((screen.getByRole("button", { name: "Run auto setup" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("Connect the server first")).toBeTruthy();
});

it("rejects an invalid server ID without calling the API", async () => {
  mockGets(unconnectedConfig, emptyTicket);
  view();
  fireEvent.change(await screen.findByLabelText("Server ID"), { target: { value: "abc" } });
  fireEvent.click(screen.getByRole("button", { name: "Connect" }));
  expect(await screen.findByText("Enter a 17–20 digit number")).toBeTruthy();
  expect(api.put).not.toHaveBeenCalled();
});

it("groups auto setup results by kind with a badge per step and a next-step notice", async () => {
  vi.mocked(api.post).mockResolvedValue({
    status: "completed",
    role_order_guide_url: "https://example.com/guide",
    steps: [
      { step: "role_staff", status: "created" },
      { step: "role_partner", status: "skipped" },
      { step: "category", status: "updated" },
      { step: "ch_ticket", status: "failed", error: "Missing Access" },
      { step: "button", status: "posted" },
    ],
  });
  view();
  fireEvent.click(await screen.findByRole("button", { name: "Run auto setup" }));
  await screen.findByText("Completed");
  for (const title of ["Roles", "Categories", "Channels", "Button"]) {
    expect(screen.getByText(title)).toBeTruthy();
  }
  const row = (label: string) => screen.getByText(label).closest(".dc-step") as HTMLElement;
  expect(within(row("Sales Anchor Staff")).getByText("Created")).toBeTruthy();
  expect(within(row("Partner")).getByText("Exists")).toBeTruthy();
  expect(within(row("DM")).getByText("Updated")).toBeTruthy();
  expect(within(row("ticket-start")).getByText("Failed")).toBeTruthy();
  expect(within(row("Ticket start button")).getByText("Posted")).toBeTruthy();
  expect(screen.getByText("Missing Access")).toBeTruthy();
  expect(screen.getByText(/Move the Bot role above Partner/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "See how" }).getAttribute("href")).toBe("https://example.com/guide");
});

it("re-fetches both configs after auto setup instead of mirroring created steps", async () => {
  vi.mocked(api.post).mockResolvedValue({
    status: "partial", role_order_guide_url: "https://example.com/guide",
    steps: [{ step: "category", status: "skipped" }],
  });
  view();
  const run = await screen.findByRole("button", { name: "Run auto setup" });
  expect(callsTo("/admin/discord-config")).toBe(1);
  expect(callsTo("/admin/discord-ticket-config")).toBe(1);
  fireEvent.click(run);
  await screen.findByText("Partly failed");
  await waitFor(() => {
    expect(callsTo("/admin/discord-config")).toBe(2);
    expect(callsTo("/admin/discord-ticket-config")).toBe(2);
  });
});

it("keeps advanced settings collapsed until toggled (aria-expanded)", async () => {
  view();
  const toggle = await screen.findByRole("button", { name: /Advanced settings/ });
  expect(toggle.getAttribute("aria-expanded")).toBe("false");
  expect(screen.queryByLabelText("Staff role ID")).toBeNull();
  fireEvent.click(toggle);
  expect(toggle.getAttribute("aria-expanded")).toBe("true");
  for (const label of [
    "Where tickets go (category ID)", "Button channel ID", "Staff role ID",
    "Channel ID for small customers", "Channel ID for large customers",
    "Small role name", "Large role name",
  ]) {
    expect(screen.getByLabelText(label)).toBeTruthy();
  }
});

it("saves the welcome message and re-posts the button", async () => {
  vi.mocked(api.put).mockResolvedValue({ ...filledTicket, welcome_template: "Hi there" });
  vi.mocked(api.post).mockResolvedValue({});
  view();
  const area = await screen.findByLabelText("Ticket welcome message");
  fireEvent.change(area, { target: { value: "Hi there" } });
  expect(screen.getByText(/8\/500/)).toBeTruthy();
  fireEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);
  await screen.findByText("Saved");
  expect(vi.mocked(api.put).mock.calls[0][0]).toBe("/admin/discord-ticket-config");
  expect(vi.mocked(api.put).mock.calls[0][1]).toMatchObject({ welcome_template: "Hi there", ticket_category_id: CATEGORY });
  fireEvent.click(screen.getByRole("button", { name: "Re-post button" }));
  await screen.findByText("Posted");
  expect(api.post).toHaveBeenCalledWith("/admin/discord-ticket-config/deploy-button", {});
});

it("asks to run auto setup when required IDs are missing on save", async () => {
  mockGets(connectedConfig, emptyTicket);
  view();
  await screen.findByLabelText("Ticket welcome message");
  fireEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);
  expect(await screen.findByText("Run auto setup first")).toBeTruthy();
  expect(api.put).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "Re-post button" })).toBeNull();
});

it("hides edit controls without edit permission", async () => {
  vi.mocked(usePermissions).mockReturnValue({
    loading: false, hasPermission: () => false, hasAny: () => true,
  } as unknown as ReturnType<typeof usePermissions>);
  view();
  await screen.findByText(GUILD);
  expect(screen.queryByRole("button", { name: "Change" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Run auto setup" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
});
