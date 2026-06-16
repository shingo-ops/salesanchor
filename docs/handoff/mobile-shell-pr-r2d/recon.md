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
2. `frontend/src/topbar.css` — .mobile-menu-btn 定義と .sidebar-mobile-backdrop 定義削除

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

## 削除した CSS（PR-R1 ハック）

### frontend/src/responsive.css から削除

以下のルールは PR-R1 が追加した App Shell mobile ハック。MobileShell（PR-R2-A〜C）の完成により不要となったため削除済み。

- `.sidebar-panel { transform: translateX(-100%); }` — MobileShell では #sidebar-panel は DOM に存在しない
- `.sidebar-panel.sidebar-mobile-open { transform: translateX(0); }` — isMobileSidebarOpen state は PR-R2-C で削除済み
- `.app-body { margin-left: 0; }` — MobileShell では .app-body は使用しない
- `.mobile-menu-btn { display: flex; }` — .mobile-menu-btn DOM は PR-R2-C で削除済み
- `@media (min-width: 768px) { .mobile-menu-btn { display: none; } }` ブロック全体 — 上記と同理由

### frontend/src/topbar.css から削除

- `.mobile-menu-btn { ... }` 定義 — PR-R1 ハンバーガーボタン。DesktopShell.tsx から削除済み（PR-R2-C）
- `.mobile-menu-btn:hover { ... }` — 同上
- `.sidebar-mobile-backdrop { ... }` — PR-R1 モバイルバックドロップ。sidebar-mobile-backdrop div は PR-R2-C で削除済み

---

## 残存 CSS の確認（削除後の現在地）

### frontend/src/responsive.css — 残したルール

削除後 43 行。`@media (max-width: 767px)` ブロック内に以下のみ残存:

| 現在地 | クラス | 残す理由 |
|---|---|---|
| `frontend/src/responsive.css:20` | `.page { padding: var(--space-4); }` | MobileShell 内でも .page クラスは使用される |
| `frontend/src/responsive.css:25` | `.roles-layout { grid-template-columns: 1fr; }` | RolesPage のモバイルレイアウト。PR-R1 とは無関係 |
| `frontend/src/responsive.css:29` | `.roles-sidebar { position: static; }` | 同上 |
| `frontend/src/responsive.css:33` | `.roles-main-header { flex-direction: column; ... }` | 同上 |
| `frontend/src/responsive.css:39` | `.dashboard-tables { grid-template-columns: 1fr; }` | DashboardPage のモバイルテーブル。PR-R1 とは無関係 |

### frontend/src/topbar.css — 残したルール

削除後 278 行。以下は PR-R1 とは無関係のため残存:

| 現在地 | クラス | 残す理由 |
|---|---|---|
| `frontend/src/topbar.css:109` | `.avatar-btn { ... }` | DesktopShell の固定アバターボタン |
| `frontend/src/topbar.css:138` | `.user-drawer-backdrop { ... }` | ユーザードロワーのバックドロップ |
| `frontend/src/topbar.css:268` | `@media (max-width: 767px)` ブロック | user-drawer 全幅・topbar-email 非表示（PR-R1 とは無関係） |

### frontend/src/mobile-shell.css — 全行残す

MobileShell 専用スタイル（PR-R2-B 追加）。削除対象外。

| 現在地 | クラス | 役割 |
|---|---|---|
| `frontend/src/mobile-shell.css:8` | .mobile-shell | MobileShell ルート |
| `frontend/src/mobile-shell.css:15` | .mobile-topbar | sticky header |
| `frontend/src/mobile-shell.css:29` | .mobile-topbar-hamburger | ハンバーガーボタン |
| `frontend/src/mobile-shell.css:46` | .mobile-topbar-title | タイトル |
| `frontend/src/mobile-shell.css:57` | .mobile-topbar-avatar | アバター（in-flow） |
| `frontend/src/mobile-shell.css:79` | .mobile-drawer-backdrop | ドロワーバックドロップ（z-index:200） |
| `frontend/src/mobile-shell.css:88` | .mobile-drawer | ドロワーパネル（z-index:210） |
| `frontend/src/mobile-shell.css:101` | .mobile-drawer--open | 開閉状態クラス |
| `frontend/src/mobile-shell.css:144` | .mobile-content | Outlet 表示エリア |

### ShellSwitch（変更なし）

| 現在地 | 内容 |
|---|---|
| `frontend/src/App.tsx:120` | `function ShellSwitch()` — useIsMobile() → MobileShell/DesktopShell 切替 |

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
