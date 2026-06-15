# design: mobile-shell-pr-r2a

## 参照
- recon: docs/handoff/mobile-shell-pr-r2a/recon.md
- PR-R2 evidence: docs/handoff/mobile-shell-pr-r2/design.md
- ADR: ADR-137 / ADR-067 / ADR-027

---

## KGI（定量・PO承認必須）

### KGI-1: NavItemList が SSoT として機能する

| 確認項目 | 期待値 |
|---|---|
| nav items 定義が 1ファイル | DesktopShell / MobileShell が同一の nav items source を参照できる構造 |
| NavItemList が純粋描画コンポーネント | 権限判定・未読バッジ計算を内部で行わない |
| variant prop で PC / Mobile の描画差異を吸収 | desktop / mobile で表示形式を切り替え可能 |

### KGI-2: useIsMobile が正しく動作する

| 確認項目 | 期待値 |
|---|---|
| 375px で true を返す | window.matchMedia (max-width: 767px) が matches: true |
| 1280px で false を返す | window.matchMedia (max-width: 767px) が matches: false |
| リサイズ時に再レンダリングする | change イベントで state 更新 |
| cleanup が正しく実行される | removeEventListener が呼ばれる |

### KGI-3: 既存 Layout.tsx を破壊しない

| 確認項目 | 期待値 |
|---|---|
| Layout.tsx の変更ゼロ | PR-R2-A では Layout.tsx を変更しない |
| 既存 E2E spec が退行しない | `npm run test:e2e -- --project=chromium` が全 pass |

---

## KPI / 検証方法

| 基準（KPI） | 目標値 | 検証方法 |
|---|---|---|
| KPI-1: NavItemList unit test | 全 pass | Vitest または Playwright component test |
| KPI-2: useIsMobile unit test | 全 pass | Vitest (jsdom) でブレークポイント境界値テスト |
| KPI-3: 既存 E2E 退行なし | 0件退行 | `npx playwright test --project=chromium` |
| KPI-4: lint / check 全 pass | 0件 | `npm run check:all` |

---

## 技術 How（設計方針）

### NavItemList.tsx（新規）

`frontend/src/components/NavItemList.tsx`

```tsx
interface ResolvedNavItem {
  key: string;
  labelKey: string;        // i18n key
  icon: React.ReactNode;
  path: string;
  children?: ResolvedNavItem[];
  unread?: boolean;
}

interface NavItemListProps {
  items: ResolvedNavItem[];
  onNavClick: () => void;
  variant: 'desktop' | 'mobile';
  unreadCount?: number;
}

export function NavItemList({ items, onNavClick, variant, unreadCount }: NavItemListProps) {
  // 純粋描画: 権限判定・バッジ計算は親が実行済み
}
```

型定義は `NavItemList.tsx` 内で export し、将来の types/ 移動は別 PR で対応。

### useIsMobile.ts（新規）

`frontend/src/hooks/useIsMobile.ts`

BREAKPOINTS.MOBILE_MAX (= 767) を参照。
window.matchMedia のみ使用（resize イベント直接監視は使わない）。
SSR 将来対応時は再設計が必要（現時点は CSR のみ）。

### nav items 定義の SSoT

既存 Layout.tsx の nav items 定義（`frontend/src/components/Layout.tsx:163-370`）は PR-R2-A では触らない。
NavItemList を先に定義し、PR-R2-B / PR-R2-C で Layout.tsx から切り出す。

---

## 弊害 / トレードオフ

| リスク | 対策 |
|---|---|
| NavItemList が PR-R2-A 段階では未使用 | PR-R2-B で MobileShell から利用開始。未使用コードとして短期間残る |
| useIsMobile が PR-R2-A 段階では未使用 | PR-R2-C で App.tsx が利用。同上 |
| ResolvedNavItem 型の将来の変更 | NavItemList.tsx 内で型定義し、変更時は1ファイルのみ更新 |

---

## 実装計画票

| フェーズ | 成果物 | 含まれる変更 |
|---|---|---|
| PR-R2-A（本PR） | NavItemList.tsx + useIsMobile.ts + tests | 新規ファイルのみ。既存ファイル変更ゼロ |
| PR-R2-B | MobileShell.tsx + mobile-shell.css | MobileShell 実装（NavItemList / useIsMobile を利用） |
| PR-R2-C | App.tsx Shell 切り替え + DesktopShell rename | PR-R2-B 完成後 |
| PR-R2-D（別PR） | PR-R1 CSS ハック削除 | MobileShell 本番動作確認後 |

---

## 検証計画

### 実装後チェック

```bash
cd frontend
npm run check:all
npx playwright test --project=chromium
```

### unit test 対象

| テスト | 内容 |
|---|---|
| NavItemList rendering | items=[...] で各 nav item が表示される |
| NavItemList onNavClick | nav item クリックで onNavClick が呼ばれる |
| NavItemList variant | desktop / mobile で適切なクラスが付与される |
| useIsMobile 375px | MOBILE_MAX 以下で true |
| useIsMobile 1280px | MOBILE_MAX 超で false |
| useIsMobile cleanup | unmount 時 removeEventListener |

---

## 外部・過去事例

ADR-137 §採用事例（docs/handoff/mobile-shell-pr-r2/design.md）参照済み。PR-R2-A は NavItemList の props 設計において Shopify Polaris の `navigationItems` props 共通化パターンを踏襲する。新規調査不要。

---

## PO確定方針（2026-06-15）

recon.md の不明点①〜③について、PO（shingo-ops）が以下のとおり方針確定。

| # | 確定内容 | 実装への影響 |
|---|---|---|
| ① 型定義場所 | ResolvedNavItem は NavItemList.tsx 内で定義・export。新規 types/ ファイルは作らない。複数ファイル利用が増えた段階で別PRにて型ファイルへ移動 | NavItemList.tsx の先頭に `export interface ResolvedNavItem {...}` を置く |
| ② accordion 移植範囲 | `children?: ResolvedNavItem[]` を受け取り子項目を描画できる最小構造まで。SidebarAccordion の開閉 state 完全移植はしない。saasAdmin / more の本格 accordion 挙動は PR-R2-B/C | PR-R2-A は描画・onNavClick・variant class の unit test を優先する |
| ③ unit test vs E2E | unit test 主体（Vitest）。NavItemList: rendering / onNavClick / variant / children 表示。useIsMobile: 375px true / 1280px false / change event / cleanup。新規 E2E spec は MobileShell 接続後の PR-R2-B/C で追加 | PR-R2-A では npx playwright test を既存退行確認として実行するのみ（新規 spec 追加なし） |

### 実装制約（PO指定）

- 既存 Layout.tsx 変更なし
- 既存 sidebar.css 変更なし
- 既存 topbar.css 変更なし
- 既存 App.tsx / route 変更なし
- 新規ファイルのみ（PC 既存 UI/UX に影響を出さない）

---

## 継続（次フェーズへの申し送り）

- 不明点①〜③はすべて PO確定済み（上記「PO確定方針」参照）
- PR-R2-B 着手前に NavItemList.tsx の型定義と props 設計を確認すること
- PR-R2-B の MobileShell は NavItemList の variant='mobile' を利用する
- PR-R2-C の App.tsx は useIsMobile() の戻り値で Shell を条件レンダリングする
