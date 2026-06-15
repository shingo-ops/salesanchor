# recon: mobile-shell-pr-r2

## 調査日: 2026-06-15

## 関連ADR検索結果

| キーワード | 結果 |
|---|---|
| `git grep -i "responsive\|mobile-shell\|MobileShell"` docs/adr/ | ADR-137 のみ（2026-06-15 新規） |
| `git grep -i "breakpoint"` docs/adr/ | ADR-054, ADR-057（LP用のみ）, ADR-067 |
| `git grep -i "shell\|layout"` docs/adr/ | ADR-022（サイドバー設計）, ADR-137（Adaptive Shell） |
| `git grep -i "topbar\|navigation"` docs/adr/ | ADR-022 のみ |

---

## PC 既存仕様

### app-shell 構造

`frontend/src/components/Layout.tsx:196` — ルート要素 `div.app-shell`
`frontend/src/sidebar.css:10-15` — `.app-shell { display: flex; height: 100vh; overflow: hidden }`

```
app-shell (flex row)
├── sidebar-panel (position: fixed, left:0, z-index:200)
└── app-body (flex:1, margin-left:54px)
    └── app-content → Outlet
```

topbar は独立した in-flow 要素として存在しない。avatar-btn が position:fixed で右上に常時表示される。

### sidebar-panel

`frontend/src/sidebar.css:18-32`
```css
.sidebar-panel {
  width: var(--sidebar-width-collapsed, 54px);   /* 折りたたみ幅 */
  position: fixed; left: 0; top: 0;
  height: 100vh;
  z-index: var(--z-sidebar);  /* 200 */
  transition: width var(--transition-sidebar);   /* 250ms ease */
}
```

`frontend/src/sidebar.css:34-36`
```css
.sidebar-panel.sidebar-expanded {
  width: var(--sidebar-width-expanded, 240px);  /* hover 展開幅 */
}
```

### sidebar hover expand

`frontend/src/components/Layout.tsx:210-211`
```tsx
onMouseEnter={() => setSidebarExpanded(true)}
onMouseLeave={handleSidebarLeave}
```

`frontend/src/components/Layout.tsx:159-162` — `handleSidebarLeave` は `setSidebarExpanded(false)` + `setOpenAccordion(null)`

### sidebar-expanded class / label表示

`frontend/src/components/Layout.tsx:209` — `sidebar-panel${sidebarExpanded ? " sidebar-expanded" : ""}${isMobileSidebarOpen ? " sidebar-mobile-open" : ""}`

sidebar-expanded が true のときのみ `.sidebar-label` が visible になる（sidebar.css 内の opacity/width 制御）。

### accordion 開閉

`frontend/src/components/Layout.tsx:153-157` — `toggleAccordion()` で `setOpenAccordion()` + `setSidebarExpanded(true)`（accordion 展開時は必ず sidebar も展開）

### app-body margin-left

`frontend/src/sidebar.css:246` — `.app-body { margin-left: var(--sidebar-width-collapsed, 54px) }`

responsive.css の mobile rule で上書き:
`frontend/src/responsive.css:35-37`（PR-R1 worktree）— `@media (max-width: 767px) { .app-body { margin-left: 0 } }`

### avatar button

`frontend/src/topbar.css:138-158`
```css
.avatar-btn {
  position: fixed;
  top: var(--avatar-zone-top);    /* 12px — tokens.css:177 */
  right: var(--avatar-zone-right); /* 16px — tokens.css:178 */
  width/height: var(--avatar-zone-width); /* 40px — tokens.css:179 */
  z-index: var(--avatar-zone-z);  /* 300 — tokens.css:180 */
}
```

`frontend/src/components/Layout.tsx:427-435` — click で `setDrawerOpen(true)`

### user drawer

`frontend/src/topbar.css:152-166` — `.user-drawer { position: fixed; right:0; width: var(--drawer-width)=300px; z-index: var(--z-drawer)=299; transform: translateX(100%) }`

`frontend/src/topbar.css:168-170` — `.user-drawer--open { transform: translateX(0) }`

---

## Mobile 現状課題

### PR-R1 responsive.css mobile rules

`frontend/src/responsive.css:20-80`（PR-R1 worktree / 本番反映済み）

主要 rule:
- `.sidebar-panel { transform: translateX(-100%); transition: width ..., transform ... }` → sidebar を画面外へ
- `.sidebar-panel.sidebar-mobile-open { transform: translateX(0); width: 240px }` → open 時にオーバーレイ表示
- `.app-body { margin-left: 0 }` → sidebar 分余白を除去
- `.mobile-menu-btn { display: flex }` → hamburger 表示
- `@media (min-width: 768px) { .mobile-menu-btn { display: none } }` → desktop では非表示

### mobile-menu-btn 実装（PR-R1）

`frontend/src/topbar.css:112-130` — `position: fixed; top: var(--avatar-zone-top); left: var(--space-4); z-index: var(--avatar-zone-z)=300`

`frontend/src/components/Layout.tsx:417-425` — click で `openMobileSidebar()` 呼び出し

### PC sidebar と mobile 開閉 state の混在

`frontend/src/components/Layout.tsx:109-111` — 1つの Layout.tsx に PC 用 state と Mobile 用 state が同居:
```tsx
const [sidebarExpanded, setSidebarExpanded] = useState(false);  // PC: hover expand
const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);  // Mobile: hamburger
```

`frontend/src/components/Layout.tsx:131-140` — `openMobileSidebar` / `closeMobileSidebar` が `sidebarExpanded` を副作用として操作（PC hover と mobile open が状態を共有）

`frontend/src/components/Layout.tsx:165` — `handleNavClick = () => closeMobileSidebar()` — PC でも nav click のたびに mobile state reset を呼ぶ（副作用は無害だが責務が不明確）

### MobileShell 分離が必要な理由

1. **DOM 重複**: モバイルで `.sidebar-panel` が DOM に存在し続ける（CSS で隠れているだけ）。スクリーンリーダーが sidebar のナビ項目を2回読む可能性（aria-hidden 未指定）。
2. **State 混在**: `sidebarExpanded`（PC hover用）と `isMobileSidebarOpen`（mobile用）が同一コンポーネントに混在し、互いに副作用を持つ（openMobileSidebar が sidebarExpanded を true にする）。
3. **topbar 欠如**: Mobile に適した topbar が存在しない。hamburger が `position: fixed` で浮いているだけで、ページタイトルとの関係が定義されていない。
4. **一時対応 CSS の蓄積**: PR-R1 の `.sidebar-panel { transform: translateX(-100%) }` は PC 構造を前提にした CSS ハック。ADR-137 の「一時対応 CSS を重ね続けて構造問題を隠さない」禁止事項に該当。

---

## SSoT 確認

### ブレークポイント

`frontend/src/tokens.css:113-116`
```css
--breakpoint-mobile-max:   767px;
--breakpoint-tablet-min:   768px;
--breakpoint-tablet-max:  1279px;
--breakpoint-desktop-min: 1280px;
```

`frontend/src/constants/breakpoints.ts:19-24`
```ts
MOBILE_MAX:   767,
TABLET_MIN:   768,
TABLET_MAX:  1279,
DESKTOP_MIN: 1280,
```

tokens.css と breakpoints.ts は一致している ✅
`check-breakpoint-sync.js` により CI で自動検証される。

### z-index hierarchy

`frontend/src/tokens.css:120-129`
```
--z-topbar:          100  → MobileTopBar はここ
--z-sidebar:         200  → MobileDrawer はここ
--z-sidebar-overlay: 210  → （将来用）
--z-backdrop:        298  → Mobile backdrop はここ
--z-drawer:          299  → user-drawer はここ
--z-avatar:          300  → avatar-btn はここ（MobileTopBar 内アバターも合わせる）
--z-modal:           400
--z-toast:           500
```

MobileDrawer backdrop (298) < MobileDrawer (200) の逆転問題:

**不明点①** — `--z-backdrop: 298` は user-drawer の backdrop 用（`topbar.css:139`）。Mobile sidebar backdrop に同じ値を使うと user-drawer backdrop より低い（298）が MobileDrawer（200）より高く、MobileDrawer の上に backdrop が表示される。MobileShell 実装時は `--z-sidebar-overlay: 210` を MobileDrawer の overlay（backdrop）専用として割り当てるか、新しいtoken `--z-mobile-drawer-backdrop` を追加するか PO 確認が必要。

### icon size tokens

`frontend/src/tokens.css:195-199`
```
--icon-sm:    14px
--icon-md:    16px
--icon-base:  20px
--icon-lg:    24px
```

`frontend/src/constants/iconSizes.ts`（Mirror: tokens.css に明記）

### ADR-067 Design Token enforcement

`docs/adr/ADR-067-design-token-enforcement.md` — 色・余白・サイズを直書き禁止。MobileShell の新規CSS変数は `:root` に追加し、暗色モード（`:root.force-dark`）にも追記必須。

### nav item 定義（現状）

`frontend/src/components/Layout.tsx:163-370` — nav items は Layout.tsx に直接インライン定義されている。現時点では PC/Mobile 共通の「nav item builder」コンポーネント・関数は存在しない。

**不明点②** — MobileShell の nav item 表示には、Layout.tsx の inline定義（権限判定・未読バッジ・アコーディオン等）をそのまま流用するか、shared nav builder を切り出すかを設計フェーズで決定する必要がある。

---

## Vite build 設定（hotfix #2198 反映済み）

`frontend/vite.config.ts`（現在）— `build.cssTarget: ['chrome87', 'safari14', 'firefox78', 'edge88']` により CSS Level 4 range 構文の生成を防止。`max-width: 767px` 形式が維持される。

---

## 不明点まとめ

| # | 不明点 | 判断が必要な理由 |
|---|---|---|
| ① | MobileDrawer backdrop の z-index | --z-backdrop(298) > --z-sidebar(200) のため MobileDrawer 背後に backdrop が隠れる。--z-sidebar-overlay(210) 利用 or 新 token 追加の判断が必要 |
| ② | nav item builder の新設範囲 | Layout.tsx の inline 権限判定・未読バッジをどこまで共通 builder として切り出すかで実装規模が変わる |
| ③ | avatar-btn の mobile 扱い | 現状 position:fixed で MobileTopBar 外に浮いている。MobileTopBar にインライン配置するか、引き続き fixed で運用するかを決定する必要がある |
| ④ | タブレット（768-1279px）のShell | ADR-137 では DesktopShell / MobileShell の2分割だが、タブレットはどちらのShellを使うか（BreakpointsはMOBILE_MAX=767/TABLET_MIN=768で3段階定義済み） |
