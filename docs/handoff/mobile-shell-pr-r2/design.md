# design: mobile-shell-pr-r2

## 参照
- recon: docs/handoff/mobile-shell-pr-r2/recon.md
- ADR: ADR-137-adaptive-shell-architecture.md, ADR-067-design-token-enforcement.md, ADR-022.md, ADR-027-ui-internationalization.md

---

## KGI（定量・PO承認必須）

### KGI-1: PC既存UX 非破壊

1280×800 / 1440×900 / 1920×1080 で以下が退行しない。

| 確認項目 | 期待値 |
|---|---|
| DesktopSidebar 表示（collapsed 54px） | sidebar-panel visible, width=54px |
| hover expand | sidebar-panel width → 240px, sidebar-expanded class 付与 |
| nav click で active 遷移 | 各 route へ正しく遷移 |
| avatar-btn クリック → user drawer 開く | user-drawer--open class 付与 |
| user drawer の theme / language 切り替え | 機能維持 |
| accordion 展開・折りたたみ | saasAdmin / more accordion が動作 |

### KGI-2: Mobile 専用 Shell 成立

375×812 / 390×844 / 414×896 で以下を満たす。

| 確認項目 | 期待値 |
|---|---|
| 左 rail が表示されない | .sidebar-panel が DOM に存在しない か 非可視 |
| MobileTopBar が表示される | hamburger / title / avatar が 1行に収まる |
| hamburger / title / avatar が重ならない | 各要素の BoundingRect が重複しない |
| hamburger クリック → MobileDrawer が開く | drawer visible, overlay 表示 |
| backdrop クリック → MobileDrawer が閉じる | drawer hidden |
| nav item クリック → MobileDrawer が閉じる + 遷移 | drawer hidden + route 変更 |
| Escape キー → MobileDrawer が閉じる | drawer hidden |
| 未読バッジが MobileDrawer 内ナビに表示される | unreadCount > 0 時にバッジ表示 |

### KGI-3: SSoT 維持

| 確認項目 | 期待値 |
|---|---|
| nav item 定義が 1箇所 | DesktopShell / MobileShell が同一の nav item source を参照 |
| PC / Mobile でメニュー定義を二重管理しない | nav items リストが 1ファイルで定義 |
| 色・余白・z-index・サイズ が token 参照 | 新規 CSS に hex / px マジックナンバーがない |
| ADR-067 darkmode token 対応 | 新規色 token が :root と :root.force-dark 両方に存在 |

### KGI-4: Safari 互換

| 確認項目 | 期待値 |
|---|---|
| build 後 dist CSS に `width<=767px` が 0件 | `grep "width<=" dist/assets/*.css` → 0件 |
| build 後 dist CSS に `max-width:767px` が存在する | `grep "max-width" dist/assets/*.css` → 1件以上 |

`frontend/vite.config.ts` の `build.cssTarget: ['chrome87', 'safari14', 'firefox78', 'edge88']` が維持されていること。

### KGI-5: 主要ページ横スクロールなし

375px で以下 6 route が横スクロールなし。

| route | 確認方法 |
|---|---|
| / | `document.documentElement.scrollWidth > window.innerWidth` → false |
| /lead-chat | 同上 |
| /crm | 同上 |
| /inventory | 同上 |
| /quotes | 同上 |
| /orders | 同上 |

---

## KPI / 検証方法

| KPI | 目標値 | 検証方法 |
|---|---|---|
| KPI-1: Desktop 非退行率 | 100% | desktop-shell.spec.ts — Playwright Chromium 1280×800/1440×900 |
| KPI-2: MobileShell 成立率 | 100% | mobile-shell.spec.ts — Playwright Chromium 375×812/390×844/414×896 |
| KPI-3: 対象 route 横スクロールゼロ | 100% | horizontal-overflow.spec.ts — 375px 全6 route |
| KPI-4: SSoT 逸脱ゼロ | 0件 | `npm run check:all`（stylelint / breakpoint-sync / ADR-067 lint） + `grep` |
| KPI-5: Visual evidence 取得完了 | 全 viewport | Playwright screenshot + Chromatic |
| KPI-6: Safari dist CSS compat | width<= 0件 | `grep "width<=" dist/assets/*.css` CI チェック |

---

## 技術 How（設計方針）

### Shell 切り替え方式

**window.matchMedia（JS 判定）を採用する。**

```tsx
// hooks/useIsMobile.ts
import { BREAKPOINTS } from '../constants/breakpoints';

export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia(`(max-width: ${BREAKPOINTS.MOBILE_MAX}px)`).matches
  );
  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${BREAKPOINTS.MOBILE_MAX}px)`);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);
  return isMobile;
}
```

App.tsx で `useIsMobile()` を呼び、`<DesktopShell>` または `<MobileShell>` を条件レンダリング。CSS @media による Shell 切り替えは行わない（ADR-137 §採用アーキテクチャに準拠）。

理由: CSS だけで両 Shell を DOM に持つと、スクリーンリーダーがナビを2回読む問題が残る。JS 判定により不要な Shell を DOM から除外する。

### DesktopShell（既存 Layout.tsx の責務）

`frontend/src/components/Layout.tsx` を `DesktopShell.tsx` に rename + 整理。
変更内容:
- `isMobileSidebarOpen` 関連 state と `openMobileSidebar` / `closeMobileSidebar` を削除
- `handleNavClick` を `handleSidebarLeave` に統一（PC のみ考慮）
- `mobile-menu-btn` を削除
- `sidebar-mobile-backdrop` を削除
- CSS: `responsive.css` の PR-R1 mobile rules（translateX等）は MobileShell 完成後に削除

### MobileShell（新規実装）

`frontend/src/components/MobileShell.tsx`（新規）

```
MobileShell
├── MobileTopBar (sticky, z-index: var(--z-topbar)=100)
│   ├── HamburgerButton (aria-controls="mobile-drawer")
│   ├── PageTitle (現在の route title — i18n)
│   └── AvatarButton (user-drawer trigger — 既存 avatar-btn と同機能)
├── MobileDrawer (position: fixed, z-index: var(--z-sidebar)=200)
│   └── nav items (shared NavItemList)
├── MobileDrawerBackdrop (position: fixed, z-index: var(--z-sidebar-overlay)=210)
└── app-content (flex:1, overflow-y: auto)
    └── Outlet
```

注意: MobileDrawerBackdrop は `--z-sidebar-overlay: 210` を使用（`--z-backdrop: 298` は user-drawer backdrop 専用のため流用しない）。この token 値の用途割り当てを実装時に明記すること。

### shared NavItemList（nav item builder）

`frontend/src/components/NavItemList.tsx`（新規）

DesktopShell の `SidebarAccordion` と同じ nav items を props 経由で受け取る共通コンポーネント。

```tsx
interface NavItemListProps {
  items: ResolvedNavItem[];   // 権限 filter 済みの nav items
  onNavClick: () => void;
  variant: 'desktop' | 'mobile';
  unreadCount?: number;
}
```

権限判定・未読バッジカウントは親（DesktopShell / MobileShell）で実行し、NavItemList は純粋な描画のみ担当。

### i18n

MobileTopBar の page title は route 定義から `navKey` を引く（既存 PageLayout の仕組みを流用）。
新規 aria-label は必ず `t("key")` 経由（ADR-027）。
新規 i18n キー（例: `nav.openDrawer`, `nav.closeDrawer`）は `ja.json` / `en.json` 両方に追加。

### CSS 新規追加分

`frontend/src/mobile-shell.css`（新規）

- `.mobile-topbar`: MobileTopBar のスタイル
- `.mobile-drawer`: MobileDrawer のスタイル（position:fixed, z-index:var(--z-sidebar)）
- `.mobile-drawer-backdrop`: overlay（position:fixed, z-index:var(--z-sidebar-overlay)）

すべての値は token 参照。hex / マジックナンバー禁止（ADR-067）。
`:root.force-dark` に対応した色 token を追加する場合は dark mode にも記載。

---

## 弊害 / トレードオフ

| リスク | 対策 |
|---|---|
| JS 判定の hydration ちらつき（SSR 将来対応時） | 現状は CSR のみのため問題なし。将来 SSR 導入時に再検討 |
| `useIsMobile` がリサイズ中に頻繁に再レンダリング | debounce or threshold で制御（実装時決定） |
| DesktopShell rename による import 一括変更 | `Layout.tsx` → `DesktopShell.tsx` の移動で全 import 更新。`App.tsx` の Routes 定義変更が必要 |
| PR-R1 CSS ハック削除タイミング | MobileShell 安定後に別 PR でまとめて削除する（PR-R2 に含めない） |
| tablets (768-1279px) の Shell | 不明点④参照。PR-R2 スコープ外として DesktopShell を適用する案が有力 |

---

## 実装計画票

| フェーズ | 成果物 | 含まれる変更 |
|---|---|---|
| PR-R2-A | NavItemList.tsx + useIsMobile.ts + tests | 新規コンポーネント・hook のみ。Layout.tsx 変更なし |
| PR-R2-B | MobileShell.tsx + mobile-shell.css + tests | MobileShell 新規実装。DesktopShell は変更なし |
| PR-R2-C | App.tsx Shell 切り替え + DesktopShell rename | Shell 切り替えロジック統合。E2E spec 更新 |
| PR-R2-D（別PR）| PR-R1 CSS ハック削除 | responsive.css の mobile rules 削除、mobile-menu-btn 削除 |

---

## 検証計画

### Manual viewport

| viewport | Shell | 確認内容 |
|---|---|---|
| 1280×800 | DesktopShell | KGI-1 全項目 |
| 1440×900 | DesktopShell | KGI-1 全項目 |
| 1920×1080 | DesktopShell | KGI-1 全項目 |
| 375×812 | MobileShell | KGI-2 全項目 |
| 390×844 | MobileShell | KGI-2 全項目 |
| 414×896 | MobileShell | KGI-2 全項目 |
| 768×1024 | DesktopShell（暫定） | 横スクロールなし |

### Routes

| route | 確認内容 |
|---|---|
| / | 横スクロール / 表示崩れ |
| /lead-chat | 横スクロール / inbox カルテ表示（既存退行なし） |
| /crm | 横スクロール / hub-shell 縦積み |
| /inventory | 横スクロール |
| /quotes | 横スクロール |
| /orders | 横スクロール |

### Automated specs（PR-R2 実装時に新規追加）

| spec | 検証内容 |
|---|---|
| `frontend/tests-e2e/desktop-shell.spec.ts` | KGI-1: Desktop 非退行（1280×800） |
| `frontend/tests-e2e/mobile-shell.spec.ts` | KGI-2: MobileShell 成立（375×812） |
| `frontend/tests-e2e/horizontal-overflow.spec.ts` | KGI-5: 全6 route 横スクロールなし |

### CSS compat チェック

```bash
# build 後確認
grep "width<=" frontend/dist/assets/*.css  # 0件であること
npm run check:all
npm run build
```

---

## 外部・過去事例

### 採用事例

**Meta Business Suite**: PC はサイドバー常時表示、mobile は bottom navigation + drawer を完全分離。DOM レベルで PC/Mobile コンポーネントを切り替え、CSS による hide/show ではない。

**GitHub.com**: `@media` ベースのサイドバー responsive ではなく、mobile 向けに `header-wrapper` + `drawer-component` を別 DOM として構築。PC 用 `AppHeader` を mobile では非表示にする CSS ではなく、mobile専用 `AppHeader` コンポーネントを条件レンダリング。

**Shopify Admin**: Polaris `Frame` コンポーネントが `NavigationOverlay`（mobile drawer）と `Navigation`（desktop sidebar）を別コンポーネントとして提供。JS `useBreakpoints()` hook で判定し DOM 切り替え。Nav items は `navigationItems` props として共通化。

**Salesforce Lightning**: `slds-navigation-list-*` は PC 専用、mobile は `slds-context-bar` に完全切り替え。Nav items は `ui:menuItem` として共通化し、Shell が選択。

**我々への応用**: nav items の共通化 (NavItemList) + JS 判定での Shell DOM 切り替えは、業界標準のアプローチ。CSS @media だけでの PC/Mobile 分離は DOM の重複・アクセシビリティ問題を抱えるため採用しない。

---

## PO確定方針（2026-06-14）

recon.md の不明点①〜④について、PO（shingo-ops）が以下のとおり方針確定。実装時に迷った場合はこのセクションを参照すること。

| # | 確定内容 | 実装への影響 |
|---|---|---|
| ① backdrop z-index | `--z-sidebar-overlay: 210` を MobileDrawer overlay 専用に割り当てる。`--z-backdrop: 298` は user-drawer backdrop 専用のまま流用しない | `mobile-shell.css` の `.mobile-drawer-backdrop { z-index: var(--z-sidebar-overlay) }` で実装 |
| ② nav item builder | 共通ソースを新設（`NavItemList.tsx` + nav items 定義ファイル）。PC/Mobile で二重管理禁止。PR-R2-A はビルダー実装から開始する | PR-R2-A スコープ: `NavItemList.tsx` + nav items SSoT + `useIsMobile.ts` |
| ③ avatar-btn mobile | MobileTopBar 内に配置。hamburger / page title / avatar の3要素を1行横並び。`position: fixed` での浮かせ配置は廃止 | `MobileTopBar` は `{ display: flex; align-items: center }` の in-flow 要素として実装 |
| ④ tablet Shell | **767px 以下のみ MobileShell、768px 以上は DesktopShell**（タブレットは DesktopShell 扱い）。ADR-137 の DesktopShell / MobileShell 2分割に準拠 | `useIsMobile`: `MOBILE_MAX = 767` の matchMedia で判定。分岐は2値のみ |

---

## 継続（次フェーズへの申し送り）

- 不明点①〜④はすべて PO確定済み（上記「PO確定方針」参照）
- PR-R2-A 着手時: `NavItemList.tsx` / nav items SSoT / `useIsMobile.ts` + tests のみ実装する
- PR-R2-B 着手時: `MobileTopBar`（hamburger / title / avatar 横並び）+ `MobileDrawer`（`--z-sidebar: 200`）+ `MobileDrawerBackdrop`（`--z-sidebar-overlay: 210`）
- PR-R2-C 着手時: `App.tsx` で `useIsMobile()` による Shell 条件レンダリング導入 + `Layout.tsx` → `DesktopShell.tsx` rename
- PR-R1 CSS ハック削除（PR-R2-D）は MobileShell の本番動作が確認されてから別 PR で実行すること
