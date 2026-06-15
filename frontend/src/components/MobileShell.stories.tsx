/**
 * MobileShell — モバイル専用 Shell デザイントークンカタログ (ADR-067)
 *
 * MobileShell.tsx 本体は AuthContext / UiPrefsContext 等の多数のContextに依存するため、
 * Layout.stories.tsx と同様に CSS クラスを直接使った静的スケルトンでデザイントークンを確認する。
 *
 * ADR-137: z-index 前後関係 Drawer(210) > Backdrop(200)
 * ADR-067: 色・余白・z-index はすべて design token 参照
 */
import type { Meta, StoryObj } from "@storybook/react-vite";
import "../mobile-shell.css";

const meta: Meta = {
  title: "Components/MobileShell",
  parameters: { layout: "fullscreen" },
  tags: ["autodocs"],
};
export default meta;

type Story = StoryObj;

/** MobileTopBar: hamburger / pageTitle / avatar が 1行 flex に収まる確認 */
export const TopBar: Story = {
  name: "MobileTopBar（sticky header）",
  render: () => (
    <div className="mobile-shell" style={{ height: "200px" }}>
      <div className="mobile-topbar">
        {/* HamburgerButton */}
        <button className="mobile-topbar-hamburger" aria-label="ナビゲーションを開く">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        {/* PageTitle */}
        <span className="mobile-topbar-title">ダッシュボード</span>
        {/* AvatarButton (in-flow) */}
        <button className="mobile-topbar-avatar" aria-label="ユーザーメニューを開く">
          T
        </button>
      </div>
      <div style={{ padding: "var(--space-4)", color: "var(--text-secondary)", fontSize: "var(--font-sm)" }}>
        コンテンツエリア
      </div>
    </div>
  ),
};

/** MobileDrawer: 開いた状態（z-index 210 — Backdrop より前面） */
export const DrawerOpen: Story = {
  name: "MobileDrawer（開いた状態）",
  render: () => (
    <div className="mobile-shell" style={{ height: "400px", position: "relative" }}>
      <div className="mobile-topbar">
        <button className="mobile-topbar-hamburger" aria-label="ナビゲーションを開く">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <span className="mobile-topbar-title">ダッシュボード</span>
        <button className="mobile-topbar-avatar" aria-label="ユーザーメニューを開く">T</button>
      </div>
      {/* Backdrop (z-index 200) */}
      <div className="mobile-drawer-backdrop" style={{ position: "absolute" }} aria-hidden="true" />
      {/* Drawer (z-index 210 — Backdrop より前面) */}
      <div
        id="mobile-drawer"
        className="mobile-drawer mobile-drawer--open"
        style={{ position: "absolute" }}
        role="dialog"
        aria-modal="true"
        aria-label="ナビゲーション"
      >
        <div className="mobile-drawer-header">
          <div style={{ width: 24, height: 24, background: "var(--bg-accent)", borderRadius: "var(--radius-sm)" }} />
          <button className="mobile-drawer-close" aria-label="ナビゲーションを閉じる">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="mobile-drawer-nav">
          {["ダッシュボード", "スケジュール", "在庫管理", "受注管理", "顧客情報"].map((label, i) => (
            <div
              key={i}
              style={{
                padding: "var(--space-2) var(--space-4)",
                color: i === 0 ? "var(--sidebar-item-color-active, var(--text-primary))" : "var(--sidebar-item-color, var(--text-secondary))",
                background: i === 0 ? "var(--sidebar-item-bg-active, var(--bg-subtle))" : "transparent",
                fontSize: "var(--font-sm)",
                fontWeight: i === 0 ? "var(--font-medium)" : "normal",
              }}
            >
              {label}
            </div>
          ))}
        </div>
      </div>
      <div className="mobile-content" style={{ padding: "var(--space-4)", color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
        コンテンツエリア（Backdropで暗転）
      </div>
    </div>
  ),
};

/** MobileDrawer: 閉じた状態 */
export const DrawerClosed: Story = {
  name: "MobileDrawer（閉じた状態）",
  render: () => (
    <div className="mobile-shell" style={{ height: "300px" }}>
      <div className="mobile-topbar">
        <button className="mobile-topbar-hamburger" aria-label="ナビゲーションを開く">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <span className="mobile-topbar-title">スケジュール</span>
        <button className="mobile-topbar-avatar" aria-label="ユーザーメニューを開く">T</button>
      </div>
      {/* Drawer: 閉じた状態（translateX(-100%) で画面外） */}
      <div
        id="mobile-drawer"
        className="mobile-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="ナビゲーション"
      />
      <div className="mobile-content" style={{ padding: "var(--space-4)", color: "var(--text-secondary)", fontSize: "var(--font-sm)" }}>
        コンテンツエリア（Drawer は画面外に退避済み）
      </div>
    </div>
  ),
};
