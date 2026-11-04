import type { Meta, StoryObj } from "@storybook/react-vite";
import { useTranslation } from "react-i18next";
import { NoticeRow } from "./NoticeRow";

type NoticeRowStoryProps = {
  unread: boolean;
  actor: string;
  channel: string;
  meta: string;
};

// 文言は t() 経由で作って渡す（NoticeBell と同じ作り方）
function NoticeRowStory({ unread, actor, channel, meta }: NoticeRowStoryProps) {
  const { t } = useTranslation();
  return (
    <NoticeRow
      title={t("notices.kind.discord_outside_ticket_post", { actor, channel })}
      meta={meta}
      unread={unread}
      onClick={() => undefined}
    />
  );
}

const meta = {
  title: "Components/NoticeRow",
  component: NoticeRowStory,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
  args: {
    unread: true,
    actor: "Sample",
    channel: "general",
    meta: "5m",
  },
} satisfies Meta<typeof NoticeRowStory>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Unread: Story = {};

export const Read: Story = { args: { unread: false } };
