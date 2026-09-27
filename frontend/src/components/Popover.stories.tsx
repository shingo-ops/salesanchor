/**
 * Popover — ストーリーカタログ
 */
import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { Popover } from "./Popover";

const meta: Meta<typeof Popover> = {
  title: "Components/Popover",
  component: Popover,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
};
export default meta;

type Story = StoryObj<typeof Popover>;

const SampleContent = () => (
  <div style={{ padding: "8px", minWidth: "160px" }}>
    <p style={{ margin: 0, fontSize: "14px" }}>ポップオーバーコンテンツ</p>
  </div>
);

// ── 基本表示 ──────────────────────────────────────────────────────────────
export const Default: Story = {
  args: {
    content: <SampleContent />,
    placement: "bottom",
  },
  render: (args) => (
    <Popover {...args}>
      <button type="button">クリックで開く</button>
    </Popover>
  ),
};

// ── placement 4種 ─────────────────────────────────────────────────────────
export const Placements: Story = {
  render: () => (
    <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", justifyContent: "center" }}>
      {(["top", "bottom", "left", "right"] as const).map((placement) => (
        <Popover
          key={placement}
          placement={placement}
          content={<SampleContent />}
        >
          <button type="button">{placement}</button>
        </Popover>
      ))}
    </div>
  ),
};

// ── 制御式（controlled）──────────────────────────────────────────────────
export const Controlled: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", alignItems: "center" }}>
        <button type="button" onClick={() => setOpen((v) => !v)}>
          外部ボタンで{open ? "閉じる" : "開く"}
        </button>
        <Popover
          open={open}
          onOpenChange={setOpen}
          content={<SampleContent />}
        >
          <span
            style={{
              display: "inline-block",
              padding: "8px 16px",
              background: "#e2e8f0",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            トリガー（クリック可）
          </span>
        </Popover>
      </div>
    );
  },
};
