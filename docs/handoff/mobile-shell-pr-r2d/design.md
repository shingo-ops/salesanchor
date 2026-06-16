# design: mobile-shell-pr-r2d

## 参照

- recon: docs/handoff/mobile-shell-pr-r2d/recon.md
- KGI/KPI 定義元: docs/handoff/mobile-shell-pr-r2/design.md
- ADR: ADR-137 §移行方針、ADR-067、ADR-027

---

## KGI（定量・PO承認）

docs/handoff/mobile-shell-pr-r2/design.md の KGI-1〜KGI-5 を全件維持すること。
本 PR-R2-D が担うのは「PR-R1 CSS ハック削除後もすべての KGI が成立すること」の確認。

| KGI | 内容 | 検証方法 |
|---|---|---|
| KGI-1 | 1280px で DesktopShell が崩れない | desktop-shell.spec.ts |
| KGI-2 | 375px で MobileShell が成立する | mobile-shell.spec.ts |
| KGI-5 | 375px で 6 route 横スクロールなし | horizontal-overflow.spec.ts |

---

## KPI / 検証方法

| 基準 | 目標値 | 検証方法 |
|---|---|---|
| KPI-1: Desktop 非退行率 | 100% | desktop-shell.spec.ts — Chromium 1280×800 |
| KPI-2: MobileShell 成立率 | 100% | mobile-shell.spec.ts — Chromium 375×812 |
| KPI-3: 対象 route 横スクロールゼロ | 100% | horizontal-overflow.spec.ts — 375px 全6 route |
| KPI-4: SSoT 逸脱ゼロ | 0件 | npm run check:all |
| KPI-5: Build 成功 | pass | npm run build |
| KPI-6: PR-R1 クラス残存ゼロ | 0件 | `grep -r "mobile-menu-btn\|sidebar-mobile-backdrop\|sidebar-mobile-open" frontend/src/` |

---

## 技術 How（削除方針）

### 削除するもの

**frontend/src/responsive.css**

`@media (max-width: 767px)` ブロック内から PR-R1 App Shell ハックを削除:
- `.sidebar-panel { transform: translateX(-100%); ... }`
- `.sidebar-panel.sidebar-mobile-open { transform: translateX(0); ... }`
- `.app-body { margin-left: 0; }`
- `.mobile-menu-btn { display: flex; }`

`@media (min-width: 768px)` ブロック全体を削除:
- `.mobile-menu-btn { display: none; }`

**frontend/src/topbar.css**

- `.mobile-menu-btn { ... }` + `.mobile-menu-btn:hover { ... }` 定義（lines 108-135）
- `.sidebar-mobile-backdrop { ... }` 定義（lines 294-302）

### 残すもの

**frontend/src/responsive.css**

`@media (max-width: 767px)` ブロック内の非 PR-R1 ルール:
- `.page { padding: var(--space-4); }` — MobileShell 内でも使用
- `.roles-layout`, `.roles-sidebar`, `.roles-main-header` — RolesPage レイアウト
- `.dashboard-tables` — DashboardPage テーブル

**frontend/src/topbar.css**

- `@media (max-width: 767px)` ブロック（user-drawer 全幅・topbar-email 非表示）
- `.mobile-menu-btn` 以外の全定義

**frontend/src/mobile-shell.css**

- 全行残す（MobileShell 専用 CSS — 削除対象外）

### 変更しないもの

- `frontend/src/App.tsx` — ShellSwitch 実装済み。変更なし
- `frontend/src/components/DesktopShell.tsx` — mobile コード削除済み（PR-R2-C）。変更なし
- `frontend/src/components/MobileShell.tsx` — 変更なし
- `frontend/src/tokens.css` — 変更なし
- 削除対象以外の CSS ファイル — 変更なし

---

## 弊害 / トレードオフ

| リスク | 評価 | 対策 |
|---|---|---|
| `.sidebar-panel` が 767px 以下で表示される | 軽微。MobileShell では `#sidebar-panel` は DOM に存在しないため適用されない | Playwright で 375px/MobileShell に sidebar-panel がないことを確認 |
| `.app-body` margin-left 削除の影響 | 軽微。DesktopShell は 768px 以上でのみ使用。768px 以上では `@media (max-width: 767px)` は適用されない | desktop-shell.spec.ts で 1280px での崩れ確認 |
| `.mobile-menu-btn` CSS 削除後の LST バグ | なし。DOM からも削除済み（PR-R2-C）。参照する TSX ゼロ | grep で確認済み |

---

## 実装計画票

| ステップ | 作業 | 成果物 |
|---|---|---|
| 1 | docs/handoff/mobile-shell-pr-r2d/ 作成 | recon.md / design.md |
| 2 | responsive.css の PR-R1 ハック削除 | frontend/src/responsive.css |
| 3 | topbar.css の .mobile-menu-btn / .sidebar-mobile-backdrop 削除 | frontend/src/topbar.css |
| 4 | npm run check:all / npm run build / Playwright 実行 | CI pass |

---

## 外部・過去事例の参照と我々への応用

CSS migration において「機能を JS で分離した後に古い CSS を削除する」は Web 開発の標準的なクリーンアップ手順（ADR-137 §移行方針に明記）。
PR-R2-A〜C（NavItemList / MobileShell / ShellSwitch）の完了を確認してから CSS を削除する本アプローチは、
Shopify の Polaris 移行ガイドや GitHub の CSS モジュール化ガイドでも「ステップ分け削除（incremental removal）」として推奨されている手法。
小規模・削除のみの変更のため「該当する外部事例の詳細調査は不要」。

---

## 継続（次フェーズへの申し送り）

- PR-R2-D 完了後: PR-R1 CSS ハックはすべて削除完了。ADR-137 §移行方針を全件達成。
- 次フェーズ候補: tablet Shell の改善（ADR-137 §Alternatives §Option B: CSS Container Queries）
