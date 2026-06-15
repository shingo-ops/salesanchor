# design: mobile-shell-pr-r2b

## 参照

- recon: docs/handoff/mobile-shell-pr-r2b/recon.md
- PR-R2 evidence: docs/handoff/mobile-shell-pr-r2/design.md
- PR-R2-A evidence: docs/handoff/mobile-shell-pr-r2a/design.md
- ADR: ADR-067-design-token-enforcement.md / ADR-027-ui-internationalization.md / ADR-022.md

---

## KGI（定量・PO承認必須）

### KGI-1: MobileShell が独立したコンポーネントとして成立する

| 確認項目 | 期待値 |
|---|---|
| MobileTopBar が表示される | hamburger / pageTitle / avatar が 1行（flex row）に収まる |
| MobileDrawer が開閉する | hamburger click → drawer visible、backdrop/Escape click → drawer hidden |
| NavItemList variant="mobile" が MobileDrawer 内に表示される | nav items がレンダリングされる |
| 未読バッジが表示される | unreadCount > 0 時に leadChat item にバッジ表示 |
| 権限フィルタが動作する | hasPermission / hasAny / prefs に基づいて表示 items が絞られる |

### KGI-2: PC 既存 UI を破壊しない

| 確認項目 | 期待値 |
|---|---|
| Layout.tsx の変更ゼロ | PR-R2-B では Layout.tsx を変更しない |
| App.tsx の変更ゼロ | PR-R2-B では App.tsx を変更しない |
| 既存 E2E spec が退行しない | `npx playwright test --project=chromium` が全 pass |
| CSS トークン逸脱ゼロ | 新規 CSS に hex / px マジックナンバーがない |

### KGI-3: ADR-067 デザイントークン準拠

| 確認項目 | 期待値 |
|---|---|
| 色・余白・z-index が token 参照 | `npm run check:all`（stylelint）が 0件 |
| i18n ハードコードゼロ | 全 UI 文字列が `t("key")` 経由 |

---

## KPI / 検証方法

| 基準 | 目標値 | 検証方法 |
|---|---|---|
| KPI-1: MobileShell unit test | 全 pass | Vitest — rendering / drawer 開閉 / nav click / unread badge |
| KPI-2: 既存 E2E 退行なし | 0件退行 | `npx playwright test --project=chromium` |
| KPI-3: lint / check 全 pass | 0件 | `npm run check:all` |
| KPI-4: TypeScript エラーなし | 0件 | `npm run check:all` に含まれる tsc |

---

## 技術 How（設計方針）

### MobileShell.tsx（新規）

新規作成先: `frontend/src/components/MobileShell.tsx`

DOM 構造:

```
MobileShell
├── MobileTopBar  (div.mobile-topbar — sticky, z-index: var(--z-topbar)=100)
│   ├── HamburgerButton (button.mobile-topbar-hamburger, aria-controls="mobile-drawer")
│   ├── PageTitle (span.mobile-topbar-title — usePageTitle() の戻り値)
│   └── AvatarButton (button.mobile-topbar-avatar — in-flow、position:fixed ではない)
├── MobileDrawer (div.mobile-drawer — position:fixed, z-index: var(--z-sidebar)=200)
│   └── NavItemList variant="mobile" items={resolvedItems} onNavClick={closeDrawer}
├── MobileDrawerBackdrop (div.mobile-drawer-backdrop — position:fixed, z-index: var(--z-sidebar-overlay)=210)
└── div.mobile-content (flex:1, overflow-y:auto)
    └── <Outlet />
```

注意:
- MobileDrawerBackdrop の z-index は `--z-sidebar-overlay: 210`（`--z-backdrop: 298` は user-drawer 専用・流用禁止）。
- AvatarButton は in-flow（`position: fixed` ではない）。MobileTopBar の flex row の右端に配置。
- MobileShell は PR-R2-B 段階では App.tsx から条件レンダリングされない（単独ファイルとして存在するのみ）。App.tsx の切り替えは PR-R2-C。

### 状態管理

```tsx
const [drawerOpen, setDrawerOpen] = useState(false);
const [userDrawerOpen, setUserDrawerOpen] = useState(false);
const [unreadCount, setUnreadCount] = useState(0);

const openDrawer = () => setDrawerOpen(true);
const closeDrawer = () => setDrawerOpen(false);
```

Escape key で drawer を閉じる:

```tsx
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if (e.key === "Escape" && drawerOpen) closeDrawer();
  };
  document.addEventListener("keydown", handler);
  return () => document.removeEventListener("keydown", handler);
}, [drawerOpen]);
```

### nav items の解決（MobileShell 内で実行）

Layout.tsx:169-391 の権限判定ロジックをそのまま MobileShell に移植し、ResolvedNavItem[] を構築して NavItemList に渡す。

MobileShell は以下の hooks を使用:

```tsx
const { hasPermission, hasAny, loading: permsLoading } = usePermissions();
const { isSuperAdmin } = useSuperAdmin();
const { prefs, loading: uiPrefsLoading, staffName } = useUiPrefs();
const navLoading = permsLoading || uiPrefsLoading;
```

ResolvedNavItem[] を構成する際、children を持つ accordion items（saasAdmin）は `children: [...]` で構造化する。

### 未読カウント

Layout.tsx:117-127 と同一パターン:

```tsx
const loadUnreadCount = useCallback(async () => {
  try {
    const data = await listConversations({ unread_only: true });
    setUnreadCount((data.conversations || []).length);
  } catch { /* バッジ非表示のまま維持 */ }
}, []);
useEffect(() => { loadUnreadCount(); }, [loadUnreadCount]);
useSSE({ endpoint: "/api/v1/conversations/stream", onUpdate: loadUnreadCount });
```

### ユーザードロワー

AvatarButton click → `setUserDrawerOpen(true)` でドロワーを開く。

ドロワー内コンテンツは Layout.tsx:453-530 のユーザードロワー実装と同等（テーマ切り替え・言語切り替え・アカウント設定・サインアウト）。

`useLocale`, `useTheme`, `useAuth` が必要。

### i18n 新規キー

`frontend/src/locales/ja.json` と `frontend/src/locales/en.json` の `nav` セクションに追加:

| キー | ja | en |
|---|---|---|
| `nav.openDrawer` | "ナビゲーションを開く" | "Open navigation" |
| `nav.closeDrawer` | "ナビゲーションを閉じる" | "Close navigation" |

全 aria-label は `t("key")` 経由（ADR-027 §強制）。ハードコード禁止。

### mobile-shell.css（新規）

新規作成先: `frontend/src/mobile-shell.css`

主要クラス:

```css
/* MobileTopBar: sticky header */
.mobile-topbar {
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: var(--z-topbar); /* 100 */
  /* 色・余白は token 参照 */
}

/* MobileDrawer: 左からスライドイン */
.mobile-drawer {
  position: fixed; /* fixed-ok: Layout-level overlay */
  inset: 0 auto 0 0;
  z-index: var(--z-sidebar); /* 200 */
  width: var(--sidebar-width-expanded, 240px);
  transform: translateX(-100%);
  transition: transform var(--transition-sidebar);
  overflow-y: auto;
}

.mobile-drawer--open {
  transform: translateX(0);
}

/* MobileDrawerBackdrop */
.mobile-drawer-backdrop {
  position: fixed; /* fixed-ok: Layout-level overlay */
  inset: 0;
  z-index: var(--z-sidebar-overlay); /* 210 — user-drawer backdrop(298) と混同禁止 */
  background: var(--overlay-bg);
}

/* mobile-content: Outlet 表示エリア */
.mobile-content {
  flex: 1;
  overflow-y: auto;
}
```

すべての色・余白・サイズは CSS token 参照。hex / px マジックナンバー禁止（ADR-067）。

`:root.force-dark` ダークモード対応: 新規色 token を追加する場合は `frontend/src/tokens.css` の `:root` と `:root.force-dark` 両方に追記。

---

## 弊害 / トレードオフ

| リスク | 対策 |
|---|---|
| PR-R2-B 段階では MobileShell が App.tsx から呼ばれない | PR-R2-C までは Storybook / Vitest でのみ動作確認可能。E2E は PR-R2-C で実施 |
| nav items 定義が Layout.tsx と MobileShell に一時的に重複 | PR-R2-C で Layout.tsx → DesktopShell rename 後に統合方針確定。二重管理は PR-R2-C までの一時的な状態 |
| ユーザードロワーの実装量が多い | Layout.tsx:453-530 をほぼそのまま移植。新設ロジックは drawer state のみ |
| LeadChatIcon が NAV_ICONS ではなく別 export | `frontend/src/constants/icons.tsx` から LeadChatIcon を直接 import（Layout.tsx:19 と同様） |

---

## 実装制約（PO指定）

- Layout.tsx 変更なし
- App.tsx 変更なし
- responsive.css 変更なし（PR-R1 mobile rules は PR-R2-D で削除）
- 新規ファイルのみ（MobileShell.tsx + mobile-shell.css + i18n keys）
- PC 既存 UI/UX に影響を出さない

---

## 実装計画票

| フェーズ | 成果物 | 含まれる変更 |
|---|---|---|
| PR-R2-B（本PR） | MobileShell.tsx + mobile-shell.css + i18n keys + unit tests | 新規ファイル + locales/ja.json + locales/en.json |
| PR-R2-C | App.tsx Shell 切り替え + DesktopShell rename | PR-R2-B 完成後 |
| PR-R2-D（別PR） | PR-R1 CSS ハック削除 | MobileShell 本番動作確認後 |

---

## 検証計画

### 実装後チェック

```bash
cd frontend
npm run check:all
npx playwright test --project=chromium
```

### unit test 対象（Vitest）

| テスト | 内容 |
|---|---|
| MobileShell rendering | MobileTopBar / NavItemList が描画される |
| drawer open/close | hamburger click で drawer open、backdrop click で close |
| Escape key | keydown Escape で drawer close |
| nav click | onNavClick で drawer close |
| unread badge | unreadCount > 0 時に leadChat item のバッジ表示 |
| navLoading | permsLoading=true 時に items が空 |

新規 E2E spec（mobile-shell.spec.ts）は PR-R2-C で App.tsx と接続後に追加する（PR-R2-B では追加しない）。

---

## 外部・過去事例

ADR-137 §採用事例（docs/handoff/mobile-shell-pr-r2/design.md §外部・過去事例）参照済み。

- **Shopify Polaris**: `NavigationOverlay`（mobile）と `Navigation`（desktop）を別コンポーネントとして提供。JS `useBreakpoints()` hook で判定し DOM 切り替え。Nav items は `navigationItems` props として共通化（NavItemList が踏襲）。
- **Meta Business Suite**: PC/Mobile で DOM 完全分離。CSS による hide/show ではなく JS 条件レンダリング。
- **GitHub.com**: mobile 専用 header コンポーネントを条件レンダリング。

PR-R2-B は業界標準パターンに従い、MobileShell を独立 DOM として実装する。新規調査不要。

---

## 継続（次フェーズへの申し送り）

- PR-R2-C 着手前に MobileShell.tsx の drawer state と ResolvedNavItem[] 構成を確認すること
- PR-R2-C では App.tsx に `useIsMobile()` を導入し、`isMobile ? <MobileShell /> : <Layout />` の条件レンダリングを追加する
- PR-R2-C で Layout.tsx を DesktopShell.tsx に rename する際、MobileShell のユーザードロワー実装との重複を確認し、共通化可否を検討する
- PR-R2-D では `frontend/src/responsive.css` の translateX 等の PR-R1 mobile rules と `mobile-menu-btn` を削除する
