/**
 * ContextMenu — ストーリーカタログ
 */
import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { ContextMenu } from "./ContextMenu";

const meta: Meta<typeof ContextMenu> = {
  title: "Components/ContextMenu",
  component: ContextMenu,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
};
export default meta;

type Story = StoryObj<typeof ContextMenu>;

const sampleItems = [
  { key: "markUnread", label: "未読にする", onSelect: () => {} },
  { key: "exclude", label: "対象外にする", onSelect: () => {} },
  { key: "delete", label: "削除", onSelect: () => {}, danger: true },
];

// ── 基本表示（制御式。ボタンを押すと指定座標の近くに出る）──────────────────
export const Default: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <div style={{ padding: "48px" }}>
        <button type="button" onClick={() => setOpen(true)}>
          長押し相当（クリックで開く）
        </button>
        <ContextMenu
          open={open}
          onClose={() => setOpen(false)}
          anchor={{ x: 80, y: 120 }}
          items={sampleItems}
          ariaLabel="会話の操作"
        />
      </div>
    );
  },
};

// ── 画面の端に近い座標でも内側に収まることの見本 ──────────────────────────
export const NearViewportEdge: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <div style={{ padding: "48px" }}>
        <button
          type="button"
          onClick={() => setOpen(true)}
        >
          画面の右下隅近くで開く
        </button>
        <ContextMenu
          open={open}
          onClose={() => setOpen(false)}
          anchor={{ x: window.innerWidth - 20, y: window.innerHeight - 20 }}
          items={sampleItems}
          ariaLabel="会話の操作"
        />
      </div>
    );
  },
};

// ── align="left"（受信箱 第5便・PO 指摘）: 押した x 座標に関わらず
//    画面左端から一定の余白の位置に左端を固定する ───────────────────────
export const AlignLeft: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <div style={{ padding: "48px" }}>
        <button
          type="button"
          onClick={() => setOpen(true)}
          style={{ marginLeft: "200px" }}
        >
          画面右寄りを押しても左側に出る
        </button>
        <ContextMenu
          open={open}
          onClose={() => setOpen(false)}
          anchor={{ x: window.innerWidth - 100, y: 160 }}
          items={sampleItems}
          ariaLabel="会話の操作"
          align="left"
        />
      </div>
    );
  },
};
