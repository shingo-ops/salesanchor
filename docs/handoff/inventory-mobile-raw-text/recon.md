# recon: スマホの在庫カードから原文を見られるようにする（便1）

> 設計書 `docs/handoff/inventory-mobile-raw-text/design.md` ②の表に挙げた事実を、この worktree の実ファイルで確かめ直す。全て `フルパス:行番号` で引用する。推測した事実には「未確認」と明記する。

worktree: `/root/worktrees/salesanchor/release-inventory-mobile-raw-text`（ブランチ `release/inventory-mobile-raw-text`・`origin/main` 起点）。

## 1. `frontend/src/components/DataTable.tsx` — カード表示・mobileHidden/mobileOrder/mobileLabel・セル内ボタンの非発火

- カード表示切替の分岐: `frontend/src/components/DataTable.tsx:176`（`const cardMode = mobileCards && isMobile;`）と `frontend/src/components/DataTable.tsx:278`（`if (cardMode) {`）。
- 列定義のモバイル用フィールド定義: `frontend/src/components/DataTable.tsx:60-65`
  ```
  60:  /** カード表示（mobileCards）での並び順。小さい順。無い列は後ろに元の順で並ぶ */
  61:  mobileOrder?: number;
  62:  /** カード表示で隠す */
  63:  mobileHidden?: boolean;
  64:  /** カード表示のラベル（無ければ header） */
  65:  mobileLabel?: string;
  ```
  列の指定に「PC で隠す」に相当するフィールドは無い（`mobileHidden`／`mobileOrder`／`mobileLabel` の3つのみ、他列フィールドは `key`/`header`/`width`/`ellipsis`/`sortable`/`align`/`stickyLeft`/`renderCell`）。
- カード表示での列の並び替え・除外ロジック: `frontend/src/components/DataTable.tsx:279-288`（`mobileHidden` を `filter` で除外・`mobileOrder` で `sort`）。
- カードのラベル描画（`mobileLabel ?? header`）: `frontend/src/components/DataTable.tsx:330`。
- **セル内のボタンで行クリックが発火しない**仕様の該当コード:
  - 判定関数 `isInteractiveTarget`: `frontend/src/components/DataTable.tsx:136-140`
    ```
    136: function isInteractiveTarget(e: MouseEvent | KeyboardEvent): boolean {
    137:   return !!(e.target as HTMLElement).closest(
    138:     'button, a, input, select, textarea, label',
    139:   );
    140: }
    ```
  - カード（`comp-table__card`）の `onClick` 内でこの判定を使い早期 return: `frontend/src/components/DataTable.tsx:306-309`
    ```
    306:  onClick={clickable ? (e: MouseEvent<HTMLDivElement>) => {
    307:    if (isInteractiveTarget(e)) return;
    308:    onRowClick(row);
    309:  } : undefined}
    ```
  - 同じ判定が PC の `<tr>` 側にも使われている: `frontend/src/components/DataTable.tsx:418-421`。
- 結論: セル内に `<button>` を置けば、そのボタンを押しても `onRowClick` は呼ばれない（`closest('button, ...')` が真になるため）。設計 3-1 の「ボタンはセルの中に置くのが素直」は裏取りできた。

## 2. `frontend/src/components/Drawer.tsx` / `Drawer.css` — スマホ幅で全画面になる根拠

- `Drawer` の props コメントに z-index の記載: `frontend/src/components/Drawer.tsx:12`（`* z-index: --z-drawer (301) — Modal の overlay は --z-modal (400) で前面`）。
- パネル本体の実装: `frontend/src/components/Drawer.tsx:129-136`（`className="comp-drawer-panel..."`、`role="dialog"` 等）。
- CSS 側:
  - 既定の `width`/`height`/`z-index`: `frontend/src/components/Drawer.css:25-41`
    ```
    25: .comp-drawer-panel {
    26:   position: fixed;
    27:   top: 0;
    28:   right: 0;
    29:   height: 100dvh;
    30:   width: var(--drawer-panel-w-default);
    ...
    33:   z-index: var(--z-drawer);
    ```
  - スマホ幅（767px 以下）の上書き: `frontend/src/components/Drawer.css:109-113`
    ```
    109: @media (max-width: 767px) { /* = --breakpoint-mobile-max */
    110:   .comp-drawer-panel {
    111:     width: 100%;
    112:   }
    113: }
    ```
  - `top: 0`（`:27`）と `height: 100dvh`（`:29`）はブレークポイントに関係なく常時適用。767px 以下では `width` も 100% になるため、`top:0 / height:100dvh / width:100%` が揃い、**すでに全画面**。
- `--z-drawer` の実際の値: `frontend/src/tokens.css:127`（`--z-drawer: 301; /* avatar(300)より前面 — user-drawer-close 直接クリック可 */`）。
- 結論: 設計②の「Drawer はスマホ幅で width:100%、top:0・height:100dvh・z-index:301（すでに全画面）」は裏取りできた。全画面化のための新しい部品は不要。

## 3. `frontend/src/features/inventory/InventoryRowDrawer.tsx` — タブ構成・権限分岐・原文 API

- 権限分岐の入口: `frontend/src/features/inventory/InventoryRowDrawer.tsx:201-205`
  ```
  201: export function InventoryRowDrawer({ row, onClose, onChanged, isSuperAdmin }: Props) {
  ...
  205:   if (!isSuperAdmin) return <RawTextPane row={row} onClose={onClose} onChanged={onChanged} />;
  ```
  super admin でなければ常に `RawTextPane`（原文だけ）。super admin は「解析｜原文」の `Tabs`（`frontend/src/features/inventory/InventoryRowDrawer.tsx:207-222`）。
- 原文を取る API 呼び出し: `frontend/src/features/inventory/InventoryRowDrawer.tsx:142-143`
  ```
  142:  api
  143:    .get<RawTextsResponse>(`/inventory/raw-texts?${params.toString()}`)
  ```
- `RawTextPane` は `Drawer` を `size="wide"` で呼ぶ: `frontend/src/features/inventory/InventoryRowDrawer.tsx:172-177`。`size="wide"` は PC では 1100px 幅（`frontend/src/components/Drawer.css:48-50` `--drawer-panel-w-wide`）だが、767px 以下の `@media` が後に効くため（`Drawer.css:109` のブロックが `--wide` より後に書かれており、かつ `max-width` メディアクエリはカスケードで優先）スマホでは100%になる。実測は本便の e2e で確認する（下記8節）。
- 結論: タブ構成・権限分岐・原文 API は既存のまま使われており、本便はこのファイルを変更しない（設計 3-4 のとおり）。

## 4. `frontend/src/pages/inventory/InventoryPage.tsx` — `columns` の `useMemo`・`onRowClick` の条件・`drawerRow` state

- `columns` の `useMemo`: `frontend/src/pages/inventory/InventoryPage.tsx:178-181`
  ```
  178:  const columns = useMemo(
  179:    () => buildInventoryColumns({ t, colVisible, fmtOfferedAt }),
  180:    [t, colVisible],
  181:  );
  ```
  現在の依存配列は `[t, colVisible]`。`isMobile` は入っていない（本便で追加する対象）。
- `isMobile` の取得: `frontend/src/pages/inventory/InventoryPage.tsx:142`（`const isMobile = useIsMobile();`）。
- `drawerRow` state: `frontend/src/pages/inventory/InventoryPage.tsx:144`（`const [drawerRow, setDrawerRow] = useState<InventoryRow | null>(null);`）。
- `onRowClick` の条件（スマホで無効）: `frontend/src/pages/inventory/InventoryPage.tsx:579`
  ```
  579:        onRowClick={!isMobile ? (row) => setDrawerRow(row) : undefined}
  ```
- `DataTable` 呼び出しの `mobileCards` 指定: `frontend/src/pages/inventory/InventoryPage.tsx:593`（`mobileCards`）。
- ドロワーのマウント: `frontend/src/pages/inventory/InventoryPage.tsx:597`
  ```
  597:  {drawerRow && <InventoryRowDrawer row={drawerRow} isSuperAdmin={isSuperAdmin} onClose={() => setDrawerRow(null)} onChanged={() => { void load(); }} />}
  ```
- 結論: 設計 3-1・3-2 が指す行はすべて現物で確認できた。`columns` の `useMemo` に `isMobile` を依存として足し、`onRowClick` の式 (`:579`) は変更しない。

## 5. `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx` — F2b の内容

- `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx:100-120`
  ```
  100:  it('F2b: on mobile the panel does not open for anyone', async () => {
  101:    const original = window.matchMedia;
  102:    window.matchMedia = ((query: string) => ({
  103:      matches: true, media: query, onchange: null,
  ...
  110:    const rowEl = await screen.findByTestId('inventory-row-r1');
  111:    await new Promise((r) => setTimeout(r, 30));
  112:    fireEvent.click(rowEl);
  113:    await new Promise((r) => setTimeout(r, 30));
  114:    const rawCalls = mock.get.mock.calls.filter(([u]) => String(u).startsWith('/inventory/raw-texts'));
  115:    expect(rawCalls).toHaveLength(0);
  116:    expect(analysisCalls()).toHaveLength(0);
  117:    } finally {
  118:      window.matchMedia = original;
  119:    }
  120:  });
  ```
  `window.matchMedia` を強制的に `matches: true`（常にモバイル判定）に差し替え、カード本体（`rowEl` = `data-testid="inventory-row-r1"`、`frontend/src/pages/inventory/InventoryPage.tsx:578` の `rowTestId`）をクリックしても API が呼ばれないことを確認している。「誰も開けない」ことを固定するテストであり、本便で「カード本体では開かない／原文ボタンでは開く」に書き換える対象。
- 行の `data-testid` の付与元: `frontend/src/pages/inventory/InventoryPage.tsx:578`（`rowTestId={(it) => \`inventory-row-${it.id}\`}`）。

## 6. `frontend/src/components/Button.tsx` / `buttonAppearance.ts` / `Button.css` — `size="lg"` + `iconOnly` が 44px になる根拠

- `Button` 本体の props: `frontend/src/components/Button.tsx:41-56`（`size="md"` 既定・`iconOnly` は `buttonAppearance` に渡すだけ）。
- クラス組み立て: `frontend/src/components/buttonAppearance.ts:33-43`
  ```
  33:  return [
  34:    "comp-btn",
  35:    VARIANT_CLASS[variant],
  36:    isTab ? "" : (size === "sm" ? "comp-btn--sm" : size === "lg" ? "comp-btn--lg" : ""),
  ...
  40:    iconOnly   ? "comp-btn--icon-only" : "",
  ```
  `size="lg"` → `comp-btn--lg`、`iconOnly` → `comp-btn--icon-only`。
- CSS 側の寸法確定: `frontend/src/components/Button.css:148-152`
  ```
  148: .comp-btn--lg.comp-btn--icon-only {
  149:   width: var(--size-icon-btn-lg);
  150:   height: var(--size-icon-btn-lg);
  151:   min-height: var(--size-icon-btn-lg);
  152: }
  ```
  さらに 767px 以下では `.comp-btn.comp-btn--icon-only` 自体が強制的に 44px になる（`frontend/src/components/Button.css:163-167`、`@media (max-width: 767px)`〈`:154-168`〉内）。
- トークンの値: `frontend/src/tokens.css:163`（`--size-icon-btn-lg: 44px; /* lg アイコンボタン（モバイルタッチターゲット基準 WCAG 2.5.5） */`）。
- 結論: `Button` に `size="lg"` と `iconOnly` を渡すだけで、スマホ幅では 44×44px が確定する（独自の寸法指定は不要）。設計②の記載を裏取りできた。

## 7. `frontend/src/constants/icons.tsx` — 使えそうな既存の絵柄

- アイコンの唯一の置き場であることのコメント: `frontend/src/constants/icons.tsx:1-12`（「全コンポーネントはここからインポートすること」）。
- 文書・紙・テキスト系の既存の絵柄（すでに `hi()` でラップ済みだが、どの公開グループにも入っていないもの）:
  - `FileText`（`DocumentTextIcon` solid）: `frontend/src/constants/icons.tsx:103`（`const FileText = hi(DocumentTextIcon);`）。import 元: `frontend/src/constants/icons.tsx:33`。
  - `FileTextOutline`（`DocumentTextIcon` outline）: `frontend/src/constants/icons.tsx:129`（`const FileTextOutline = hi(DocumentTextOutlineIcon);`）。すでに `NAV_ICONS.fileText` として公開済み: `frontend/src/constants/icons.tsx:212`。
  - `ClipboardText`（`ClipboardDocumentListIcon`）: `frontend/src/constants/icons.tsx:102`。既に `PAGE_ICONS.kartePanel`（受信箱のカルテボタン用）として使用中: `frontend/src/constants/icons.tsx:186`。原文ボタンとは別の既存用途があるため使い回さない。
- 結論: `FileText`（`frontend/src/constants/icons.tsx:103`）は `PAGE_ICONS` 等の公開グループに未登録の既存の絵柄で、「原文（文書）」の絵柄として使える。新しい SVG を描かず、`PAGE_ICONS` に1行足して公開する（例: `rawText: FileText`）。

## 8. 下部タブバー（class名・z-index）がどこで定義されているか

- 定義元: `frontend/src/components/MobileShell.tsx`。クラス付与箇所: `frontend/src/components/MobileShell.tsx:267`（`<nav className="mobile-tabbar" aria-label={t("nav.openMenu")}>`）。構成コメント: `frontend/src/components/MobileShell.tsx:16`（`* ├── MobileTabBar (.mobile-tabbar — position:fixed, bottom:0, z-index: var(--z-topbar)=100)`）。
- CSS: `frontend/src/mobile-shell.css:95-108`
  ```
  95: /* ---- MobileTabBar: fixed bottom tab bar ---- */
  96: .mobile-tabbar {
  97:   position: fixed; /* fixed-ok: persistent bottom nav */
  98:   bottom: 0;
  99:   left: 0;
  100:   right: 0;
  101:   z-index: var(--z-topbar); /* 100 */
  102:   height: var(--tabbar-height, 56px);
  ```
- トークン値: `frontend/src/tokens.css:123`（`--z-topbar: 100;`）。
- `Drawer` の z-index は `--z-drawer`=301（`frontend/src/tokens.css:127`）。301 > 100 であり、`.comp-drawer-panel` と `.mobile-tabbar` はどちらも `position: fixed` で同じスタッキングコンテキスト（body 直下）に属する。z-index の比較だけからは Drawer が前面に出るはずだが、**実際に覆えているか（`elementFromPoint` で判定が返るのが Drawer 側の要素か）は未確認**。設計 3-3 のとおり e2e で実測する（本報告の実装セクションに実測結果を記載）。
- 既存テストでの確認箇所（参考・クラス名の裏取り）: `frontend/src/components/MobileShell.test.tsx:163-165`
  ```
  163:  it("renders .mobile-tabbar", () => {
  ...
  165:    expect(container.querySelector(".mobile-tabbar")).toBeTruthy();
  ```

## 9. 既存の在庫 e2e（`frontend/tests-e2e/inventory-table-layout.spec.ts`）の書き方

- ログイン手順: 通常の LoginPage は経由せず、`installAuthBypass(page)`（`frontend/tests-e2e/inventory-table-layout.spec.ts:49` → 定義は `frontend/tests-e2e/utils/auth.ts`）が `localStorage` にダミーユーザーを注入して保護ページを直接描画する。
- API モック: `mockApi(page, { ...commonMocks(), "GET /inventory": {...}, "GET /me/inventory-filters": {...}, "GET /products/tcg-types": [...] })`（`frontend/tests-e2e/inventory-table-layout.spec.ts:50-71`）。`commonMocks()`（`frontend/tests-e2e/utils/common-mocks.ts:38-54`）が `/me/permissions`・`/staff/me` を返す（`is_super_admin` は含まれない＝未指定時は非 super admin 相当。実際の判定ロジックは `useSuperAdmin` フック側・本便では確認不要）。
- 待ち方: `setViewportSize` → `installAuthBypass` → `mockApi` → `page.goto("/inventory")` → `await expect(page.getByTestId("inventory-row-row-1")).toBeVisible();` で最初の行が描画されるのを待つ（`frontend/tests-e2e/inventory-table-layout.spec.ts:75-80`）。375px のテストでは `thead` が存在しないこと（カード表示）も確認している（`:80`）。
- 行の `data-testid` パターン: `inventory-row-<id>`（モック行の id は `row-1`, `row-2`, …、`frontend/tests-e2e/inventory-table-layout.spec.ts:22`）。カード（`role="listitem"`）のセレクタ例: `'[data-testid^="inventory-row-"][role="listitem"]'`（`:83`）。
- 1440px のテストは `.comp-table-fit__card` の CSS 変数で判定しており、ボタン数を数える既存例は無い（本便が新規）。

## 10. その他（設計の裏取り）

- 前便の「触らない範囲」記載: `docs/handoff/inventory-row-drawer/design.md:39`
  ```
  39: - スマホのカード表示（`mobileCards`）からの開閉。PC の表のクリックだけを対象にする。
  ```
  裏取りできた（原文どおり）。
- i18n キー `inventory.rowDrawer.*` の既存状況: `frontend/src/locales/ja.json:1463-1471` と `frontend/src/locales/en.json:1463-1471` にキー数・構造が一致している（`title`/`loadError`/`notFound`/`itemTab`/`tabAnalysis`/`tabRawText`/`rawTextTitle`）。本便で追加するキー（例: `openButton`）はこのオブジェクトに両ファイル同じ場所へ追加する。
- `inventoryColumns.tsx` の列定義パターン（`hideId`/`col` の組で `all` 配列に積み、`colVisible` で絞る）: `frontend/src/features/inventory/inventoryColumns.tsx:53-213`。本便で足す列もこのパターンに従う（ただし PC では出さないため `hideId: null` 固定にはできず、呼び出し側 `isMobile` 分岐で列配列自体を組み替える方式にする。設計 3-1 のとおり）。

## 未確認（推測せず明記）

- Drawer（`size="wide"`）が実際にスマホ幅でタブバーを覆うかどうかは、z-index の数値比較だけでは確定しない。e2e の `document.elementFromPoint()` 実測が必要（設計 3-3 のとおり、実装セクションで実測し `design.md` に追記する）。
- `.claude-pipeline/active-work.d/release-inventory-mobile-raw-text.md` は worktree 内に存在しない（`ls` で確認・該当ファイルなし）。依頼文は「担当機能エリア欄が未記入」という前提だが、ファイル自体が無い。実装報告で明記する。
