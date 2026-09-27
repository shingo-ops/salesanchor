/**
 * Tooltip — ストーリーカタログ
 */
import type { Meta, StoryObj } from "@storybook/react-vite";
import { Tooltip } from "./Tooltip";

const meta: Meta<typeof Tooltip> = {
  title: "Components/Tooltip",
  component: Tooltip,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  args: {
    content: "ツールチップのテキスト",
    placement: "top",
    delay: 150,
  },
};
export default meta;

type Story = StoryObj<typeof Tooltip>;

// ── 基本表示 ──────────────────────────────────────────────────────────────
export const Default: Story = {
  render: (args) => (
    <Tooltip {...args}>
      <button type="button">ホバーで表示</button>
    </Tooltip>
  ),
};

// ── placement 2種 ─────────────────────────────────────────────────────────
export const Placements: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "32px" }}>
      <Tooltip content="上に表示" placement="top">
        <button type="button">top</button>
      </Tooltip>
      <Tooltip content="下に表示" placement="bottom">
        <button type="button">bottom</button>
      </Tooltip>
    </div>
  ),
};
