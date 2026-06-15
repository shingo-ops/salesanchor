# recon: mobile-shell-pr-r2a

## 調査日: 2026-06-15

## 参照元
- PR-R2 evidence package: docs/handoff/mobile-shell-pr-r2/recon.md, design.md（#2209 マージ済み）
- ADR: ADR-137 / ADR-067 / ADR-027

---

## PR-R2-A スコープ

### 実装対象（3ファイル）

1. `frontend/src/components/NavItemList.tsx`（新規）— 共通 nav item builder
2. `frontend/src/hooks/useIsMobile.ts`（新規）— JS 判定 Shell 切り替え hook
3. `frontend/tests-e2e/nav-item-list.spec.ts` または unit test（新規）— minimal tests

### 実装対象外（PR-R2-A に含めない）

- `frontend/src/components/Layout.tsx` の変更（DesktopShell への rename は PR-R2-C）
- `frontend/src/components/MobileShell.tsx` の新規作成（PR-R2-B）
- `frontend/src/App.tsx` の Shell 切り替えロジック（PR-R2-C）

---

## 既存 nav item 定義の調査

### 現状: Layout.tsx にインライン定義

`frontend/src/components/Layout.tsx:163-370` — nav items が Layout.tsx に直接インライン定義

主要構造（要確認）:
- 権限判定（userPermissions / currentUser によるフィルタ）
- アコーディオン形式の階層メニュー（saasAdmin, more accordion 等）
- 未読バッジカウント（unreadCount）
- i18n キー参照（t("nav.xxx")）
- 各 NavLink / sidebar-item の onClick で closeMobileSidebar 呼び出し

### NavItemList が受け取る props 設計（PO確定 #2209）

```tsx
interface NavItemListProps {
  items: ResolvedNavItem[];   // 権限 filter 済みの nav items
  onNavClick: () => void;
  variant: 'desktop' | 'mobile';
  unreadCount?: number;
}
```

権限判定・未読バッジカウントは親（DesktopShell / MobileShell）で実行。
NavItemList は純粋な描画のみ担当（SSoT: nav items 定義ファイルを1箇所に）。

---

## 既存 hooks 確認

### hooks ディレクトリ

`frontend/src/hooks/` — 既存 hooks の確認が必要

### useIsMobile 設計（ADR-137 §採用アーキテクチャ）

```ts
// frontend/src/hooks/useIsMobile.ts
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

`frontend/src/constants/breakpoints.ts:19-24` — MOBILE_MAX: 767 を参照

---

## アイコン管理ルール

`frontend/src/constants/icons.tsx` — 全アイコンはここから import（lucide-react 直接 import 禁止、ESLint 強制）

---

## i18n ルール（ADR-027）

新規 aria-label は必ず t("key") 経由。
`frontend/src/i18n/ja.json` と `frontend/src/i18n/en.json` の両方に追加必須。

---

## 不明点 → PO確定済み（2026-06-15）

| # | 確定方針 |
|---|---|
| ① ResolvedNavItem 型 | NavItemList.tsx 内で定義・export。新規 types/ ファイルは作らない |
| ② accordion 移植範囲 | children?: ResolvedNavItem[] の最小構造まで。開閉 state 完全移植は PR-R2-B/C |
| ③ unit test vs E2E | unit test 主体（Vitest）。新規 E2E spec は PR-R2-B/C で追加 |
