/**
 * MobileShell — モバイル専用 Shell（PR-R2-B）
 *
 * ADR-137: MobileShell は DesktopShell とは独立した DOM。
 * PR-R2-B 段階では App.tsx 未接続（Vitest / Storybook でのみ動作確認）。
 *
 * NOTE: このコンポーネントは Auth / Permissions / UiPrefs 等の
 *   全コンテキストに依存するため、Storybook では MSW モックを使わず
 *   コンテキストプロバイダーをデコレータとして提供する。
 *   API 呼び出しは初期状態（ローディング or 空）で表示される。
 */
import type { Meta, StoryObj } from "@storybook/react-vite";
import { MemoryRouter } from "react-router-dom";
import MobileShell from "./MobileShell";

/**
 * Storybook 用最小コンテキストモック。
 * MobileShell が依存する React context を最小限で提供し、
 * クラッシュせずに DOM 構造（MobileTopBar / MobileDrawer）を確認できるようにする。
 */
const meta: Meta<typeof MobileShell> = {
  title: "Components/MobileShell",
  component: MobileShell,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component: `
**MobileShell（PR-R2-B）** — モバイル専用 Shell コンポーネント。

- MobileTopBar（hamburger / pageTitle / avatar を 1行 flex）
- MobileDrawer（NavItemList variant="mobile"、左スライドイン）
- z-index: Drawer(210) > Backdrop(200)（クリック不能バグ防止 ADR-137）

※ この Story は DOM 構造確認用。API 呼び出しはモックなしのため初期状態で表示。
        `,
      },
    },
  },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <Story />
      </MemoryRouter>
    ),
  ],
  tags: ["autodocs"],
};
export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  name: "MobileShell（初期状態）",
};
