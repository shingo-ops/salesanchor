# design: mobile-shell-pr-r2c

## 参照
- recon: docs/handoff/mobile-shell-pr-r2c/recon.md
- KGI/KPI 定義元: docs/handoff/mobile-shell-pr-r2/design.md
- ADR: ADR-137 §採用アーキテクチャ、ADR-067、ADR-027

---

## KGI（定量・PO承認）

docs/handoff/mobile-shell-pr-r2/design.md の KGI-1〜KGI-5 を全件達成すること。
本 PR-R2-C が担うのは KGI-1（PC非破壊）・KGI-2（MobileShell成立）・KGI-5（横スクロールなし）の自動検証追加と Shell 切り替えロジック実装。

| KGI | 内容 | 検証方法 |
|---|---|---|
| KGI-1 | 1280×800 で DesktopShell が崩れない | desktop-shell.spec.ts |
| KGI-2 | 375×812 で MobileShell が成立する | mobile-shell.spec.ts |
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

---

## 技術 How

### Shell 切り替え: ShellSwitch コンポーネント

App.tsx に `ShellSwitch` を定義し、`ProtectedRoute` の children として配置。

```tsx
// App.tsx 内
function ShellSwitch() {
  const isMobile = useIsMobile();
  return isMobile ? <MobileShell /> : <DesktopShell />;
}

// Routes 内
<Route element={<ProtectedRoute><ShellSwitch /></ProtectedRoute>}>
  ...
</Route>
```

- `useIsMobile()` は BrowserRouter 内でレンダリングされるため利用可
- CSS @media による hide/show ではなく DOM 切り替え（ADR-137 §採用アーキテクチャ）
- 767px 以下 → MobileShell、768px 以上 → DesktopShell

### DesktopShell.tsx（Layout.tsx rename + 整理）

Layout.tsx を DesktopShell.tsx にリネームし、mobile 固有コードを削除する。

削除するもの:
- `isMobileSidebarOpen` state と setter
- `openMobileSidebar` 関数
- `closeMobileSidebar` 関数
- Escape key handler（isMobileSidebarOpen 依存）
- `sidebar-mobile-backdrop` DOM 要素
- `sidebar-mobile-open` クラス付与
- `mobile-menu-btn` ボタン

変更するもの:
- `handleNavClick` を削除し、nav item の onClick を `handleSidebarLeave` に統一
- export 名を `Layout` から `DesktopShell` に変更

### App.tsx 変更

- `import Layout from "./components/Layout"` → `import DesktopShell from "./components/DesktopShell"`
- `import MobileShell from "./components/MobileShell"` を追加
- `import { useIsMobile } from "./hooks/useIsMobile"` を追加
- `<Layout />` → `<ShellSwitch />`

### Layout.tsx 削除

`frontend/src/components/Layout.tsx` は DesktopShell.tsx に完全移行後、git rm で削除する。

---

## 弊害 / トレードオフ

| リスク | 対策 |
|---|---|
| リサイズ中の再レンダリング | useIsMobile は matchMedia change event で更新。UI が一瞬ちらつく可能性あり。現状 CSR のみのため許容 |
| Layout.tsx import の削除 | App.tsx が唯一の consumer のため影響範囲は 1 ファイル |

---

## 実装計画票

| ステップ | 作業 | 成果物 |
|---|---|---|
| 1 | docs/handoff/mobile-shell-pr-r2c/ 作成 | recon.md / design.md |
| 2 | DesktopShell.tsx 作成（Layout.tsx から mobile コード削除） | frontend/src/components/DesktopShell.tsx |
| 3 | App.tsx 修正（ShellSwitch 追加・import 変更） | frontend/src/App.tsx |
| 4 | Layout.tsx 削除 | git rm frontend/src/components/Layout.tsx |
| 5 | E2E specs 作成 | desktop-shell.spec.ts / mobile-shell.spec.ts / horizontal-overflow.spec.ts |
| 6 | npm run check:all / npm run build / Playwright 実行 | CI pass |

---

## 外部事例

docs/handoff/mobile-shell-pr-r2/design.md §外部・過去事例 参照（Meta / GitHub / Shopify / Salesforce）。JS 判定での DOM 切り替えが業界標準。

---

## PO確定方針（PR-R2 引き継ぎ）

| # | 確定内容 |
|---|---|
| ① ShellSwitch 配置 | ProtectedRoute children として App.tsx 内に定義 |
| ② Layout rename | DesktopShell.tsx。export default も DesktopShell |
| ③ handleNavClick 統一 | handleSidebarLeave に置換（PC は mouse leave で sidebar 折りたたみ） |
| ④ tablet 扱い | 768px 以上は DesktopShell |

---

## 継続（次フェーズへの申し送り）

- PR-R2-D: responsive.css の PR-R1 CSS ハック削除（mobile-menu-btn の CSS が残存）
- PR-R2-C マージ後、MobileShell の本番動作確認を経てから PR-R2-D 実施
