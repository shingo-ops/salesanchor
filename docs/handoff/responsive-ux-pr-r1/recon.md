# Recon: PR-R1 レスポンシブ基盤最適化

## 目的

SalesAnchor アプリのレスポンシブ基盤を現行 DOM（`app-shell` / `sidebar-panel` / `app-body`）に合わせて整理し、mobile 375px で表示幅が sidebar によって削られない状態にする。

---

## 調査コマンド

```bash
# 既存 breakpoint 使用状況
grep -rn "max-width: 768\|max-width:768\|max-width: 767\|min-width: 768" frontend/src --include="*.css"

# ADR 検索
git grep -i "responsive" docs/adr/
git grep -i "breakpoint" docs/adr/
git grep -i "design token" docs/adr/
git grep -i "PageLayout" docs/adr/

# 旧クラスの DOM 使用確認
grep -rn "className.*\"layout\"\|className.*\"topnav\"\|className.*\"brandbar\"" frontend/src --include="*.tsx"

# app-topbar の使用確認
grep -rn "app-topbar" frontend/src --include="*.tsx"
```

---

## 既存 ADR 検索結果

| 検索キー | 結果 |
|----------|------|
| `responsive` in docs/adr/ | 0件 — responsive 専用 ADR なし |
| `breakpoint` in docs/adr/ | ADR-054, ADR-057（LP用のみ）; ADR-067（メディアクエリはdual-file sync必要） |
| `design token` in docs/adr/ | ADR-067（デザイントークン強制）|
| `PageLayout` in docs/adr/ | 0件 |

**関連 ADR:**
- `docs/adr/ADR-022-*.md` — App Shell（sidebar / app-body 構成）
- `docs/adr/ADR-027-ui-internationalization.md` — i18n 強制（aria-label も `t()` 経由）
- `docs/adr/ADR-067-design-token-enforcement.md` — hex/magic number 禁止・CSS変数のみ

---

## 実コード根拠（file:line）

### 問題の核心

| 問題 | ファイル:行 |
|------|------------|
| `@media (max-width: 768px)` 旧クラス群（.layout/.sidebar/.topnav等） | `frontend/src/responsive.css:7-81` |
| `.app-body { margin-left: var(--sidebar-width-collapsed, 54px) }` | `frontend/src/sidebar.css:246` |
| `.sidebar-panel` は `position: fixed; left:0; height:100vh` | `frontend/src/sidebar.css:27-31` |
| sidebar 開閉は `onMouseEnter` / `onMouseLeave` 依存（touch端末対応なし） | `frontend/src/components/Layout.tsx:177-178` |
| `.avatar-btn` は `position: fixed` | `frontend/src/topbar.css:110` |
| `.user-drawer` は `width: var(--drawer-width)` 固定（300px） | `frontend/src/topbar.css:157` |
| `.page-layout-header` の padding | `frontend/src/pages-layout.css:64` |
| `.page-layout-title-row` は flex row, `min-height: var(--btn-min-height-md)` | `frontend/src/pages-layout.css:68-75` |

### 公式 breakpoint 定義

| 定義場所 | 行 |
|----------|-----|
| `tokens.css` § ブレークポイント | `frontend/src/tokens.css:100-117` |
| `constants/breakpoints.ts` | `frontend/src/constants/breakpoints.ts:19-41` |
| check-breakpoint-sync.js | `frontend/scripts/check-breakpoint-sync.js:3-18` |

公式値:
- mobile: `max-width: 767px`
- tablet min: `768px`
- tablet max: `1279px`
- desktop: `min-width: 1280px`

### 既存 responsive の正常ファイル（変更しない）

| ファイル | 状況 |
|----------|------|
| `frontend/src/hub-shell.css:104` | `@media (max-width: 767px)` — 正しい |
| `frontend/src/pages/inbox/InboxPage.css:1114` | `@media (max-width: 767px)` — 正しい |
| `frontend/src/components/Card.css:34` | `@media (max-width: 767px)` — 正しい |
| `frontend/src/components/Button.css:31` | `@media (max-width: 767px)` — 正しい |
| `frontend/src/components/FormField.css:151` | `@media (max-width: 767px)` — 正しい |

### スコープ外（PR-R1 で触らない）

| ファイル | 理由 |
|----------|------|
| `frontend/src/company-forms.css:194` | `max-width: 768px` の 768px 問題あり。対象外 |

---

## 変更対象ファイル

| ファイル | 変更内容 |
|----------|---------|
| `frontend/src/responsive.css` | 全面書き換え（旧クラス削除・現行DOM対応・767px統一） |
| `frontend/src/topbar.css` | mobile menu button スタイル追加・mobile section 追加 |
| `frontend/src/pages-layout.css` | mobile section 追加 |
| `frontend/src/components/Layout.tsx` | isMobileSidebarOpen state・mobile menu button・backdrop・Escape key |
| `frontend/src/constants/icons.tsx` | Bars3Icon (hamburger) 追加 |
| `frontend/src/locales/ja.json` | `nav.openMenu` 追加 |
| `frontend/src/locales/en.json` | `nav.openMenu` 追加 |

---

## 不明点・確認事項

- `app-topbar` は Storybook (`Layout.stories.tsx`) には存在するが、実アプリの Layout.tsx では未使用（`.app-topbar` の TSX 参照なし）。PR-R1 ではこの状況を変えない。
- `company-forms.css:194` の `@media (max-width: 768px)` はスコープ外。別 PR で対応。
