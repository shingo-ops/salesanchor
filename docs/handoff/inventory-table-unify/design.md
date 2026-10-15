# design — アプリの在庫表を GAS 在庫一覧と同じ作りにする（2026-10-15）

状態: 設計審査済み r3 APPROVE（Opus 作成・Opus Architect 審査。同一 AI の自己審査）。
根拠: [recon.md](recon.md)。審査 r1 の全文: /tmp/CC報告ファイル/app_inventory_recon_20261015/review_design_r1.txt
recon の正式パス: docs/handoff/inventory-table-unify/recon.md。関係 ADR（recon §0）: ADR-093・ADR-1014・ADR-067・ADR-144・ADR-027・ADR-087・ADR-140・ADR-1017。

## PO の決定と許可の出所（審査 r1 B-10）

- Q14=y（アプリの在庫表も同じ部品で作る）の原文: PO の 2026-10-15 のチャット「アプリの在庫表も同じ作りにする」。記録はメモ project_session_20261015_viewer_autonomy（Claude のメモ置き場・リポジトリ外）（引用元 design.md:393 は「確認中」のまま。閲覧ページ設計の書き直し時に決定へ直す＝審査 r2 N-r2-4）。
- 12 項目の回答（2026-10-15）: release/gas-viewer-fresh-fast の docs/handoff/gas-viewer-fresh-fast/design.md「PO 決定（2026-10-15、アプリと GAS の差分12項目への回答…）」。7 見出しの固定・8 表を縮めて画面に収める・9 スマホの縦カード・10 色つきバッジ・11 発送日の列は「採用」、4 提供者は「選んだ人だけ出す、レイアウトも同じ」、12「ページ送り機能をつける」。
- 金型の新設の許可: 同 design.md の Q10 は「金型が無い4部品（24時間スイッチ・複数選択・倍率合わせ・スマホの縦カード）をどうするか。金型の登録には PO の許可が要る」と問い、PO は上の回答で複数選択（4）・倍率合わせ（8）・縦カード（9）を「採用」とした（同 design.md「Q10 の4部品のうち3つを『採用』と決定」）。さらに PO の 2026-10-15 の指示原文「フロントエンドのパーツもデザイントークンとデザインシステム を遵守して、金型登録のないハードコードを禁止する」「アプリの在庫表も同じ作りにする」（Q14=y）。よって MultiSelect の新設と DataTable の機能追加（見出し固定・縮小・カード表示）は、PO が採用した3部品を金型として登録する作業として行う。24時間スイッチは対象外（アプリに既にあり、PO の回答に無い）。
- 更新ボタン（項目1）は未決 → 入れない。

## KGI（PO が画面で ○× を判定できる形）

1. 在庫表で「ぽけもん」と打つと「ポケモン」を含む商品が出る。○×
2. 空白で2語（例「ポケモン 151」）を打つと、両方を含む行だけが出る。○×
3. 提供者を2人選ぶと、その2人の行だけが出る。「選択をクリア」で全員に戻る。○×
4. PC で下へスクロールしても見出しの行が上に残り、商品名の列が左に残る。○×
5. PC（768px 以上）で窓の幅を狭めると、横スクロールが出ずに表全体が縮む。○×
6. スマホ（767px 以下）では、1行が縦のカードになり、横にはみ出さない。○×
7. 並び替えのプルダウンに「価格が安い順／在庫が多い順／投稿が新しい」の3つがある。初めて開いたときは発売日の新しい順で、プルダウンは「並び替え」と出る。○×
8. 状態の列が色つきバッジ（sealed 緑・damaged 赤・case 青・ほかグレー）。○×
9. TCGシリーズ（カテゴリ）の列が無い。○×
10. ページ送り（前へ／次へ・件数）が残っている。○×

## 対象と対象外

- 対象: 在庫表（/inventory）の画面、在庫表 API の q と提供者の絞り込み、共通の金型（DataTable の追加機能・MultiSelect の新設）。
- 対象外: 閲覧専用ページの実装（ADR-1017・PR #4283 側。その設計の書き直しは別に行う）、更新ボタン、英語名が空の 33 商品の登録、DB の列（hidden_supplier_ids は残す）、/inventory/search（別 API）、GAS 側、見積・請求の画面（inventory.view.searchPlaceholder を使う QuoteCreatePage.tsx:262・InvoiceCreatePage.tsx:413 は触らない）。

## 便の分け方（1便1テーマ）

| 便 | 中身 | 触る層 | GO 記録 |
|---|---|---|---|
| 便1 | 金型: DataTable に testid の口・列の右寄せ・見出し固定・縮小・カード表示、MultiSelect 新設 | frontend/src/components, hooks, constants, tokens.css | 不要（画面のみ。migration・deploy.yml・本番 scripts なし） |
| 便2 | 在庫表を DataTable と Badge へ載せ替え、並び替えプルダウン、カテゴリ列削除 | frontend/src/pages/inventory, features/inventory, locales | 不要 |
| 便3 | 検索（GAS と同じ正規化・AND）と提供者（選んだ人だけ） | backend router + frontend + api-contract | 不要（migration なし） |

各便とも: origin/main 起点、PR は merge commit、画面だけの便は CI 緑で Opus 判断でマージ。

## 便1 金型

### 1-0. 既存の利用を変えない約束
新しい props はすべて省略可で、省略時の DOM・クラス名は今と同じ（DataTable.tsx:174 のラッパー `<div class="comp-table" role="region">` の中に table とページ送り :303-327）。既存の DataTable テストと Storybook がそのまま通ること。

### 1-0b. matchMedia が無い環境（審査 r2 B-12）
- 【事実】jsdom には window.matchMedia が無く、frontend/src/test-setup.ts にもモックが無い（前例: InboxMessageThread.discordSendError.test.tsx:17-20 が個別にモック）。DataTable を使うテストは 56 ファイル。
- 対処: `frontend/src/hooks/useIsMobile.ts` の初期値と useEffect の両方で `typeof window.matchMedia !== "function"` なら false を返し、購読しない（フックは React の規則上いつも呼ぶので、フックの中で守る）。useFitTableZoom も同じ判定で、無ければ何もしない。
- DataTable は `useIsMobile()` を常に呼ぶが、カード表示にするのは `mobileCards && isMobile` のときだけ。
- useIsMobile.test.ts に「matchMedia が無いと false」を1件足す。

### 1-1. testid・読込中・右寄せの口（審査 r1 B-1・B-6）
- `rowTestId?: (row: T) => string` → tr（DataTable.tsx:246-265）とカード表示の各カードに `data-testid`。
- `paginationTestIds?: { prev: string; next: string; label: string }` → 前へ・次への Button（:305-325）と件数の span（:314）に `data-testid`。
- `paginationDisabled?: boolean` → true のとき前へ・次へを両方 disabled。前へは今どおり `page <= 1` でも disabled（`disabled={page <= 1 || paginationDisabled}`）、次へは `!hasNextPage || paginationDisabled`。
- 列 `align?: "left" | "right" | "center"`（既定 left）→ th と td に `comp-table__cell--align-right` などのクラス（CSS は text-align のみ）。

### 1-2. 見出し固定 `stickyHeader` と列の `stickyLeft`（審査 r1 B-2・B-3）
- DOM（stickyHeader か fitToWidth のどちらかが true のとき）:
  ```
  div.comp-table-frame (role="region"・幅の基準)
    div.comp-table-fit__card   ← fitToWidth のときだけ。縮める箱
      div.comp-table.comp-table--sticky   ← スクロールする箱（stickyHeader のときだけ --sticky）
        table
    div.comp-table__pagination  ← ページ送り。スクロール箱と縮める箱の外（縮まない・スクロールしなくても見える）
  ```
  どちらも false なら 1-0 のとおり今の DOM。
- 新トークン（tokens.css の --comp-table-* の並び :507-521 に追加）: `--comp-table-sticky-max-h: calc(100vh - 18rem);`（前例 components.css:136-155 と同じ値）。
- CSS（DataTable.css。値はすべて var()）:
  - `.comp-table--sticky { max-height: var(--comp-table-sticky-max-h); overflow: auto; }`
  - `.comp-table--sticky thead th { position: sticky; top: 0; z-index: var(--z-base); background: var(--bg-subtle); }`（今の見出し背景は tr の `.comp-table__head-row { background: var(--bg-subtle) }`（DataTable.css:83）。sticky の th 自身にも同じ値を持たせる）
  - 固定列のクラスは3つ（th と td の両方に付ける）:
    - `comp-table__cell--sticky-check` … selectable かつ固定列があるときの選択列。`left: 0`
    - `comp-table__cell--sticky-left` … stickyLeft の列（選択列なし）。`left: 0`
    - `comp-table__cell--sticky-left-after-check` … stickyLeft の列（選択列あり）。`left: var(--comp-table-check-col-w)`
    - stickyLeft は先頭の1列だけに使う（2列以上は対象外。props の説明に書く）。
  - 以下、3クラスをまとめて「固定列」と書く。CSS は3クラスを並べたセレクタで書く。書く順と詳細度（審査 r2 B-13。stylelint no-descending-specificity に当たらないよう、詳細度が上がる順に書く）:
    1. 本文の固定列 `.comp-table--sticky tbody td.<固定列>`（(0,2,2)）: `position: sticky; z-index: calc(var(--z-base) - 5); background: var(--bg-surface);`
    2. 見出し `.comp-table--sticky thead th`（(0,1,2)。上の1とは対象が別）: `position: sticky; top: 0; z-index: var(--z-base); background: var(--bg-subtle);`
    3. 見出しの角 `.comp-table--sticky thead th.<固定列>`（(0,2,2)。2 に勝つ）: `z-index: calc(var(--z-base) + 5);`
    4. 行の色を固定列にも当てる（DataTable.css:133-165 の行の色と同じトークン。1 より後に、この順で書く。詳細度は下がらない）:
       - (0,3,2) `.comp-table--sticky tbody .comp-table__row--danger td.<固定列>` → var(--danger-bg)
       - (0,3,2) `.comp-table--sticky tbody .comp-table__row--warning td.<固定列>` → var(--warning-bg)
       - (0,3,2) `.comp-table--sticky tbody .comp-table__row--selected td.<固定列>` → var(--info-bg)
       - (0,4,2) `.comp-table--sticky tbody .comp-table__row:hover td.<固定列>` → var(--bg-hover)
       - (0,4,2) `.comp-table--sticky tbody .comp-table__row--selected:hover td.<固定列>` → var(--info-bg)（hover の後に書くので同じ詳細度で勝つ。選択行は hover でも info-bg のまま＝今の行と同じ DataTable.css:142-145）
  - 重なりの順は 本文の固定列 ＜ 見出し ＜ 見出しの角（GAS H:405, 430-434 と同じ）。
  - 固定列は stickyHeader が true のときだけ効く（クラスは付くが、CSS が `.comp-table--sticky` 配下だけなので stickyHeader なしでは今と同じ見た目）。stylelint が並び順で止めた場合は、上の詳細度を保ったまま並び順だけ直す（値は変えない）。

### 1-3. 表を幅に合わせて縮める `fitToWidth`（審査 r1 B-4・N-4・N-6）
- 定数ファイル frontend/src/constants/tableFit.ts（新規）: `MAX_ZOOM_ADJUST_STEPS = 200`、`ZOOM_ADJUST_DECREMENT = 0.001`、`ZOOM_PRECISION = 1000`（GAS H:1506-1569 と同じ値）。
- 計算は純関数に分ける frontend/src/lib/tableFitZoom.ts（新規）:
  - `initialZoom(frameWidth: number, naturalWidth: number): number` = `Math.floor(Math.min(1, frameWidth / naturalWidth) * ZOOM_PRECISION) / ZOOM_PRECISION`（naturalWidth ≤ 0 なら 1）。
  - `refineZoom(z: number, overflows: (z: number) => boolean): number` = `steps < MAX_ZOOM_ADJUST_STEPS && z > ZOOM_ADJUST_DECREMENT && overflows(z)` の間 `z = Math.round((z - ZOOM_ADJUST_DECREMENT) * ZOOM_PRECISION) / ZOOM_PRECISION`。
- フック frontend/src/hooks/useFitTableZoom.ts（新規）（frame・card・scroll の ref を受ける）。手順:
  1. `window.matchMedia(\`(min-width: ${BREAKPOINTS.TABLET_MIN}px)\`)` が偽、またはカード表示中 → `--comp-table-fit-zoom` を消して終わり。
  2. 測る前に zoom を外す: `card.style.removeProperty('--comp-table-fit-zoom')`（GAS H:1524 と同じ）。
  3. natural = `scroll.scrollWidth + scroll の左右 border`（border を持つのはスクロール箱 `.comp-table`（DataTable.css:16）。`getComputedStyle(scroll)` の borderLeftWidth + borderRightWidth）。frame = `frame.clientWidth`。
  4. `z = initialZoom(frame, natural)`。z ≥ 1 なら何もしない（GAS H:1531）。
  5. z < 1 なら `card.style.setProperty('--comp-table-fit-zoom', String(z))`、続けて `refineZoom(z, (zz) => { setProperty(zz); return scroll.scrollWidth > scroll.clientWidth; })` の結果を設定（GAS H:1533）。
  6. 計算し直すとき: frame の大きさが変わったとき（ResizeObserver。サイドバーの開閉も拾う。ResizeObserver が無い環境では window resize）、matchMedia の change、rows の変化。どれも requestAnimationFrame で1フレームに1回へ間引く。
- CSS: `.comp-table-fit__card { zoom: var(--comp-table-fit-zoom, 1); }`。style 属性は使わず ref の setProperty だけで値を渡す（ADR-144:120 の将来検査に備える）。
- 縮小中の見出し固定の高さ: `.comp-table-fit__card .comp-table--sticky { max-height: calc(var(--comp-table-sticky-max-h) / var(--comp-table-fit-zoom, 1)); }`。zoom の内側の max-height が見た目で z 倍になるかは【未確認】（ブラウザ実装依存）なので、受入で実測する（1-6 の e2e）。

### 1-4. スマホのカード表示 `mobileCards`（審査 r1 B-5）
- `mobileCards?: boolean`。`useIsMobile()`（767px 以下）が真のとき、table を描かず div で描く:
  ```
  div.comp-table-cards (role="list")
    div.comp-table__card (role="listitem", data-testid=rowTestId(row), rowClassName も付ける, onRowClick)
      [selectable のとき] カード先頭に選択の checkbox（DataTable の選択列と同じ部品）
      div.comp-table__card-field × 表示する列
        span.comp-table__card-label  ← 見出しの文字列（列の mobileLabel、無ければ header が文字列ならそれ）
        span.comp-table__card-value  ← renderCell の結果
  div.comp-table__pagination（今と同じ）
  ```
- 列 props: `mobileOrder?: number`（小さい順に並べる。無い列は後ろに元の順で）、`mobileHidden?: boolean`、`mobileLabel?: string`。
- カード表示のときは stickyHeader・stickyLeft・fitToWidth を効かせない（カードは縦に並ぶだけ）。thead が無いので全選択の checkbox（DataTable.tsx:178-190）は出ない。在庫表の選択は今は表示にしか使っていない（InventoryPage.tsx:138,356,678）ので許容する。
- CSS: カードは `--comp-table-*` と既存の間隔・枠トークンだけ（border: 1px solid var(--border)、border-radius: var(--comp-table-radius)、padding: var(--space-3) など）。table の min-width（tokens.css:521 の 480px）はカードに掛からない。

### 1-5. MultiSelect 金型（新設）
- ファイル: frontend/src/components/MultiSelect.tsx（新規）、`MultiSelect.css`（var() のみ）、MultiSelect.stories.tsx（新規）、MultiSelect.test.tsx（新規）（docs/CC_UI_GOVERNANCE.md:13-15 の型）。
- props: `label: string`、`options: { value: string; label: string }[]`、`selected: string[]`、`onChange(next: string[])`、`clearLabel: string`、`allLabel: string`、`countLabel: (n: number) => string`、`testId?: string`。文言は呼び出し側が t() で渡す（金型に文言を書かない）。
- 中身: Popover（components/Popover.tsx）を土台にボタン＋メニュー。メニュー先頭に「選択をクリア」ボタン、その下にチェックの一覧（`max-height: var(--dropdown-max-h)`、overflow:auto）。checkbox のサイズは `var(--size-checkbox)`。
- ボタンの表示: 0件「{label}: {allLabel}」／1件 その選択肢の label／2件以上 countLabel(n)（GAS H:1313-1328）。
- testid: ボタン `${testId}-button`、各選択肢 `${testId}-option-${value}`、クリア `${testId}-clear`。

### 1-6. 便1 の手順と受入
- 手順の追加（審査 r1 B-11）: tokens.css に新トークンを足すので、PR 本文の「デザイントークン変更時」4項目（.github/pull_request_template.md:51-55）に [x] と内容を書く（check-new-tokens.js が見る）。

| 基準 | 検証方法 |
|---|---|
| 既存の DataTable 利用画面が変わらない | 既存の vitest 全通過。新 props 無しの DOM がクラス名で今と同じ（テストで assert） |
| testid・読込中の口 | vitest: rowTestId が tr とカードに付く、paginationTestIds が3か所に付く、paginationDisabled で前へ・次へ両方 disabled |
| stickyHeader・stickyLeft | vitest: frame・--sticky・sticky-left のクラス、ページ送りがスクロール箱の外にある |
| 縮小の計算が GAS と同じ | vitest（純関数）: initialZoom(900, 1200)=0.75、initialZoom(1200, 900)=1、refineZoom が overflows=true の間 0.001 ずつ下がり 200 回で止まる、z ≤ 0.001 で止まる |
| カード表示 | vitest: matchMedia をモックして、mobileOrder 順・mobileHidden 除外・ラベル表示・rowTestId |
| MultiSelect | vitest: 0/1/2件のボタン表示、クリアで []、チェックで追加と除去 |
| 直値・生部品なし | `npm run lint`、check-ui-governance、design-token 検査、check-new-tokens が緑 |
| Storybook | MultiSelect と DataTable の新状態（sticky・fit・cards）の stories を追加。storybook build が CI で緑 |

## 便2 在庫表の載せ替え

### 2-1. 列定義（審査 r1 B-6）
置き場所: frontend/src/features/inventory/inventoryColumns.tsx（新規）（InventoryPage.tsx は今 771 行、上限 800（frontend/scripts/check-page-size.js:19）なので列の中身はこちらへ移す）。`buildInventoryColumns({ t, colVisible, ... }): DataTableColumn<InventoryItem>[]`。各セルの中身は今の InventoryPage.tsx:683-741 の td をそのまま renderCell に移す（表示内容は変えない。状態だけ Badge に変える。選択の checkbox :676-682 は DataTable の selectable に置き換わる）。
- 文字の大きさ（審査 r2 N-r2-2）: 今の表は font-md（:645。:640 の注記「フォントは少し大きめ」）、DataTable は font-sm（DataTable.css:25）。GAS も font-sm（H:400）なので、DataTable の font-sm に揃える（文字が1段小さくなる。KGI の PO 目視で確認してもらう）。
- 未使用になるもの（審査 r2 N-r2-1）: カテゴリ列を消すと categoryLabel・tcgTypeName（:172-177）と visibleColCount（:183-184）が使われなくなるので消す。tcgTypes はタブ（:600-617）で使うので残す。

| 列 key（= API の sort 値 inventory_offers.py:118-130） | 見出し | sortable | align | 隠せる（hidden_columns の id） | stickyLeft | mobileOrder | mobileHidden |
|---|---|---|---|---|---|---|---|
| （選択列: DataTable の selectable） | — | — | — | — | 固定 | カード先頭 | — |
| mark | inventory.col.mark | ○ | left | mark | | | ○ |
| name | inventory.col.title（日本語が上、英語が下 font-sm） | ○ | left | 常に表示 | ○ | 1 | |
| condition | inventory.col.condition（Badge） | ○ | left | condition | | 2 | |
| unit | inventory.col.unit | ○ | left | unit | | | ○ |
| offer_type | inventory.col.offerType（予約は今の badge-negotiating のまま） | ○ | left | offerType | | | ○ |
| quantity | inventory.col.quantity（まとめ件数を含む） | ○ | right | quantity | | 4 | |
| unit_price | inventory.col.unitPrice | ○ | right | unitPrice | | 3 | |
| supplier | inventory.col.supplier（掲載時刻つき） | ○ | left | supplier | | 7 | |
| note | inventory.col.note | × | left | note | | 5 | |
| ship | inventory.col.ship | × | left | ship | | 6 | |
| release_date | inventory.col.releaseDate | ○ | left | 常に表示 | | | ○ |

- 隠す列は今と同じ colVisible（InventoryPage.tsx:183）で columns を絞る。HIDEABLE_COLUMNS（:111-113）から "category" を外す。保存済みの hidden_columns に "category" が残っていても無視するだけ（PATCH では buildFilterPayload :95-108 のとおりそのまま返す）。
- category 列（:651, :684-686）は削除。
- DataTable の props（審査 r2 B-14・B-15・N-r2-5 で確定）:
  - `rowKey={(it) => it.id}`（今の key・testid・選択はすべて it.id。InventoryPage.tsx:26,672,678。見積へ渡す preselectedInventoryIds も id 前提 :125,138-139）
  - `rowTestId={(it) => \`inventory-row-${it.id}\`}`（-merged などセル内の testid は renderCell の中にそのまま残す）
  - `selectable`、`selectedKeys={selectedIds}`、`onSelectChange`（今の selectedIds の更新）
  - `sortKey={sortField}`、`sortDir={sortDir}`、`onSort={(key, dir) => { setSortField(key); setSortDir(dir); setPage(1); }}`（DataTable の handleSort :158-163 は今の onSort :366-373 と同じく「同じ列は反転・別列は asc」）
  - `page={page}`、`hasNextPage={page < totalPages}`（:179）、`onPageChange={setPage}`、`prevPageLabel={t("common.previous")}`、`nextPageLabel={t("common.next")}`（DataTable の既定 ‹ › DataTable.tsx:127-128 を使わない）、`pageInfo={t("inventory.pageOf", { page, total: totalPages, count: total })}`（:761-763 と同じ）
  - `paginationTestIds={{ prev: "inventory-prev", next: "inventory-next", label: "inventory-pagination-label" }}`、`paginationDisabled={loading}`
  - `stickyHeader`、`fitToWidth`、`mobileCards`、`emptyState={t("inventory.noResults")}`
  - `data-testid="inventory-table"` と表の `aria-busy` は付けない（【事実】参照は frontend/src・frontend/tests-e2e に 0 件＝審査 r2）。DataTable に testId・busy の口は足さない。
- 状態バッジ: frontend/src/features/inventory/conditionBadge.ts（新規） に `conditionBadgeVariant(condition: string): BadgeVariant`（trim・小文字化して完全一致: sealed→success、damaged→danger、case→info、他→neutral。GAS H:1591-1605）。閲覧ページも同じ関数を使う。

### 2-2. 並び替えプルダウン
- SelectControl（Select.tsx）、placeholder は t("inventory.sortMenu.placeholder")（value ""）。選択肢: `unit_price:asc`「価格が安い順」、`quantity:desc`「在庫が多い順」、`offered_at:desc`「投稿が新しい」。選ぶと sortField/sortDir を設定し page=1。表示値は `${sortField}:${sortDir}` が3つのどれかならそれ、違えば ""（placeholder）。
- 置き場所（審査 r2 N-r2-3。GAS の並び 検索 → 24時間 → 並び替え → 絞り込み H:818-847 に合わせる）: ツールバー（:505-544）の 24時間ボタン（:523-534）の後、詳細フィルタボタン（:535-544）の前。
- resetAll（:376-383）を `setSortField("release_date"); setSortDir("desc");` に直す。

### 2-3. 文言（ADR-027。ja.json / en.json 同一キー）
- 追加: `inventory.sortMenu.placeholder`「並び替え」/"Sort"、`inventory.sortMenu.priceAsc`「価格が安い順」/"Price: low to high"、`inventory.sortMenu.stockDesc`「在庫が多い順」/"Quantity: high to low"、`inventory.sortMenu.postedDesc`「投稿が新しい」/"Newest posts"。

### 2-4. 受入
| 基準 | 検証方法 |
|---|---|
| KGI 4・5・6・7・8・9・10 | vitest（列の順・category なし・Badge の variant・プルダウン3択と既定の placeholder・resetAll 後 release_date desc）。本番で PO 目視 |
| 既存 testid のテスト | CommerceNavigationButtonMigration.test（:58-71、読込中の前へ disabled を含む）、InventoryPage.settings / noechopatch / singlefetch.test が通る |
| 横にはみ出さない・縮む・見出しが画面内（審査 r2 B-16） | 新しい e2e frontend/tests-e2e/inventory-table-layout.spec.ts（新規）（【訂正 2026-10-15】e2e.yml:207 の Playwright E2E は `if: false` で 2026-06-01 から CI 停止中。この e2e は手元で実行し、数値を PR に残す。便2 #4327 で 3/3 成功）。既存の fixtures（installAuthBypass・mockApi・commonMocks）を使い、mock を3つ置く: GET /inventory（items 5件以上。うち1件は長い商品名・長い備考で表の幅が 900px を超えるもの。total・suppliers・conditions・units も入れる）、GET /me/inventory-filters（既定値）、GET /products/tcg-types。検査: (1) 375×800: カード（`inventory-row-<id>`）が見える、thead が無い、`document.documentElement.scrollWidth <= innerWidth`。(2) 900×800: まず `.comp-table-fit__card` の `--comp-table-fit-zoom` が 1 未満であることを assert（縮小が起きていない緑を防ぐ）、次にスクロール箱の getBoundingClientRect().height ≤ (innerHeight − 18rem の px) + 1、doc の横スクロールなし。(3) 1440×900: `--comp-table-fit-zoom` が未設定。既存の horizontal-overflow.spec.ts:76-80 は行の mock が無く空の表で検査している【事実: routeMocks :31-45 に /inventory 無し】ので、この新しい e2e で置き換えて確かめる（既存の検査は消さない） |
| 生 table・インライン style が減る | `grep -c "<table" frontend/src/pages/inventory/InventoryPage.tsx` = 0、check-page-size（800行以下）、check-ui-governance 緑 |

## 便3 検索と提供者

### 3-1. 検索（backend/app/routers/inventory_offers.py:184-189）
- 変更前: 6列の ILIKE `%q%`。
- 変更後:
  - 正規化関数 `normalize_search_text(s: str) -> str`（同ファイル内）: `unicodedata.normalize("NFKC", s).lower()` → U+3041〜U+3096 を +0x60（カタカナ）。
  - 語: `normalize_search_text(q).split()`、空語を捨て、先頭 `_SEARCH_MAX_TERMS = 10` 語まで。語が0個（空白だけ）なら条件を足さない。
  - SQL: 各語 i について `strpos(translate(lower(normalize(concat_ws(E'\n', d.japanese_title, d.english_title, d.mark, d.search_keywords), NFKC)), :kana_from, :kana_to), :qt{i}) > 0` を AND で足す。:kana_from / :kana_to は U+3041〜U+3096 と U+30A1〜U+30F6 から作る86文字ずつの文字列（モジュール定数）。【事実】ローカル PG16.15 で「ぽけもん」→「ポケモン」・「ＡＢＣ」→「abc」・concat_ws の NULL 飛ばしを確認（/tmp/CC報告ファイル/app_inventory_recon_20261015/review_r1_sql.txt）。本番 DB の datctype は en_US.utf8【事実: pg_database を読み取り確認】なので lower() は非 ASCII も小文字化する。
  - バインドの型: asyncpg で text と推論されるかは【未確認】→ 実装では `CAST(:kana_from AS text)` のように明示して型推論に頼らない。
  - provider・product_id・category は対象から外す（GAS と同じ）。q の description（:288）を「日本語名/英語名/型番/検索ワード（NFKC・かな同一視・空白区切りAND）」に直す。
- 共通テストベクタ: frontend/src/features/inventory/searchNormalize.vectors.json（新規）（入力→期待値。ひらがな・全角英数・半角カナ・大文字・空白混じり）。backend のテストは repo ルートからの相対パスで読み Python 関数と照合。frontend の features/inventory/searchNormalize.ts（新規）（閲覧ページで使う normalizeForSearch。GAS H:987-993 と同じ）も同じベクタで照合。【事実】backend の pytest は paths フィルタ（test.yml:17-26）に frontend/** が無いため、ベクタだけを変える PR では Python 側が走らない。ベクタを変えるときは backend のテストファイルも同じ PR で触る（テストの冒頭にその旨のコメント）。
- frontend:
  - 検索ボタン（:517、testid inventory-search-btn）を削除。250ms 待つ検索は残す。Enter（:515）は待ちを飛ばしてすぐ検索（setDebouncedQ(searchQ)）。【事実】inventory-search-btn と runSearch を使うテストは無い（審査 r1 N-5、grep 0 件）。
  - プレースホルダ: 新キー `inventory.view.searchNameCode`「商品名・型番で検索」/"Search by name or code" を作って在庫表だけで使う。既存の inventory.view.searchPlaceholder は見積・請求（QuoteCreatePage.tsx:262・InvoiceCreatePage.tsx:413）が使うので変えない。

### 3-2. 提供者（選んだ人だけ）
- backend: `list_inventory_view` に `supplier_ids: str | None = Query(default=None, max_length=2000, description="表示する仕入元IDのCSV（選んだ仕入元だけ）")`。`_build_view_filters` には既定値 None のキーワード引数 `supplier_ids: str | None = None` で足す（test_inventory_distribution_rows.py:47-50 が決まった引数だけで呼ぶため）。整数だけ採って `d.supplier_id IN (:sid0, …)`（:190-195 と同じ作り）。整数が1つも無いときは絞らない。hide_supplier_ids の引数と処理は残す。
- frontend:
  - 状態 `selectedSupplierIds: string[]`（保存しない。開くたびに空＝全員）。選択があれば常に `supplier_ids` を送る（フィルタ有効スイッチと無関係）。選択を変えたら page=1。
  - 置き場所（審査 r2 B-17。PO 決定 4「レイアウトも同じ」= GAS は PC ではツールバーに並べ（H:308,311,874-887）、スマホでは絞り込みの中（H:596-681））:
    - PC（useIsMobile() が偽）: ツールバーの並び替えの後、詳細フィルタボタンの前に MultiSelect（testId `inventory-supplier-filter`）。
    - スマホ: 詳細フィルタパネル（InventoryFilterPanel.tsx。アプリにはドロワーが無く、GAS のドロワーに当たるのはこのパネル）の先頭に同じ MultiSelect。InventoryFilterPanel に props（supplierOptions・selectedSupplierIds・onSupplierChange・showSupplierSelect）で渡す。
    - 候補は API の suppliers（facet は絞り込み前の行から作るので選んでも候補は消えない。inventory_offers.py:370-378）。値は `String(s.id)`、表示は `s.name ?? \`#${s.id}\``（今の InventoryFilterPanel.tsx:170 と同じ）。
  - 仕入元を除外する欄（InventoryFilterPanel.tsx:152-173）を消す。hide_supplier_ids は送らない（InventoryPage.tsx:219-221 を削除）。保存済み hidden_supplier_ids は GET で受け取り、PATCH でそのまま返す（buildFilterPayload :95-108 は変えない）→ DB の値は消えない。
  - 文言: `inventory.supplierFilter.label`「提供者」/"Supplier"、`.clear`「選択をクリア」/"Clear selection"、`.all`「すべて」/"All"、`.count`「{{count}}件」/"{{count}} selected"。使われなくなる `inventory.filterPanel.suppliers` は ja/en から同時に消す。
- テストの更新: InventoryPage.singlefetch.test:57-63（hide_supplier_ids=1 の期待 → 提供者を選んだときに supplier_ids が送られる期待へ）、noechopatch.test（hidden_supplier_ids が PATCH で保たれる）。backend: test_me_inventory_filters は変更なしで通る見込み【未確認】→ 通らなければ止めて報告。q と supplier_ids の新テストは test_inventory_distribution_rows_pg の作りに合わせる。
- API 契約（審査 r1 B-8）: `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を実行して差分をコミット（api-contract-check.yml:50-53 が main 向け全 PR で検査）。

### 3-3. 受入
| 基準 | 検証方法 |
|---|---|
| KGI 1・2 | backend テスト（PG）: 「ぽけもん」で「ポケモン」行、「ＡＢＣ」で ABC 行、2語 AND、検索ワードだけに含む語で当たる、提供者名だけでは当たらない、空白だけの q は全件。本番で PO 目視 |
| KGI 3 | backend テスト: supplier_ids=1,2 で 1 と 2 の行だけ、"x,y" は絞らない。frontend テスト: MultiSelect で選ぶと supplier_ids が送られ、クリアで送られない |
| Python と JS の正規化が一致 | 共通ベクタを両方のテストで読む |
| 保存値を壊さない | frontend テスト: GET の hidden_supplier_ids=[1] が PATCH の本文にも [1] |
| 速さ | 便3 の前に本番で今の q 検索（例「ポケモン」）の応答時間を3回測って基準値にし、反映後に同じ語で3回測る。1秒を超えたら索引の便を別に起こす（正規化の分だけ重くなるかは【未確認】。今の q も ILIKE `%q%` の全走査【事実: :184-189】） |
| API 契約 | api-contract-check が緑 |

## 代替案と選択理由

- 検索をクライアント側でやる（GAS 方式）: 在庫表はページ送り（50件）で全件を持たない → サーバー側で同じ正規化をする。
- 正規化の生成列や索引を足す: migration が要り便が重い → まず全走査で測り、必要なら別便。
- 提供者の選択を保存する: PO 決定 4 は「GAS と同じ」＝保存なし。
- fitToWidth を transform: scale で作る: 外枠の幅が縮まず余白が残る → GAS と同じ zoom。
- カード表示を table の display 変更で作る: min-width 480px が残り 375px ではみ出す → div で描く。

## リスクと対処

| リスク | 対処 |
|---|---|
| 金型の変更で他画面が崩れる | 新 props はすべて既定 off で今の DOM（1-0）。既存テストと Storybook build |
| zoom と sticky の組み合わせのずれ | 1-3 の max-height の補正と、2-4 の e2e（下端が画面内）で実測。だめなら止めて設計を直す |
| hidden_supplier_ids が DB に残る | 画面で使わないだけ。戻すときに使える |
| 提供者名で検索していた人が困る | 提供者は MultiSelect で選べる。PO 決定 3 は GAS と同じ |
| 全選択が別ページの選択を消す（DataTable.tsx:138-145） | 在庫表の選択は表示だけに使っている（:138,356,678）ので影響は小さい。直さない |

## 戻し方

便ごとに revert PR（merge commit を `git revert -m 1`）。migration なしなので DB の戻しは不要。

## 外部・過去事例

- GAS 在庫一覧（本番で稼働中の実物）が直接の手本。検索・並び替え・縮小・カードの動きはその実装（H の行番号）を写す。外部の事例は使わない（理由: 手本が社内の稼働中の実物で、挙動を行単位で写せるため）。
- 商品マスタの見出し固定（components.css:136-155、ADR-093）を金型へ一般化する。

## 維持の仕組み

- 守り手: .github/workflows/frontend-check.yml（check:all・tsc・新トークン検査・Storybook ビルド。e2e は .github/workflows/e2e.yml）
- 金型にしたので、閲覧ページ（ADR-1017）も同じ部品を使う → 片方だけ直る事故を防ぐ。
- 正規化は共通テストベクタで Python と JS を照合（ベクタを変えるときは両方のテストを同じ PR で触る）。
- アプリ在庫表を変えるときは GAS 在庫一覧にも揃える方針（メモ app_inventory_gas_parity）。

## 審査（Architect）

- r1（2026-10-15）: REVISE。B-1〜B-11 を本 r2 で反映（B-1→1-1、B-2・B-3→1-2、B-4→1-3、B-5→1-4、B-6→2-1、B-7→2-3・3-1・3-2、B-8→3-2、B-9→3-1・3-2、B-10→冒頭、B-11→1-6）。N-1→リスク表、N-2→3-1、N-3→3-1、N-4・N-6→1-3、N-5→3-1。
- r2（2026-10-15）: REVISE。B-1〜B-11 解消（B-3 の残りは B-13）。新規 B-12〜B-17 を r3 で反映（B-12→1-0b、B-13→1-2、B-14・B-15→2-1、B-16→2-4、B-17→3-2）。N-r2-1・2→2-1、N-r2-3→2-2、N-r2-4→冒頭、N-r2-5→2-1、N-r2-6（カードにも行の色が付く）は意図どおり。全文 /tmp/CC報告ファイル/app_inventory_recon_20261015/review_design_r2.txt
- r3（2026-10-15）: **APPROVE**。B-12〜B-17・N-r2 全件解消。全文 /tmp/CC報告ファイル/app_inventory_recon_20261015/review_design_r3.txt。実装時に直す点（実装カードに入れる）:
  - N-r3-1: 行の型は実物では `InventoryRow`（InventoryPage.tsx 内・未 export）。列定義ファイルへ移すときに export する。
  - N-r3-3: 375px の横はみ出しは document では測れない（`.mobile-content` が overflow-y:auto で横も auto。mobile-shell.css:22-25）→ `.mobile-content` の scrollWidth ≤ clientWidth と、各カードの右端 ≤ innerWidth で検査する。
  - N-r3-4: 900px の高さ検査は行が少ないと常に合格 → mock の items を 20 件以上にする。
  - N-r3-5: mock の長い文字列は日本語か空白入りにする。カードの値に `overflow-wrap: anywhere`。
  - N-r3-6: GAS は表全体が nowrap（H:401）、DataTable は折り返す → 便2 では変えず、PC の見た目は KGI 5 の PO 目視で確認。
  - N-r3-7: useFitTableZoom は fitToWidth が無いとき・ref が null のときは何もしない。
  - N-r3-8: 便3 で InventoryFilterPanel の旧 props（toggleHiddenSupplier など）を消す。
  - N-r3-2・9: 行番号の1行ずれ・固定列の色の優先順位（在庫表では影響なし）。
