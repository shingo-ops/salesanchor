# recon — page-header-sticky-revert

**仕事名**: page-header-sticky-revert
**日付**: 2026-06-23
**対象ADR**: ADR-067（デザイントークン強制）
**担当**: Hikky-dev

---

## 概要

全 PageLayout ページで「ヘッダーが 1 段下にズレ、上部に白帯が出て背景グラデが透過しない」症状の真因調査。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages-layout.css:62-69` | `.page-layout-header` に #2432(7c5a5ea2) が追加した 4 行（position/top/z-index/background）が現存 |
| `frontend/src/sidebar.css:238-245` | `.app-body { background-image: var(--inbox-bg-gradient); }` — グラデ供給元（現存） |
| `frontend/src/topbar.css:97-102` | `.app-content { background: transparent; }` — app-body グラデを透過させる設計（現存） |
| `frontend/src/index.css:162` | `--inbox-bg-gradient` ライト定義（radial-gradient 2層） |
| `frontend/src/index.css:345` | `--inbox-bg-gradient` ダーク定義（暗色版） |
| `frontend/src/tokens.css:154` | `--topbar-height: 56px` — top: var(--topbar-height) の実値 |
| `frontend/src/components/DesktopShell.tsx:382-387` | `.app-topbar` DOM 要素が存在しない（JSX に記述なし） |

---

## 真因の確定

### 問題の 4 行（blame: origin/main, 全て `7c5a5ea2` 単独）

```css
/* frontend/src/pages-layout.css:62-69 (origin/main) */
.page-layout-header {
  flex-shrink: 0;
  padding: var(--page-padding-y) var(--page-header-avatar-clearance) 0 var(--page-padding-x);
  position: sticky;              /* 7c5a5ea2 #2432 2026-06-21 */
  top: var(--topbar-height);     /* 7c5a5ea2 #2432 2026-06-21 = 56px */
  z-index: var(--z-topbar);      /* 7c5a5ea2 #2432 2026-06-21 */
  background: var(--bg-surface); /* 7c5a5ea2 #2432 2026-06-21 — 不透過 */
}
```

2 つの副作用:
1. **白帯・1段下ズレ**: `top: 56px` は `.app-topbar` 存在前提。だが `.app-topbar` DOM は `9ab5f6cf`(2026-05-22)「トップバー廃止・固定アバターボタン化」で削除済み。存在しないバー分の 56px 空白が白帯として露出。
2. **背景が白い**: `background: var(--bg-surface)`（不透過）でヘッダー部分のグラデ透過が潰れる。

### 除去後の到達点（#2432 直前 `2e23c7db` の定義）

```css
.page-layout-header {
  flex-shrink: 0;                 /* 2b5322c4 2026-05-24 */
  padding: var(--page-padding-y) var(--page-header-avatar-clearance) 0 var(--page-padding-x); /* ba565cf3 2026-05-25 */
}
```

### schedule 非依存（除去で壊れない）

- `.schedule-grid__viewport { overflow-y: auto }` — 独自スクロール領域 (`schedule.css`)
- `.schedule-grid__header { position: sticky; top: 0 }` — viewport 内ローカル (`top: 0`)
- `.schedule-grid__allday-row { position: sticky; top: var(--schedule-day-head-h) }` — viewport 内ローカル
- `.schedule-page { height: 100% }` — page-level scroll 抑制

現行 SchedulePage（カレンダー本体）は PageLayout 不使用（thin wrapper）のため `.page-layout-header` 自体が存在しない。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `position: sticky; top: 56px` の出自 | `git blame origin/main -- frontend/src/pages-layout.css` | ✅ 解消済み（7c5a5ea2 #2432 単独） |
| 2 | `.app-topbar` DOM が現在も存在するか | DesktopShell.tsx JSX 確認 | ✅ 解消済み（存在しない） |
| 3 | schedule スクロールが sticky に依存するか | schedule.css + #2432 diff 確認 | ✅ 解消済み（非依存） |

**未解決ゼロ確認**: 全て解消済み
