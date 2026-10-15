# Opus 審査記録 — inventory-table-unify

同一 AI（Claude Opus）の Architect 役による自己審査。独立した第二者レビューではない。

## r1

```text
判定: REVISE（方向は妥当。便1〜3を実装役へ渡すには必須修正 B-1〜B-11 が要る）

対象: /Users/tanizawashingo/worktrees/salesanchor/release-inventory-table-unify/docs/handoff/inventory-table-unify/{design.md,recon.md}
照合: worktree HEAD e1cdbc468。`git diff --stat e1cdbc468 4866be5bf -- frontend/src backend/app` の出力は空【事実】
GAS: /tmp/CC報告ファイル/gas_pull_prod/index.html（1622行）
SQL 実測の生出力: /tmp/CC報告ファイル/app_inventory_recon_20261015/review_r1_sql.txt

== 1. file:line の突合 ==
一致【事実】: InventoryPage.tsx :95-108 / :111-113 / :134-136 / :204 load / :220 hide_supplier_ids / :245 suppliers / :366 onSort / :376 resetAll / :425 sortTh / :509 search / :517 search-btn / :596 ui-allow / :642-745 table / :651,:684 category / :749-767 pagination。
InventoryFilterPanel.tsx :152-173 / DataTable.tsx :29-46,:51-93,:158-163,:174,:180,:268,:303-327 / Popover.tsx :140 / Badge.tsx :11,:16 / components.css :136-155 / tokens.css :115,:121-122,:226,:348,:434,:507-521 / inventory_offers.py :118-130,:184-189,:190-195,:246-248,:288,:305-312,:370 / tcg_distribution_svc.py :302-306。
d.search_keywords と d.supplier_id: 参照できる【事実】。WHERE の d は rows_x（inventory_offers.py:258 `rows_f AS (SELECT * FROM rows_x d {where})`）。rows_x は final_main の x.*。final は _distribution_final_select（tcg_distribution_svc.py:258-266）で search_keywords, supplier_id を出し、plain（:269-271）と merged（:369-371）で同じ関数を使う。

== 必須修正 ==
B-1 DataTable に testid と読込中の無効化の口が無い（design.md:89 が「渡せない場合は」と条件付きのまま）
  - 行の testid: DataTable の tr（DataTable.tsx:246-265）に data-testid を付ける口が無い。inventory-row-<id> を使うテスト: InventoryPage.settings.test.tsx:41,51,74,84 / noechopatch.test.tsx:49,69,81 / singlefetch.test.tsx:58,75,100-104。
  - ページ送り: Button（DataTable.tsx:305-325）と span（:314）に testid の口が無い。
  - 読込中の無効化: CommerceNavigationButtonMigration.test.tsx:63 は次ページ読込中に prev も disabled を期待。DataTable は prev が `disabled={page <= 1}`（:309）のみで、現行の `|| loading`（InventoryPage.tsx:758,765）を表せない。
  → 便1で確定事項として rowTestId(row)=>string、paginationTestIds{prev,next,label}、paginationDisabled(boolean) 相当を追加すると書く（名前は設計で固定）。
B-2 ページ送りの置き場所が未定義
  - ページ送りは .comp-table ラッパーの内側（DataTable.tsx:174 の div 内 :303-327）。stickyHeader で max-height+overflow:auto をこの箱に掛けると、ページ送りがスクロール箱の中（表の最下部までスクロールしないと出ない）に入り、fitToWidth では縮小対象にも入る。
  → stickyHeader/fitToWidth 時の DOM（ページ送りをスクロール箱・zoom 箱の外へ出すか否か）を設計で決め、既存利用（新 props 未指定）の DOM は不変と明記。
B-3 sticky の CSS が未確定（design.md:37 の「<既存の見出し背景トークン>」、:39 の z-index）
  - 見出しの背景は今は tr にある（DataTable.css `.comp-table__head-row { background: var(--bg-subtle) }`）。sticky th 自身に var(--bg-subtle) が要る。
  - 本文の固定列セルは var(--bg-surface) に加え、選択行（.comp-table__row--selected = var(--info-bg)）と hover（var(--bg-hover)）の色を固定列セルにも当てる規則が要る（無いと固定列だけ色が抜ける）。
  - z-index: 設計は本文固定列も見出しも var(--z-base) で同値 → 後に描かれる本文固定列が見出しの上に重なる。GAS は td 固定列 calc(z-base - 5) / th z-base / th 固定列 calc(z-base + 5)（H:430-434）。本文固定列 < 見出し < 見出し角 の順を設計に書く。
B-4 fitToWidth の計算手順に穴
  - 測る前に zoom を外す手順が無い。GAS は毎回 `card.style.zoom = ''`（H:1524）してから測り、z>=1 なら何もしない（H:1531）。下げるループには z > ZOOM_ADJUST_DECREMENT の下限もある（H:1533）。設計 1-2 の 1〜4 に3点とも無い。
  - border の出所: 設計は「card の左右 border」だが、本設計で border を持つのはスクロール箱 .comp-table（DataTable.css `.comp-table { border: 1px solid var(--border) }`）。card に border が無ければ natural が 2px 小さく、枠から最大 2px はみ出す【推測】。どの要素の border を足すか固定する。
  - stickyHeader 併用時: max-height（calc(100vh - 18rem)）はスクロール箱＝zoom の内側に掛かる。zoom 後の見た目の高さが z 倍に縮むかは【未確認】（ブラウザの zoom 実装依存）。受入表に「z<1 のとき表の下端が画面下端付近にあること」の確認方法（Storybook か PO 目視の手順）を足すか、max-height を zoom で割る式を設計で決める。
B-5 mobileCards の DOM と CSS が未定義（design.md:53-58）
  - table のまま display を変えるのか div で描くのかが無い。table のままなら `.comp-table__table { min-width: var(--comp-table-min-width) }`（480px、tokens.css:521）が残り、375px で横にはみ出す。tests-e2e/horizontal-overflow.spec.ts:76-80 が /inventory を 375px で検査している → 受入表に入れる。
  - カード表示のとき stickyHeader の max-height と stickyLeft と fitToWidth をどう扱うか（外す／残す）を書く。
  - thead を出さないので全選択の checkbox（DataTable.tsx:178-190）が消える。それで良いかを明記。
B-6 便2 の列定義が実装役に渡せる粒度でない
  - DataTable は sortKey===col.key で並べ替えを判定し onSort(key, dir) を返す（DataTable.tsx:158-163,198,208）。列 key を API の sort 値（inventory_offers.py:118-130。title→name、offerType→offer_type、unitPrice→unit_price、releaseDate→release_date など）にする対応表が要る。
  - 並べ替えできない列（備考・発送。今は sortTh なし InventoryPage.tsx:660-661）、右寄せ列（数量・単価 InventoryPage.tsx:717,728）の扱い。DataTable の列に align の口が無い（DataTable.tsx:29-46）→ 便1で足すか、右寄せをやめるかを決める。
  - 列の表示切替（HIDEABLE_COLUMNS と colVisible、InventoryPage.tsx:111-113,183）を columns の絞り込みで残すと書く。
  - 置き場所: InventoryPage.tsx は今 771行、上限 800（frontend/scripts/check-page-size.js:19）。列定義は features/inventory 側に置くと書く。
  → 「列 key / 見出し i18n キー / sortable / 右寄せ / 隠せる列のキー / stickyLeft / mobileOrder / mobileHidden」の表を1つ置く。
B-7 i18n キーの不足と誤り（ADR-027）
  - design.md:108 の t("inventory.searchPlaceholder") は実在キーと違う。実物は inventory.view.searchPlaceholder（InventoryPage.tsx:508、ja/en とも inventory.view 配下）。値を変えるのか新キーにするのかを決める。
  - MultiSelect に渡す文言（提供者 / 選択をクリア / すべて / N件）の ja/en キーが設計に無い（design.md:90 は並び替えの4キーだけ）。
B-8 API 契約の更新手順が無い
  - api-contract-check.yml は main 向けの全 PR で動き、`git diff --exit-code -- frontend/api-contract/` で止める（:50-53）。supplier_ids の追加と q の説明文変更（design.md:106,111）で openapi.json が変わる。便3 の手順に `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` とそのコミットを入れる。
B-9 _build_view_filters の引数
  - 既存テスト test_inventory_distribution_rows.py:47-50 は決まったキーワードだけで呼び、([], {}) を期待する。新しい supplier_ids は既定値 None の keyword で足すと書く（既定なしだと TypeError）。
  - 正規化後に語が0個（空白だけ）なら条件を足さない、supplier_ids に整数が1つも無いときの扱い（絞らない／0件）を書く。
B-10 金型新設の PO 許可の記録（ADR-144）
  - ADR-144:61-64 と docs/CC_UI_GOVERNANCE.md:13-15 は「金型が無ければ止めて PO 報告 → PO 許可後に新設」。design.md:3 は在庫表の作り直しの委任だけを引いており、MultiSelect の新設と DataTable の機能追加の許可の出所が書かれていない。許可の原文の置き場所を design.md に書く（無ければ PO に確認）。
B-11 新しいトークンの PR 本文チェック
  - tokens.css へ --comp-table-sticky-max-h を足すと check-new-tokens.js（frontend-check.yml:47）が PR 本文の「デザイントークン変更時」4項目（.github/pull_request_template.md:51-55）の [x] を求める。便1の手順に入れる。

== 確認事項への回答（必須修正以外）==
3. style 属性のカスタムプロパティ: 今の CI は止めない【事実】。eslint.config.js:39-113 の no-restricted-syntax は hex / rgba / opacity・zIndex の数値 / width 等の数値リテラルだけ。scripts/check-ui-governance.js は生 select・生 input(text/search/省略)・自作タブだけ。scripts/check-design-token-ratchet.sh は hex の増加だけ。check-css-hardcoded-values.js は tokens.css を除外（:23）。
   ただし ADR-144:120（Proposed）が「共通UIへの自由な style」を将来検出すると書いているので、ref から setProperty で設定する方を最初から選ぶのが安全【推測】。
   ADR-067: 新 CSS はすべて var() で問題なし。ADR-1014: 配信の WHERE を router に書かない規則はテスト test_inventory_distribution_rows.py:101-108 が配信の語（pid_resolved 等）だけを禁止する形。利用者の絞り込み（q・supplier_ids）は今も router にあり、矛盾しない【事実】。
4. DataTable のページ送りへの testid: 今の実物では渡せない【事実】（B-1）。
6. 便3 の SQL: ローカル PostgreSQL 16.15（UTF8, datctype en_US.utf8）で SELECT のみ実測【事実】。
   - U+3041〜U+3096 と U+30A1〜U+30F6 はどちらも 86 文字。
   - translate(lower(normalize(concat_ws(E'\n', …), NFKC)), hira, kata): 「ぽけもん」→「ポケモン」で strpos>0、「ＡＢＣ」→「abc」で一致、concat_ws は NULL を飛ばす、半角ｶｰﾄﾞ→カード。
   - normalize(x, NFKC) の NFKC は引用符なしのキーワードで正しい。strpos は % や _ をワイルドカードとして扱わないので LIKE のエスケープは不要。
   - 本番の datctype は【未確認】。C ロケールだと lower() は ASCII 以外を小文字化しない（Python の str.lower() とずれる）。NFKC で全角英字は ASCII になるので KGI 1・2 には影響しない【推測】。
   - :hira / :kata / :qt{i} は translate と strpos の text 引数なので型推論で text になる【推測】（asyncpg の実測はしていない）。

== 止めずに直してよい指摘 ==
N-1 DataTable の全選択は集合を置き換える（DataTable.tsx:138-145）。別ページで選んだものが消える。今の selectedIds は表示にしか使われていない（InventoryPage.tsx:138,356,678）ので影響は小さい。
N-2 共通テストベクタは frontend 配下。backend の pytest は paths フィルタ（test.yml:17-26）に frontend/** が無いので、ベクタだけ変えた PR では Python 側が走らない。design.md:151「CI で毎回」は言い過ぎ。
N-3 検索ボタンを消したあと Enter キー（InventoryPage.tsx:515 の runSearch）をどうするかが無い。
N-4 枠の幅は window の resize 以外（サイドバー開閉）でも変わる。ResizeObserver で frame を見るのが確実【推測】。
N-5 recon §4 の AllLegacyButtonDynamicMigration.test は hidden_supplier_ids を初期値に持つだけ（:16）で影響なし。inventory-search-btn と runSearch を使うテストは無い（grep で 0 件）。
N-6 useFitTableZoom の単体テストは jsdom にレイアウトが無いので、計算を「測った値を受ける純関数」に分けると受入表 :73 が書きやすい。

PO 承認: 要（B-10 の金型新設の許可）
Generator へ渡せるか: false（B-1〜B-11 を直して再提出）
```

## r2

```text
判定: REVISE（r1 の B-1〜B-11 は全件解消。r2 で書き足した部分に、実装役へそのまま渡すと止まる・壊れる箇所が6件ある＝B-12〜B-17）

対象: /Users/tanizawashingo/worktrees/salesanchor/release-inventory-table-unify/docs/handoff/inventory-table-unify/{design.md(r2, 235行), recon.md(80行)}
照合: worktree HEAD e1cdbc468。origin/main = 4866be5bf【事実: git rev-parse】。`git diff --stat 4866be5bf HEAD -- frontend backend` の出力は空【事実】
GAS: /tmp/CC報告ファイル/gas_pull_prod/index.html（H）

== 1. r1 指摘の解消判定 ==
B-1  解消。rowTestId / paginationTestIds / paginationDisabled を design.md:46-48 で確定。prev は `page <= 1 || paginationDisabled` で CommerceNavigationButtonMigration.test.tsx:62 の「読込中は前へも disabled」を満たす。
     ※ design.md:144 の testId/busy の条件付き記述が残っている → B-15 で確定させる。
B-2  解消。design.md:52-60 で frame / fit card / スクロール箱 / ページ送り（箱の外）の DOM を固定。新 props 無しは今の DOM（:43, :60）。
B-3  一部未解消 → B-13。背景トークン・z-index の順・行の色は書かれたが、セレクタの詳細度で角の z-index が効かない。
B-4  解消。zoom を外す（:78）、z>=1 で終了（:80）、下限 z>ZOOM_ADJUST_DECREMENT と200回（:75）、border の出所＝.comp-table（DataTable.css:16）（:79）。max-height の補正式（:84）。受入の e2e が弱い点は B-16。
B-5  解消（設計として）。div で描く（:87-96）、min-width がカードに掛からない（:99）、カード時は sticky/fit を外す・全選択なし（:98）。ただし useIsMobile を jsdom で呼ぶと落ちる → B-12。
B-6  ほぼ解消。列 key＝API sort 値の表（:127-140）、align（:49）、colVisible で絞る（:142）、置き場所 features/inventory（:125）。rowKey の記述が実物と違う → B-14。
B-7  解消。新キー inventory.view.searchNameCode（:177）、MultiSelect 文言キー（:185）、並び替え4キー（:153）。ja/en とも未存在を確認【事実: sortMenu・supplierFilter・searchNameCode いずれも無し】。inventory.filterPanel.suppliers の利用は InventoryFilterPanel.tsx:155 の1か所だけ【事実】→ 消してよい。
B-8  解消。backend/tools/export_openapi.py は実在【事実】。コマンドは .github/workflows/api-contract-check.yml:31-34 と同一。型 frontend/src/api/generated/ は .gitignore:128 で追跡外【事実】なので openapi.json だけのコミットで足りる。
B-9  解消。既定 None のキーワード引数（:180）。test_inventory_distribution_rows.py:47-50 は dict.fromkeys の14キーで呼ぶので壊れない【事実】。語0個・整数0個の扱いも記載（:170, :180）。
B-10 解消（原文の引用あり :8-9）。ただし引用元の release/gas-viewer-fresh-fast の design.md:393 は今も「【未確認・PO に確認中（Q14）】」のまま【事実: git show で確認】→ N-r2-4。
B-11 解消（:109）。

== 2. r2 の新しい内容の突合 ==
(a) DataTable に testId / aria-busy の口が要るか → 要らない【事実】。
    `inventory-table` と表の aria-busy を参照するものは frontend/src・frontend/tests-e2e に 0 件（grep。ヒットは InventoryPage.tsx 自身と他部品の aria-busy だけ）。inventory-empty・inventory-row-*-select・inventory-sort-*・inventory-search-btn も参照 0 件。参照があるのは inventory-row-<id>（settings/noechopatch/singlefetch）、inventory-row-<id>-merged（settings.test:43）、inventory-prev/next（CommerceNavigation.test:58-71）だけ → 1-1 の口で足りる。
(b) 列定義表のセルが今の td から移せるか → 移せる。ただし次の差がある。
    - 見出し: DataTable の header は string（DataTable.tsx:33）。今の見出しは t(`inventory.col.${colKey}`)（InventoryPage.tsx:445）で、表の i18n キー（mark/title/condition/unit/offerType/quantity/unitPrice/supplier/note/ship/releaseDate）は ja/en に全部ある【事実】。
    - sort key: 表の key は _SORT_COLUMNS（inventory_offers.py:117-129）と一致【事実】。DataTable の onSort は (key, dir)（DataTable.tsx:61,162）で、今の onSort(field) と形が違う → 呼び出し側で setSortField/setSortDir/setPage(1) にする（N-r2-5）。
    - 中身: 商品名 :688-694、区分 :697-716、数量＋merged の testid :717-726、単価 :727-729、仕入元 :730-737、備考 :738、発送 :739、発売日 :740。design.md:125 の「:676-742」は選択の checkbox の td（:673-681）を含む → N-r2-1。
    - rowKey: design.md:144 の `it.row_key` は存在しない（InventoryRow は id: string、InventoryPage.tsx:26）→ B-14。
(c) e2e が今の基盤で書けるか → 書ける【事実】。installAuthBypass（tests-e2e/utils/auth.ts）＋ mockApi（tests-e2e/utils/api-mock.ts、/api/v1 のパスで照合・未定義は 404）＋ commonMocks（ALL_PERMISSIONS）。chromium project で tests-e2e 配下を全部実行（playwright.config.ts:24,55-60、e2e.yml の npm run test:e2e）。ただし今の horizontal-overflow の /inventory は在庫 API を mock していない → B-16。
(d) tools.export_openapi → 実在（backend/tools/export_openapi.py）【事実】。
(e) CSS 検査: check-css-hardcoded-values.js の z-index 規則は `z-index:\s*\d+` だけ（:43）なので calc(var(--z-base) - 5) は通る。check-css-var-fallbacks.js は hex の fallback だけ（:25）なので var(--comp-table-fit-zoom, 1) は通る【事実】。stylelint は no-descending-specificity が有効（frontend/.stylelintrc.json、check:all に check:stylelint）→ B-13。
(f) 便3 backend: _build_view_filters（inventory_offers.py:171-195）の作りに沿って足せる。ベクタを repo 相対で読むのは、pytest が checkout 済みのランナー上で動く（test.yml:148,164）ので可【事実】。

== 必須修正（r2）==
B-12 matchMedia を無条件に呼ぶと既存テストが落ちる（1-3・1-4）
  - jsdom は window.matchMedia を実装していない。frontend/src/test-setup.ts（19行）にモックが無い【事実】。リポジトリ内の前例も個別にモックしている（InboxMessageThread.discordSendError.test.tsx:17-20 の注記「jsdom は window.matchMedia を実装していない」）。
  - useIsMobile は useState の初期化で window.matchMedia を呼ぶ（frontend/src/hooks/useIsMobile.ts）。DataTable の中で無条件に使うと、DataTable を使う 56 ファイル（stories 除く）とそのテスト、DataTable.test.tsx、InventoryPage の各テスト（CommerceNavigation.test は matchMedia を用意していない :25-41）が TypeError で落ちる。design.md:43 の「既存の DataTable テストがそのまま通る」と矛盾。
  → 設計で固定: mobileCards / fitToWidth が false のときは matchMedia を呼ばない（例: `useMediaQuery(query, enabled)` を新設し、enabled=false または typeof window.matchMedia !== "function" なら false を返す）。useFitTableZoom の手順1（:77）も同じ guard。在庫表のテストは guard により表モードで動く、と明記。
B-13 見出しの角の z-index が効かない・stylelint で止まる（1-2 :64-69）
  - `.comp-table--sticky thead th` は詳細度 (0,1,2)、`thead .comp-table__cell--sticky-left` は (0,1,1)。前者が勝つので角も z-index: var(--z-base) のまま＝他の見出しセルと同値。横スクロール時、後に描かれる見出しセルが角（商品名の見出し）の上に重なる。GAS は thead 全体に z-base（H:405）＋ th.col-title に z-base+5（H:433）。
    → 角のセレクタを `.comp-table--sticky thead th.comp-table__cell--sticky-left`（(0,2,2)）等、詳細度が上回る形で書く。
  - `.comp-table__row:hover .comp-table__cell--sticky-left`（(0,3,0)）の後に `.comp-table__row--selected .comp-table__cell--sticky-left`（(0,2,0)）を書く順（:68 の並び）は no-descending-specificity に当たる【推測: 同じ末尾の複合セレクタで詳細度が下がるため】。並び順と、選択行に hover したときの固定列の色（今の行は info-bg のまま DataTable.css:142-145）を設計で決める。
  - selectable 時に選択列を left:0 で固定するクラス名（th/td 両方）が無い（:69）。名前を固定する。
B-14 便2 の DataTable への渡し方が実物と違う・足りない（2-1 :144）
  - rowKey: `it.row_key` は無い。今は key・testid・選択すべて it.id（InventoryPage.tsx:672,678）。見積往復の preselectedInventoryIds（:125,138-139）も id 前提 → `rowKey={(it) => it.id}`、`rowTestId={(it) => \`inventory-row-${it.id}\`}` と書く。
  - hasNextPage の式が無い。今は totalPages から（:179、next の disabled は `page >= totalPages || loading` :765）→ `hasNextPage={page < totalPages}`。
  - 前へ／次への文言: DataTable の既定は '‹' '›'（DataTable.tsx:127-128）。今は t("common.previous") / t("common.next")（:759,766）。KGI 10「前へ／次へ」のため prevPageLabel/nextPageLabel を渡すと書く。
B-15 testId/aria-busy の条件付き記述を確定させる（2-1 :144 末尾）
  - 上の 2(a) のとおり参照 0 件。「実装役は無いと分かったら止めて報告」を消し、「inventory-table・aria-busy は付けない（参照なし）。DataTable に testId/busy の口は足さない」のように確定文にする（どちらを選ぶかは設計の判断。条件分岐のまま渡さない）。
B-16 受入の e2e が今の形では空の表で緑になる（2-4 :160-161）
  - horizontal-overflow.spec.ts の routeMocks（:31-45）と commonMocks に GET /inventory が無い → mockApi は未定義を 404 で返す（api-mock.ts の注記）→ 行0件で検査している。KGI 6（カードで横にはみ出さない）は行が無いと確かめられない。
  - 新規 e2e（:161）も同じで、行の mock が無いと 900px で natural ≤ frame になり zoom=1 のまま緑になる。また「スクロール箱の bottom ≤ innerHeight」は表より上の要素の高さ次第で、zoom の補正と無関係に赤／緑が決まる【推測】。
  → 設計に書く: (1) GET /inventory（幅が出る長い商品名を含む items 数件＋ total・suppliers）、GET /me/inventory-filters、GET /products/tcg-types の mock。(2) 375px: 上の mock 付きで doc の横スクロールなし＋カード（rowTestId）が見える。(3) 900px: card の --comp-table-fit-zoom が 1 未満であることを先に assert し、スクロール箱の見た目の高さが max-height（innerHeight − 18rem の px）以下、doc の横スクロールなし。1280px は zoom 未設定。
B-17 提供者の置き場所が PO 決定 4「レイアウトも同じ」と違う（3-2 :183）
  - GAS は PC で絞り込み欄を display: contents にしてツールバーに並べる（H:308 `.mobile-filter-panel { display: contents; }`、H:311、提供者は H:874-887）。スマホではドロワーの中で一覧を開いた形（H:596-681）。
  - design.md:183 は詳細フィルタパネル（ドロワー）の先頭 → PC ではフィルタを開かないと選べず、GAS と配置が違う。
  → PC はツールバーに MultiSelect を置く（スマホはドロワー）に直すか、ドロワーに置く理由を書いて PO 確認を取る。

== 止めずに直してよい指摘 ==
N-r2-1 カテゴリ列を消すと categoryLabel・tcgTypeName（InventoryPage.tsx:172-177）と visibleColCount（:183-184）が未使用になり lint で止まる。消すと書く（tcgTypes 自体はタブ :600-617 で使うので残す）。design.md:125 の行範囲は :683-741 が正。
N-r2-2 文字の大きさ: 今の表は font-md（:645、:640 の注記「フォントは少し大きめ」）、DataTable は font-sm（DataTable.css:25）。GAS も font-sm（H:400）なので揃う方向だが、変わることを設計に書く。
N-r2-3 並び替えの位置: GAS はツールバーで 検索 → 24時間 → 並び替え → 絞り込み（H:818-847）。design.md:149「検索の右」だと24時間より前になる。PO 決定 2「同じレイアウト」に合わせるなら 24時間の後。
N-r2-4 Q14=y の記録の置き場所: 引用元 design.md:393 は「確認中」のまま。チャット原文を置いた場所（ファイル）を design.md:9 に足す。
N-r2-5 onSort の形: DataTable は onSort(key, dir)。呼び出し側で setSortField(key)・setSortDir(dir)・setPage(1) とすると書く（今の onSort は「別列は asc から」で DataTable.tsx:158-163 と同じ挙動）。
N-r2-6 カードにも rowClassName を付ける（:90）ので .comp-table__row--danger/--warning の背景はカードにも付く。意図どおりならそのまま。

== 3. 便1〜3 を実装役へそのまま渡せるか ==
- 便1: 不可（B-12・B-13）。
- 便2: 不可（B-14・B-15・B-16。便1 の確定も前提）。
- 便3: backend 部分（3-1・3-2 backend・openapi 手順・テスト）はこのままで渡せる。frontend 部分は B-17 の置き場所が決まるまで不可。
PO 承認: B-17 で「ドロワーに置く」を選ぶ場合のみ要。PC ツールバーに置く（GAS どおり）なら不要。
Generator へ渡せるか: false（B-12〜B-17 を直して r3 で再提出）
```

## r3

```text
判定: APPROVE（r2 の B-12〜B-17 は全件解消。r3 で書き足した部分に、実装が止まる・壊れる箇所は見つからなかった。弱い点は N-r3-1〜9 として実装時に直す）

対象: /Users/tanizawashingo/worktrees/salesanchor/release-inventory-table-unify/docs/handoff/inventory-table-unify/{design.md(r3, 267行), recon.md(80行)}
照合: worktree HEAD e1cdbc468、origin/main 4866be5bf（git fetch 後）。`git diff --stat origin/main HEAD -- frontend backend` の出力は空【事実】
GAS: /tmp/CC報告ファイル/gas_pull_prod/index.html（H、1622行）

== 1. r2 指摘の解消判定 ==
B-12 解消。design.md:46-50。useIsMobile の初期値と useEffect の両方で typeof window.matchMedia を見る形。
     【事実】frontend/src/hooks/useIsMobile.ts:16-25 は今は無条件で呼ぶので、ここを直せば DataTable が常に呼んでも jsdom で落ちない。
     【事実】テストで matchMedia を差し替えているのは useIsMobile.test.ts:5-18（vi.stubGlobal で addEventListener/removeEventListener あり）と InboxMessageThread.discordSendError.test.tsx:20（フックごと vi.mock）の2件だけ。addEventListener を持たない雑なモックは無い → ガード追加で既存テストは壊れない。
     【事実】useIsMobile.test.ts は afterEach で vi.unstubAllGlobals（:24-26）。新しい「matchMedia が無いと false」は stub しなければ jsdom 既定（未定義）で書ける。既存6件（:29-76）はガードの後も同じ結果。
B-13 解消。design.md:77-88。
     - 角 `.comp-table--sticky thead th.<固定列>` (0,2,2) が見出し (0,1,2) に勝つ。
     - stylelint no-descending-specificity は末尾の複合セレクタ単位で比べる。`td.<固定列>` の並びは (0,2,2)→(0,3,2)×3→(0,4,2)×2 で下がらない。`th` と `th.<固定列>` は末尾が違う。既存の DataTable.css（:12-192）に `td.<固定列>`・`th` で終わるセレクタは無い【事実】→ 止まらない。
     - 選択列のクラス名（comp-table__cell--sticky-check）と left の値が決まった。--comp-table-check-col-w は tokens.css:515 に実在【事実】。全体に `* { box-sizing: border-box }`（index.css:410-414）があるので、選択列の幅 40px と left:40px は合う【事実】。
B-14 解消。design.md:166-171。rowKey/rowTestId=it.id（InventoryPage.tsx:26,674）、hasNextPage=page<totalPages（:179）、prev/nextPageLabel=common.previous/next（ja.json に previous「前へ」next「次へ」あり【事実】）、pageInfo（:762-764 と同じ）。
     【事実】CommerceNavigationButtonMigration.test.tsx:48-71 は inventory-prev/next を testid で取り、disabled と GET の URL だけ見る。DataTable の prev は `page<=1||paginationDisabled`、next は `!hasNextPage||paginationDisabled` で同じ結果。URL（sort=release_date&order=desc…）は便2・便3 で変わらない。
B-15 解消。design.md:173 で「付けない・口も足さない」と確定。
B-16 解消。design.md:189。
     【事実】fixtures は実在: installAuthBypass（tests-e2e/utils/auth.ts:20、引数 page）、mockApi（utils/api-mock.ts:55、キー "<METHOD> <PATH>"・/api/v1 抜き・クエリは無視してパスだけで照合 :66-69・未定義は 404 :84-93）、commonMocks（utils/common-mocks.ts:42、products.view を含む ALL_PERMISSIONS :13-40）。
     【事実】API の実パス: GET /api/v1/inventory（inventory_offers.py:282-286、products.view。main.py:626 で prefix /api/v1）、GET /api/v1/products/tcg-types（products.py:258、main.py:389）、GET /api/v1/me/inventory-filters（me_inventory_filters.py:85）。設計のキー "GET /inventory"・"GET /products/tcg-types"・"GET /me/inventory-filters" はそのまま当たる。フロントも API_BASE="/api/v1"（lib/api.ts:30）。
     【事実】/inventory のルート（App.tsx:206）に画面側の権限ガードは無い。375px は MobileShell（App.tsx:137-138）。
     弱い点は N-r3-3・N-r3-4。
B-17 解消。design.md:211-213。GAS は PC で 検索→24時間→並び替え→(絞り込みボタンは PC で非表示 H:316)→更新→コンディション→提供者（H:818-887、H:308-311 の display: contents）。「並び替えの後・詳細フィルタボタンの前」は GAS の並びと矛盾しない。スマホはパネル先頭。
     InventoryFilterPanel の props 追加（supplierOptions・selectedSupplierIds・onSupplierChange・showSupplierSelect）は今の Props（InventoryFilterPanel.tsx:21-52）に足すだけで書ける。

N-r2-1 解消（design.md:146）。N-r2-2 解消（:145）。N-r2-3 解消（:178）。N-r2-4 解消（:8。メモ ~/.claude/projects/-Users-tanizawashingo-salesanchor/memory/project_session_20261015_viewer_autonomy.md は実在し、:11 に「アプリの在庫表も同じ作りにする」【事実】）。N-r2-5 解消（:169）。N-r2-6 意図どおりとして了承（:266）。

== 2. r3 の新しい内容の突合 ==
(a) 1-0b useIsMobile のガード → 上の B-12 のとおり食い違いなし。useFitTableZoom も同じガード（:48）。ResizeObserver が無い jsdom では window resize に落とす記述あり（:101）。
(b) 1-2 CSS の詳細度と並び → 上の B-13 のとおり。使うトークン --bg-subtle/--bg-surface/--bg-hover/--info-bg（index.css:17-19,109）、--z-base（tokens.css:121）は実在【事実】。
(c) 2-1 props → DataTable の既存 props（DataTable.tsx:51-93）と型が合う。selectedIds は Set<string>（InventoryPage.tsx:138）、sortDir は "asc"|"desc"（:135）で SortDir と一致。sort の列 key は _SORT_COLUMNS（inventory_offers.py:118-130）と一致。
(d) 2-4 e2e と fixtures → 上の B-16 のとおり実在・使い方とも合う。
(e) 3-2 置き場所と props → 上の B-17 のとおり。backend の d.search_keywords は配信行の最終 SELECT に実在（tcg_distribution_svc.py:251-254,263）【事実】。_build_view_filters（inventory_offers.py:171-195）にキーワード引数を足す形は test_inventory_distribution_rows.py:47-50 の dict.fromkeys 呼び出しを壊さない【事実】。

== 止めずに直してよい指摘（r3）==
N-r3-1 型名: design.md:144 の `DataTableColumn<InventoryItem>` は実物では `InventoryRow`（InventoryPage.tsx:25、export なし）。features/inventory へ移すとき export するか型を移す。
N-r3-2 行番号の小さなずれ: 選択の td は :675-683、列の td は :684-740、pageInfo は :762-764（design.md:144,170 はそれぞれ1行ずれ）。中身の指す場所は合っている。
N-r3-3 375px の「doc の横スクロールなし」は素通りする: 【事実】.mobile-content は overflow-y: auto（mobile-shell.css:22-25）。CSS の仕様で overflow-x も auto になるので、中身がはみ出しても document の scrollWidth は増えない。KGI 6 を確かめるなら `main.mobile-content` の scrollWidth ≤ clientWidth、または各カードの getBoundingClientRect().right ≤ innerWidth を見る（既存 horizontal-overflow.spec.ts も同じ理由で素通りしている可能性がある【推測】。対象外）。
N-r3-4 900px の「スクロール箱の高さ ≤ innerHeight − 18rem」は行5件だと素通りする: 800 − 288 = 512px に対して、5行 × 44px × zoom ＋ 見出しは 512px に届かない【推測: 行高 --comp-table-row-h-default 44px（tokens.css:508）からの計算】。max-height の補正（design.md:103 で【未確認】としている点）を確かめるには、mock の行を 20 件以上にして、高さが上限で止まることを見る。
N-r3-5 mock の長い文字列: 設計のとおり 900px で幅を超えさせるには、日本語や空白入りの長い文字列にする。空白なしの長い英数字だと、(1) 1440px でも幅を超えて「zoom 未設定」の検査が落ちる、(2) カードで折り返されずはみ出す（カードの値に overflow-wrap: anywhere を付けておく。GAS H:731 と同じ）。
N-r3-6 折り返し: GAS は表全体が white-space: nowrap（H:401）。DataTable の td は折り返す（DataTable.css:46-51）ので、PC では「文字が折り返したうえで、見出しの幅が足りないときだけ縮む」になり、GAS と見た目が少し違う。どちらにするかは KGI 5 の PO 目視で見る（nowrap を足すなら N-r3-5 の 1440px の検査と合わせて決める）。
N-r3-7 フックの呼び方: useFitTableZoom は React の規則上いつも呼ぶので、fitToWidth が false のときやカード表示で ref が null のときは何もしない作りにする（design.md:96 の手順1に null の扱いを足す程度）。
N-r3-8 提供者の旧 props: 除外欄（InventoryFilterPanel.tsx:152-173）を消すと、Props の hiddenSupplierIds・toggleHiddenSupplier（:29-30）と InventoryPage.tsx:396-404 の toggleHiddenSupplier が使われなくなる。lint で止まらないよう同じ便で消す（setHiddenSupplierIds は GET で使うので残る）。
N-r3-9 固定列の色の優先: 固定列は danger/warning の後に selected を書くので選択が勝つ。行（tr）は danger（DataTable.css:164）が selected（:138）より後なので danger が勝つ。在庫表は rowClassName を使わないので見た目の差は出ない。直すなら固定列側の並びを行と同じにする。

== 3. 便1〜3 を実装役へそのまま渡せるか ==
- 便1: 渡せる。N-r3-7 は実装時に直す。
- 便2: 渡せる（便1 のマージ後）。N-r3-1・2・3・4・5 は e2e とファイル移動のときに直す。
- 便3: 渡せる。N-r3-8 は同じ便で直す。速さの基準値（design.md:227）を便3 の前に取ること。
PO 承認: 追加は不要（B-17 は GAS どおり PC はツールバーに置く形を選んだため）。N-r3-6（折り返し）と文字の大きさ（design.md:145）は KGI の PO 目視で確認する。
Generator へ渡せるか: true
```
