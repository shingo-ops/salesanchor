# recon: mobile-shell-pr-r2b

## 調査日: 2026-06-15

## 参照元

- PR-R2 evidence: docs/handoff/mobile-shell-pr-r2/recon.md, docs/handoff/mobile-shell-pr-r2/design.md（#2209 マージ済み）
- PR-R2-A evidence: docs/handoff/mobile-shell-pr-r2a/recon.md, docs/handoff/mobile-shell-pr-r2a/design.md（#2223 マージ済み）
- ADR: ADR-137 / ADR-067 / ADR-027 / ADR-022

---

## PR-R2-B スコープ

### 実装対象（新規ファイルのみ）

1. `frontend/src/components/MobileShell.tsx`（新規）— Mobile 専用 Shell コンポーネント本体
2. `frontend/src/mobile-shell.css`（新規）— MobileShell 専用スタイル
3. i18n キー追加: `frontend/src/locales/ja.json` / `frontend/src/locales/en.json`

### 実装対象外（PR-R2-B に含めない）

- `frontend/src/App.tsx` の Shell 切り替えロジック（PR-R2-C）
- `frontend/src/components/Layout.tsx` の DesktopShell rename（PR-R2-C）
- `frontend/src/responsive.css` の PR-R1 CSS ハック削除（PR-R2-D）
- migrations / deploy.yml / 本番 scripts

---

## PR-R2-A 成果物（接続先）

### NavItemList.tsx（PR-R2-A 新規・MobileShell が利用）

`frontend/src/components/NavItemList.tsx:14-21` — ResolvedNavItem 型定義・export

```tsx
export interface ResolvedNavItem {
  key: string;
  labelKey: string;
  icon: React.ReactNode;
  path: string;
  children?: ResolvedNavItem[];
  unread?: boolean;
}
```

`frontend/src/components/NavItemList.tsx:30-87` — NavItemList コンポーネント

- props: `items: ResolvedNavItem[]`, `onNavClick: () => void`, `variant: 'desktop' | 'mobile'`, `unreadCount?: number`
- 純粋描画のみ。権限判定・未読バッジ計算は親（MobileShell）が実行済みであること前提

### useIsMobile.ts（PR-R2-A 新規・PR-R2-C で利用）

`frontend/src/hooks/useIsMobile.ts:15-28` — PR-R2-C で App.tsx が利用。PR-R2-B では MobileShell 自身が利用しない（App.tsx から条件レンダリングされる前提）

---

## 既存コンポーネント・hooks 確認

### Layout.tsx（DesktopShell の現状）

`frontend/src/components/Layout.tsx:17-31` — 必要 import 全量:

```ts
import { useAuth } from "../contexts/AuthContext";
import { useLocale } from "../contexts/LocaleContext";
import { useTheme } from "../contexts/ThemeContext";
import { useUiPrefs } from "../contexts/UiPrefsContext";
import { usePermissions } from "../hooks/usePermissions";
import { useSuperAdmin } from "../hooks/useSuperAdmin";
import { useSSE } from "../hooks/useSSE";
import { listConversations } from "../lib/messages";
import { NAV_ICONS, THEME_ICONS, GlobeIcon, LeadChatIcon, ACCOUNT_ICONS } from "../constants/icons";
import { ICON } from "../constants/iconSizes";
```

MobileShell は同等の import が必要（ユーザードロワー・nav item 生成のため）。

### usePermissions（権限判定）

`frontend/src/hooks/usePermissions.ts:16` — `export function usePermissions()`

戻り値: `{ permissions, loading, error, hasPermission, hasAny, reload }`

Layout.tsx での使用パターン: `frontend/src/components/Layout.tsx:100` — `const { hasPermission, hasAny, loading: permsLoading } = usePermissions()`

### useSuperAdmin

`frontend/src/hooks/useSuperAdmin.ts:19` — `export function useSuperAdmin()`

戻り値: `{ isSuperAdmin, loading }`

### useUiPrefs（UI設定）

`frontend/src/contexts/UiPrefsContext.tsx:53-68` — 型定義

戻り値: `{ prefs, loading, prefsFetched, selfStaffId, staffName, refresh, setPrefs }`

MobileShell での使用: `prefs.show_chat_menu` / `prefs.show_sales_menu` / `staffName`

### useSSE + listConversations（未読カウント）

`frontend/src/hooks/useSSE.ts:16-23` — `useSSE({ endpoint, onUpdate }): void`

`frontend/src/lib/messages.ts` — `listConversations({ unread_only: true })`

Layout.tsx での未読カウントパターン: `frontend/src/components/Layout.tsx:117-127`

```tsx
const [unreadCount, setUnreadCount] = useState(0);
const loadUnreadCount = useCallback(async () => {
  try {
    const data = await listConversations({ unread_only: true });
    setUnreadCount((data.conversations || []).length);
  } catch { /* バッジ非表示のまま維持 */ }
}, []);
useEffect(() => { loadUnreadCount(); }, [loadUnreadCount]);
useSSE({ endpoint: "/api/v1/conversations/stream", onUpdate: loadUnreadCount });
```

MobileShell も同一パターンを採用する。

### usePageTitle（MobileTopBar ページタイトル）

`frontend/src/hooks/usePageTitle.ts:15` — `export function usePageTitle(): string`

`frontend/src/config/routeTitles.ts` — ROUTE_TITLE_KEYS（pathname → nav.* i18n key の対応表）

MobileTopBar の PageTitle は `usePageTitle()` の戻り値をそのまま表示する。

### useAuth（ユーザー情報・サインアウト）

`frontend/src/contexts/AuthContext.tsx` — `export function useAuth()`

戻り値に `user` / `signOut` が含まれる（Layout.tsx:99 参照）

### useLocale / useTheme（ユーザードロワー内）

`frontend/src/contexts/LocaleContext.tsx` — `useLocale()` → `{ locale, changeLanguage }`

`frontend/src/contexts/ThemeContext.tsx` — `useTheme()` → `{ theme, changeTheme }`

---

## nav item 定義（Layout.tsx インライン定義の把握）

### 権限別 nav items

`frontend/src/components/Layout.tsx:169-191` — 権限チェックと showXxx フラグ:

| showXxx | 権限条件 | パス |
|---|---|---|
| hasPermission("dashboard.view") | 直接チェック | `/` |
| — | 制限なし | `/schedule` |
| prefs.show_chat_menu | UI設定 | `/lead-chat`（unread=true） |
| hasPermission("products.view") | 直接チェック | `/inventory` |
| hasPermission("purchase_orders.view") | 直接チェック | `/purchase-orders` |
| showSalesLink | prefs.show_sales_menu && (quotes.view or invoices.view) | `/quotes` or `/invoices` |
| showCrmLink | leads.view or customers.view | `/crm` |
| hasPermission("orders.view") | 直接チェック | `/orders` |
| hasPermission("orders.view") | 直接チェック | `/sales` |
| hasPermission("orders.view") | 直接チェック | `/commissions` |
| showManagementCenter | staff/teams/roles/bots/shifts/channels/erp/orders/customers/deals/suppliers/purchase_orders/tenant いずれか | `/management-center` |
| isSuperAdmin | super_admin | accordion（children）|

### アイコン定義元

`frontend/src/constants/icons.tsx` — NAV_ICONS, THEME_ICONS, GlobeIcon, LeadChatIcon, ACCOUNT_ICONS

`frontend/src/constants/iconSizes.ts` — ICON.base=20, ICON.md=16, ICON.sm=14

---

## CSS トークン確認

### z-index 階層

`frontend/src/tokens.css:122-127`

```css
--z-topbar:          100;   /* MobileTopBar */
--z-sidebar:         200;   /* MobileDrawer */
--z-sidebar-overlay: 210;   /* MobileDrawerBackdrop（PO確定: backdrop専用） */
--z-backdrop:        298;   /* user-drawer backdrop 専用（流用禁止） */
--z-drawer:          299;   /* user-drawer パネル */
--z-avatar:          300;   /* avatar-btn */
```

PO確定（docs/handoff/mobile-shell-pr-r2/design.md §PO確定方針①）:
MobileDrawerBackdrop は `--z-sidebar-overlay: 210` を使用。`--z-backdrop: 298` は user-drawer backdrop 専用のため流用しない。

### ブレークポイント

`frontend/src/constants/breakpoints.ts:19` — MOBILE_MAX: 767

`frontend/src/tokens.css:113-116` — `--breakpoint-mobile-max: 767px`（CSS custom property）

### その他関連 token

`frontend/src/tokens.css:113-199` — sidebar 幅・avatar zone・icon サイズなど。MobileShell CSS は直接値を書かず token 参照を徹底する（ADR-067）。

---

## 既存 CSS 構造（PC 既存・変更禁止）

### sidebar-panel（位置・z-index）

`frontend/src/sidebar.css:18-32` — `.sidebar-panel { position: fixed; left:0; z-index: var(--z-sidebar) }`

MobileShell では sidebar-panel は DOM に存在しない。PC の sidebar-panel を流用しない。

### avatar-btn（PC: position: fixed）

`frontend/src/topbar.css:138-158` — `.avatar-btn { position: fixed; right: var(--avatar-zone-right); z-index: var(--avatar-zone-z) }`

PO確定（docs/handoff/mobile-shell-pr-r2/design.md §PO確定方針③）:
MobileTopBar 内では avatar を in-flow 配置（`position: fixed` 廃止）。MobileShell 内アバターは `.mobile-topbar-avatar` クラスで独立実装。

### PR-R1 responsive.css mobile rules（PR-R2-B では触らない）

`frontend/src/responsive.css` — `.sidebar-panel { transform: translateX(-100%) }` 等の PR-R1 CSS ハックが残存。PR-R2-B では変更しない（PR-R2-D で削除）。

---

## i18n 確認

### 既存 nav キー

`frontend/src/locales/ja.json:84-157` — `nav.openMenu: "メニューを開く"` 等既存キー

### PR-R2-B で追加が必要な新規キー

`frontend/src/locales/ja.json` / `frontend/src/locales/en.json` の `nav` セクションに追加:

| キー | ja | en |
|---|---|---|
| `nav.openDrawer` | "ナビゲーションを開く" | "Open navigation" |
| `nav.closeDrawer` | "ナビゲーションを閉じる" | "Close navigation" |

`nav.openMenu` は PR-R1 で追加済み。MobileTopBar の hamburger aria-label は `nav.openDrawer` を用いる（PR-R2-B では MobileShell 内専用の aria-label として新設）。

---

## 不明点 → 全件 PO確定済み（docs/handoff/mobile-shell-pr-r2/design.md §PO確定方針）

| # | 確定方針 |
|---|---|
| ① backdrop z-index | `--z-sidebar-overlay: 210` を MobileDrawerBackdrop に使用 |
| ② nav item builder | NavItemList.tsx（PR-R2-A 完了済み）を利用 |
| ③ avatar mobile 配置 | MobileTopBar 内に in-flow で配置 |
| ④ tablet Shell | 768px 以上は DesktopShell（MobileShell は 767px 以下のみ） |
