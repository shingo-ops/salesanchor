/**
 * HoverCard — ストーリーカタログ
 */
import type { Meta, StoryObj } from "@storybook/react-vite";
import { HoverCard, HoverCardHost } from "./HoverCard";

const meta: Meta<typeof HoverCard> = {
  title: "Components/HoverCard",
  component: HoverCard,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  args: { delay: 150, onlyWhenClipped: true },
};
export default meta;

type Story = StoryObj<typeof HoverCard>;

const clipStyle = {
  width: "160px",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
} as const;

// ── 切れる長い名前（ホバーでカードが出る） ──────────────────────────────
export const Default: Story = {
  args: {
    title: "ポケモンカードゲーム 拡張パック 超電ブレイカー BOX シュリンク付き",
    subtitle: "Pokemon Card Game Expansion Pack Super Electric Breaker Box",
  },
  render: (args) => (
    <>
      <HoverCard {...args}>
        <div data-hover-card-clip style={clipStyle}>
          {args.title}
        </div>
      </HoverCard>
      <HoverCardHost />
    </>
  ),
};

// ── 切れない名前（何も出ない） ───────────────────────────────────────────
export const Short: Story = {
  args: { title: "短い名前", subtitle: "Short name" },
  render: (args) => (
    <>
      <HoverCard {...args}>
        <div data-hover-card-clip style={clipStyle}>
          {args.title}
        </div>
      </HoverCard>
      <HoverCardHost />
    </>
  ),
};
