# Design: PR-R1 レスポンシブ基盤最適化

## KGI

1. 公式ブレークポイントに統一
   - mobile: `<= 767px`
   - tablet: `768px - 1279px`
   - desktop: `>= 1280px`
2. mobile 375px で `.app-body` が sidebar margin を残さない
3. mobile でサイドバーナビが操作できる（mobile menu button 経由）
4. Inbox / Hub Shell の既存 responsive を退行させない
5. CI / check スクリプトが green

---

## 対象範囲

### 対象

- `frontend/src/responsive.css` — 全面書き換え
- `frontend/src/topbar.css` — mobile menu button + mobile section 追加
- `frontend/src/pages-layout.css` — mobile section 追加
- `frontend/src/components/Layout.tsx` — mobile menu button / state / backdrop / Escape key 追加
- `frontend/src/constants/icons.tsx` — Bars3Icon (hamburger) 追加
- `frontend/src/locales/ja.json` / `en.json` — `nav.openMenu` キー追加

### 対象外

- `frontend/src/sidebar.css` — responsive は responsive.css 側で制御するため変更なし
- `frontend/src/pages/inbox/InboxPage.css` — 既存の 3段階 responsive を維持
- `frontend/src/hub-shell.css` — 既存の mobile 縦積みを維持
- `frontend/src/company-forms.css` — 768px 問題あるが PR-R1 スコープ外
- DB migration / deploy.yml / `.github/workflows/*` / 本番 scripts — 触らない

---

## 技術 How

### 1. `responsive.css` 全面書き換え

**問題:** 既存 `responsive.css:7` の `@media (max-width: 768px)` は旧クラス（`.layout`/`.sidebar`/`.topnav`/`.brandbar`/`.mainnav`）を対象にしており、現行 DOM に存在しないクラスへの適用となっていた。現行 DOM（`.app-shell`/`.sidebar-panel`/`.app-body`）への responsive 制御がゼロ。

**解決:**
- breakpoint を `767px` に修正
- 旧クラスの rules を削除（現行 DOM に存在しない）
- 現行クラスへの mobile rules を追加
- 現行 DOM に存在する `.page`/`.roles-layout`/`.dashboard-tables` 等は維持

### 2. mobile menu button（Option A 採用）

**問題:** 現行 sidebar の開閉は `onMouseEnter` / `onMouseLeave` 依存。touch 端末では hover を導線として使えないため、sidebar を CSS で隠すだけではナビが開けない。

**解決:** `Layout.tsx` に `isMobileSidebarOpen` state と mobile menu button を追加。

- `sidebar-panel` に `sidebar-mobile-open` class を付与（`sidebar-expanded` とは独立）
- desktop の hover 展開（`sidebar-expanded`）は変更なし
- mobile 専用 backdrop で背景クリック → 閉じる
- Escape key → 閉じる
- nav item click → 閉じる（`handleNavClick` に追加）

**CSS での制御:**
```css
/* responsive.css */
@media (max-width: 767px) {
  .sidebar-panel { transform: translateX(-100%); }
  .sidebar-panel.sidebar-mobile-open { transform: translateX(0); width: var(--sidebar-width-expanded); }
  .app-body { margin-left: 0; }
  .mobile-menu-btn { display: flex; }
}
@media (min-width: 768px) {
  .mobile-menu-btn { display: none; }
}
```

### 3. `--page-header-avatar-clearance` 流用

mobile で `page-layout-header` の padding-right は既存の `--page-header-avatar-clearance`（68px = avatar 40px + right 16px + gap 12px）をそのまま流用。`--space-16` など存在しないトークンは使わない。

### 4. デザイントークン準拠

- 新規 hex 色なし
- magic number なし（すべて既存 CSS 変数を流用）
- `tokens.css` への追加なし（`--page-header-avatar-clearance` が既存のため不要）
- `breakpoints.ts` との同期を維持（`check:breakpoint-sync` で検証）

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| breakpoint が 767px に統一 | `check:breakpoint-sync` |
| position:fixed が pages/ に入っていない | `check:css-fixed-position` |
| PageLayout raw h2 なし | `check:page-layout` |
| CSS lint clean | `check:stylelint` |
| 全体 lint clean | `check:all` |
| build 成功 | `npm run build` |
| mobile menu button が 375px で見える | 手動確認 |
| sidebar が menu button click で開く | 手動確認 |
| backdrop click で閉じる | 手動確認 |
| nav item click で閉じる | 手動確認 |
| Escape key で閉じる | 手動確認 |
| desktop hover sidebar が退行しない | 手動確認 (1280px) |
| `/lead-chat` drawer/bottom sheet が退行しない | 手動確認 (375px, 768px) |
| `/crm` hub-shell mobile 縦積みが退行しない | 手動確認 (375px) |

---

## リスク・軽減策

| リスク | 軽減策 |
|--------|--------|
| sidebar-expanded と sidebar-mobile-open の干渉 | CSS を `@media` で分離。desktop では `@media (max-width: 767px)` の transform が適用されないため干渉なし |
| accordion open → sidebar-expanded が true → mobile でも expand される | sidebar-mobile-open は open/close、sidebar-expanded は width 制御の別役割。mobile 時は sidebar-mobile-open で幅を `--sidebar-width-expanded` に固定するため問題なし |
| check:css-fixed-position に `.mobile-menu-btn` と `.sidebar-mobile-backdrop` が引っかかる | どちらも `src/pages/` 外（`src/topbar.css`）に定義しているためスクリプト対象外 |
| `company-forms.css:194` の 768px 残存 | PR-R1 スコープ外。別 PR で対応 |

---

## 外部・過去事例の検討

PR-R1 は既存アプリの CSS/JS 基盤修正（small scope）のため、外部事例調査の対象外とする。

参考パターンとして:
- Meta Business Suite: fixed sidebar + mobile hamburger button（avatar button と同様の fixed 配置）
- Salesforce SLDS: 767px/1279px の3段階 breakpoint（本プロジェクトの公式 breakpoint と一致）

---

## 参照

- recon: docs/handoff/responsive-ux-pr-r1/recon.md
- ADR: ADR-067-design-token-enforcement.md（ADR-067）, ADR-027-ui-internationalization.md, ADR-022.md

---

## 今後の課題（PR-R1 スコープ外）

- **PR-R3**: `responsive-layout.spec.ts` (Playwright E2E) の追加。375×812 / 768×1024 / 1280×800 で主要ページを自動検証。
- `company-forms.css:194` の `max-width: 768px` を `767px` に修正（別 PR）。
- `app-topbar` コンポーネントが Storybook のみでなく実アプリにも追加される場合、mobile responsive の再検討が必要。
