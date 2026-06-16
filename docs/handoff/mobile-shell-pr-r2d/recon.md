# recon: mobile-shell-pr-r2d

## 調査日: 2026-06-16

## 参照元

- PR-R2 design: docs/handoff/mobile-shell-pr-r2/design.md（KGI/KPI 定義元）
- PR-R2-C recon: docs/handoff/mobile-shell-pr-r2c/recon.md（DesktopShell rename・mobile コード削除の証拠）
- ADR: ADR-137 / ADR-067 / ADR-027

---

## PR-R2-D スコープ

PR-R1（#2156）が追加した mobile sidebar CSS ハックを削除する。
PR-R2-C で DesktopShell.tsx から mobile 固有コード（DOM 要素・state）は削除済み。
残存しているのは CSS のみ。

### 実装対象

1. `frontend/src/responsive.css` — PR-R1 App Shell mobile ハック（6 ルール）削除
2. `frontend/src/topbar.css` — `.mobile-menu-btn` 定義と `.sidebar-mobile-backdrop` 定義削除

### 実装対象外（PR-R2-D に含めない）

- `frontend/src/mobile-shell.css`（MobileShell 専用 CSS — すべて残す）
- `frontend/src/components/DesktopShell.tsx`（変更なし）
- `frontend/src/App.tsx`（変更なし）
- migrations / deploy.yml / 本番 scripts

---

## 既存 ADR 検索結果

```bash
git grep -i "mobile" docs/adr/  # → ADR-137（採用アーキテクチャ）が該当
```

| ADR | 関連内容 |
|---|---|
| ADR-137 §移行方針 | "MobileShell が完成したら PR-R1 の CSS ハックを削除し、DesktopShell と切り替える" |
| ADR-067 §Design Token | CSS 変数のみ使用・hex/マジックナンバー禁止 |
| ADR-027 §i18n | 今回変更なし |

---

## 削除対象 CSS（file:line）

### frontend/src/responsive.css

| 行 | クラス | 削除理由 |
|---|---|---|
| `frontend/src/responsive.css:19-28` | `.sidebar-panel { transform: translateX(-100%); ... }` | PR-R1 ハック。MobileShell では `#sidebar-panel` は DOM に存在しない |
| `frontend/src/responsive.css:31-34` | `.sidebar-panel.sidebar-mobile-open { transform: translateX(0); ... }` | PR-R1 ハック。`isMobileSidebarOpen` state は DesktopShell.tsx から削除済み（PR-R2-C） |
| `frontend/src/responsive.css:37-39` | `.app-body { margin-left: 0; }` | PR-R1 ハック。MobileShell では `.app-body` は使用しない |
| `frontend/src/responsive.css:43-45` | `.mobile-menu-btn { display: flex; }` | PR-R1 ハック。`mobile-menu-btn` は DesktopShell.tsx から削除済み（PR-R2-C） |
| `frontend/src/responsive.css:73-79` | `@media (min-width: 768px) { .mobile-menu-btn { display: none; } }` ブロック全体 | PR-R1 ハック。`.mobile-menu-btn` が DOM に存在しなくなったため不要 |

また、`@media (max-width: 767px)` ブロック内のコメント（行 19-22 / 30-31 / 36-37 / 41-43）も削除対象（削除対象ルールへの説明コメントのため）。

### frontend/src/topbar.css

| 行 | クラス | 削除理由 |
|---|---|---|
| `frontend/src/topbar.css:108-135` | `.mobile-menu-btn { ... }` + `.mobile-menu-btn:hover { ... }` | PR-R1 ハンバーガーボタン定義。DesktopShell.tsx から削除済み（PR-R2-C）。MobileTopBar は `.mobile-topbar-hamburger`（mobile-shell.css）を使用 |
| `frontend/src/topbar.css:294-302` | `.sidebar-mobile-backdrop { ... }` | PR-R1 モバイルバックドロップ。`sidebar-mobile-backdrop` div は DesktopShell.tsx から削除済み（PR-R2-C）。MobileShell は `.mobile-drawer-backdrop`（mobile-shell.css）を使用 |

---

## 削除してはいけない CSS（file:line）

### frontend/src/responsive.css — 残すルール

| 行 | クラス | 残す理由 |
|---|---|---|
| `frontend/src/responsive.css:47-51` | `.page { padding: var(--space-4); }` | page コンテンツのモバイルパディング。MobileShell でも `.page` クラスは使用される |
| `frontend/src/responsive.css:53-55` | `.roles-layout { grid-template-columns: 1fr; }` | RolesPage のモバイルレイアウト。PR-R1 とは無関係 |
| `frontend/src/responsive.css:57-59` | `.roles-sidebar { position: static; }` | 同上 |
| `frontend/src/responsive.css:61-64` | `.roles-main-header { flex-direction: column; align-items: stretch; }` | 同上 |
| `frontend/src/responsive.css:67-70` | `.dashboard-tables { grid-template-columns: 1fr; }` | DashboardPage のモバイルテーブル。PR-R1 とは無関係 |

### frontend/src/topbar.css — 残すルール

| 行 | クラス | 残す理由 |
|---|---|---|
| `frontend/src/topbar.css:307-311` | `@media (max-width: 767px) { .user-drawer { width: 100%; } }` | ユーザードロワーの mobile 全幅表示。PR-R1 とは無関係 |
| `frontend/src/topbar.css:313-315` | `.topbar-email { display: none; }` | 狭い画面でのメール非表示。PR-R1 とは無関係 |

### frontend/src/mobile-shell.css — 全行残す

MobileShell 専用スタイル（PR-R2-B 追加）。削除してはいけない。

| 対象 | 残す理由 |
|---|---|
| `frontend/src/mobile-shell.css:8-12` | `.mobile-shell` ルート |
| `frontend/src/mobile-shell.css:15-27` | `.mobile-topbar` sticky header |
| `frontend/src/mobile-shell.css:29-72` | `.mobile-topbar-hamburger`, `.mobile-topbar-title`, `.mobile-topbar-avatar` |
| `frontend/src/mobile-shell.css:79-103` | `.mobile-drawer-backdrop`, `.mobile-drawer`, `.mobile-drawer--open` |
| `frontend/src/mobile-shell.css:106-147` | `.mobile-drawer-header`, `.mobile-drawer-nav` 等 |
| `frontend/src/mobile-shell.css:149-151` | `.mobile-content` |

---

## PR-R1 クラスの TSX 参照確認

DesktopShell.tsx のコメント行以外に TSX/TS での参照なし:

```bash
grep -rn "mobile-menu-btn|sidebar-mobile-backdrop|sidebar-mobile-open" \
  frontend/src/ --include="*.tsx" --include="*.ts"
# → frontend/src/components/DesktopShell.tsx:6 (コメントのみ)
```

E2E spec での参照なし:

```bash
grep -rn "mobile-menu-btn|sidebar-mobile-backdrop|sidebar-mobile-open" \
  frontend/tests-e2e/
# → 0件
```

---

## 不明点 → なし

削除対象・保持対象ともに明確。PR-R1 クラスは TSX・E2E から参照されていないことを確認済み。
