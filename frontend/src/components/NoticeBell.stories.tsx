import { useEffect } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import NoticeBell, { type NoticeItem } from "./NoticeBell";
import { api } from "../lib/api";

const NOW = Date.now();

const MOCK_ITEMS: NoticeItem[] = [
  {
    id: 1,
    kind: "discord_outside_ticket_post",
    actor_name: "Sample A",
    channel_name: "general",
    link_url: null,
    created_at: new Date(NOW - 5 * 60_000).toISOString(),
    read_at: null,
  },
  {
    id: 2,
    kind: "discord_outside_ticket_post",
    actor_name: "Sample B",
    channel_name: "support",
    link_url: null,
    created_at: new Date(NOW - 3 * 3_600_000).toISOString(),
    read_at: new Date(NOW - 2 * 3_600_000).toISOString(),
  },
];

type NoticeBellStoryProps = { items: NoticeItem[]; unreadCount: number };

// API はモック（この story の間だけ api.get / api.post を差し替える）
function NoticeBellStory({ items, unreadCount }: NoticeBellStoryProps) {
  const originalGet = api.get;
  const originalPost = api.post;
  api.get = (async () => ({ items, unread_count: unreadCount })) as typeof api.get;
  api.post = (async () => ({ unread_count: Math.max(unreadCount - 1, 0) })) as typeof api.post;

  useEffect(
    () => () => {
      api.get = originalGet;
      api.post = originalPost;
    },
    [originalGet, originalPost],
  );

  return <NoticeBell />;
}

const meta = {
  title: "Components/NoticeBell",
  component: NoticeBellStory,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
  args: { items: MOCK_ITEMS, unreadCount: 1 },
} satisfies Meta<typeof NoticeBellStory>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithUnread: Story = {};

export const AllRead: Story = {
  args: { items: MOCK_ITEMS.map((n) => ({ ...n, read_at: n.created_at })), unreadCount: 0 },
};

export const Empty: Story = { args: { items: [], unreadCount: 0 } };

export const OverNinetyNine: Story = { args: { unreadCount: 120 } };
