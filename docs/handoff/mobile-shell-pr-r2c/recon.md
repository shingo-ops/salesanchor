# recon: mobile-shell-pr-r2c

## 調査日: 2026-06-16

## 参照元

- PR-R2 design: docs/handoff/mobile-shell-pr-r2/design.md（KGI/KPI 定義元）
- PR-R2-B evidence: docs/handoff/mobile-shell-pr-r2b/recon.md（MobileShell 実装詳細）
- ADR: ADR-137 / ADR-067 / ADR-027 / ADR-022

---

## PR-R2-C スコープ

### 実装対象

1. `frontend/src/App.tsx` — ShellSwitch 追加・Shell 条件レンダリング接続
2. `frontend/src/components/DesktopShell.tsx` — Layout.tsx → rename + mobile 固有コード削除
3. E2E specs 3本: `frontend/tests-e2e/desktop-shell.spec.ts` / `frontend/tests-e2e/mobile-shell.spec.ts` / `frontend/tests-e2e/horizontal-overflow.spec.ts`

### 実装対象外（PR-R2-C に含めない）

- frontend/src/responsive.css の PR-R1 CSS ハック削除（PR-R2-D）
- migrations / deploy.yml / 本番 scripts

---

## PR-R2-B 成果物（接続先）

### MobileShell.tsx（PR-R2-B 新規・develop にマージ済み）

`frontend/src/components/MobileShell.tsx:74` — export default function MobileShell()

MobileShell は useAuth / useLocale / useTheme / useUiPrefs / usePermissions / useSuperAdmin / usePageTitle / useSSE / listConversations を利用。
Outlet を main.mobile-content でラップ。DesktopShell と完全に独立した DOM。

### useIsMobile.ts（PR-R2-A 新規・develop にマージ済み）

`frontend/src/hooks/useIsMobile.ts:15` — export function useIsMobile(): boolean

- window.matchMedia("(max-width: 767px)") で判定（BREAKPOINTS.MOBILE_MAX = 767）
- matchMedia change イベントでリアルタイム更新
- SSR では動作しない（現時点は CSR のみ）

---

## 既存ファイル確認

### App.tsx（Shell 切り替え追加先）

`frontend/src/App.tsx:8` — import Layout から ShellSwitch への変更対象行

`frontend/src/App.tsx:126-131` — ProtectedRoute element として Layout が配置されており、ShellSwitch に置換する。ShellSwitch は BrowserRouter 内でレンダリングされるため useIsMobile / useNavigate ともに利用可。

### Layout.tsx（DesktopShell にリネーム・削除済み）

Layout.tsx は PR-R2-C で DesktopShell.tsx にリネームし git rm 削除済み。
`frontend/src/components/DesktopShell.tsx` — export default function DesktopShell()

#### mobile 固有コード（Layout.tsx から削除済み）

| 削除コード | 内容 | 削除理由 |
|---|---|---|
| isMobileSidebarOpen state (旧 Layout.tsx line 111) | モバイルサイドバー開閉状態管理 | MobileShell へ移管済み |
| openMobileSidebar 関数 (旧 Layout.tsx line 131-134) | サイドバーを開く | 同上 |
| closeMobileSidebar 関数 (旧 Layout.tsx line 136-140) | サイドバーを閉じる | 同上 |
| Escape key handler (旧 Layout.tsx line 143-150) | isMobileSidebarOpen 依存 | 同上 |
| handleNavClick → handleSidebarLeave に統一 (旧 Layout.tsx line 165) | PC は mouse leave で折りたたみ | mobile 固有コード不要 |
| sidebar-mobile-backdrop div (旧 Layout.tsx line 197-204) | モバイルバックドロップ要素 | MobileShell へ移管済み |
| sidebar-mobile-open クラス付与 (旧 Layout.tsx line 209) | モバイル展開クラス | 同上 |
| mobile-menu-btn button (旧 Layout.tsx line 417-425) | ハンバーガーボタン | MobileShell TopBar へ移管済み |

---

## E2E ユーティリティ確認

### auth.ts（認証 bypass）

`frontend/tests-e2e/utils/auth.ts:43` — export async function installAuthBypass(page: Page): Promise<void>

Firebase Auth を IndexedDB + fetch patch で bypass する。page.goto 前に必ず呼ぶ。

### api-mock.ts（API モック）

`frontend/tests-e2e/utils/api-mock.ts` — export async function mockApi(page, mocks: MockMap): Promise<void>

### common-mocks.ts（共通モック）

`frontend/tests-e2e/utils/common-mocks.ts:42` — export function commonMocks(): MockMap

- GET /me/permissions → 全権限付与
- GET /staff/me → ui_preferences 含む staff 情報

### playwright.config.ts

`frontend/playwright.config.ts:56-59` — Chromium Desktop Chrome project 設定

デフォルト viewport は Desktop Chrome（1280×720）。モバイル E2E は page.setViewportSize で 375×812 に変更する。

---

## CSS / design token 確認

### MobileShell 用 token（変更なし）

`frontend/src/tokens.css:122-127` — z-index 階層:
- --z-topbar: 100（MobileTopBar）
- --z-sidebar: 200（MobileDrawer）
- --z-sidebar-overlay: 210（MobileDrawerBackdrop）

### BREAKPOINTS 定数

`frontend/src/constants/breakpoints.ts:19` — MOBILE_MAX: 767

---

## 不明点 → 全件 PO確定済み（docs/handoff/mobile-shell-pr-r2/design.md §PO確定方針）

| # | 確定方針 |
|---|---|
| ① ShellSwitch 配置 | App.tsx 内の ProtectedRoute element として定義 |
| ② Layout rename | DesktopShell.tsx にリネーム。export default も DesktopShell に変更 |
| ③ handleNavClick | handleSidebarLeave に統一（mobile 固有コード不要） |
| ④ tablet Shell | 768px 以上は DesktopShell（MobileShell は 767px 以下のみ）|
