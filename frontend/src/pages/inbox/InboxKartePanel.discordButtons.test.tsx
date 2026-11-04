import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import ja from "../../locales/ja.json";
import type { LeadDetail } from "./inbox.types";

let permissions: string[] = [];

// t resolves existing ja.json keys (no hard-coded labels in this test)
const lookup = (key: string): string => {
  const v = key.split(".").reduce<unknown>(
    (o, k) => (o && typeof o === "object" ? (o as Record<string, unknown>)[k] : undefined),
    ja,
  );
  return typeof v === "string" ? v : key;
};

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: lookup, i18n: { language: "ja" } }),
}));
vi.mock("../../hooks/usePermissions", () => ({
  usePermissions: () => ({ loading: false, hasPermission: (k: string) => permissions.includes(k) }),
}));
vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(() => Promise.resolve([])), post: vi.fn(() => Promise.resolve({})) },
}));

import { KarteTabContent } from "./InboxKartePanel";

const leadDetail = {
  id: 1,
  discord_user_id: "111",
  discord_guild_channel_id: "222",
  estimated_scale: "Small",
  discord_role_sync_status: "success",
  discord_role_sync_at: null,
} as unknown as LeadDetail;

function renderContact() {
  render(
    <KarteTabContent
      tab="contact"
      leadDetail={leadDetail}
      cardForm={{}}
      handleCardFieldChange={vi.fn()}
      handleCardFieldBlur={vi.fn()}
      guildId={null}
    />,
  );
}

const INVITE = lookup("leads.channelInviteSend");
const RESYNC = lookup("leads.discordRoleResync");
const REMOVE = lookup("leads.discordRemoveFromChannel");
const KICK = lookup("leads.discordKick");
const BAN = lookup("leads.discordBan");
const STATUS = lookup("leads.discordRoleSyncStatus");

describe("Karte Discord buttons by permission", () => {
  beforeEach(() => {
    permissions = [];
  });
  afterEach(cleanup);

  it("T1 no permission: no action buttons, status label shown", () => {
    renderContact();
    for (const label of [INVITE, RESYNC, REMOVE, KICK, BAN]) {
      expect(screen.queryByText(label)).toBeNull();
    }
    expect(screen.getByText(STATUS)).toBeTruthy();
  });

  it("T2 leads.update and leads.delete only: none of the five shown", () => {
    permissions = ["leads.update", "leads.delete"];
    renderContact();
    for (const label of [INVITE, RESYNC, REMOVE, KICK, BAN]) {
      expect(screen.queryByText(label)).toBeNull();
    }
  });

  it("T3 all five new keys: all five shown", () => {
    permissions = [
      "leads.discord_invite", "leads.discord_resync", "leads.discord_remove_channel",
      "leads.discord_kick", "leads.discord_ban",
    ];
    renderContact();
    for (const label of [INVITE, RESYNC, REMOVE, KICK, BAN]) {
      expect(screen.getByText(label)).toBeTruthy();
    }
  });

  it.each([
    ["leads.discord_invite", INVITE],
    ["leads.discord_resync", RESYNC],
    ["leads.discord_remove_channel", REMOVE],
    ["leads.discord_kick", KICK],
    ["leads.discord_ban", BAN],
  ])("T4 only %s: only its own button shown", (key, label) => {
    permissions = [key];
    renderContact();
    for (const l of [INVITE, RESYNC, REMOVE, KICK, BAN]) {
      if (l === label) expect(screen.getByText(l)).toBeTruthy();
      else expect(screen.queryByText(l)).toBeNull();
    }
    if (key === "leads.discord_remove_channel") {
      expect(screen.getByText(lookup("leads.discordRemove"))).toBeTruthy();
    }
  });
});
