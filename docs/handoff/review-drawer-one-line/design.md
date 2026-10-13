# 要確認一覧の1行化（作業3）と確認スライドの3列化（作業4）設計 — 2026-10-13 Opus

状態: 設計審査済み（Fable APPROVE 2026-10-13）。実装は PO の一任（2026-10-13「PRマージ、デプロイまで完走」＋金型許可「GO #4226 y」）に基づく。PO の依頼（2026-10-13）:
- 作業3「表の行が折れて2行になる → 1行で見たい」
- 作業4「行を押して出るスライドを、上段3列（原文／Gemini の抽出／システムの最終結果）＋下段に直す欄、文字の間隔をそろえる」
PO 許可: 「GO #4226 y」の「y」＝金型3件（DataTable の列ごと1行・省略表示／Drawer 幅のトークン化／3列レイアウト）の追加（ADR-144 の PO 許可）。

## 1. KGI（PO が○×で判定できる形）
- KGI-1（作業3）: 要確認一覧の各行が **1行（高さ 44px）** で出る。長い商品名・理由は末尾が「…」になり、マウスを当てると全文が出る。
- KGI-2（作業4）: 行を押して出るスライドの上段に、左から **原文 → Gemini抽出 → システム最終結果** の3列が並び、3つの見出しの上端がそろう。原文は、その商品の行の位置まで自動で送られ、範囲が色付きで示される。
- KGI-3（作業4）: Gemini とシステムの同じ項目（例: 価格）が **同じ高さの行** に並ぶ（項目ラベル列は 72px でそろう）。直す欄（状態の確認・商品を直す・理由）は下段にまとまる。
- KGI-4: 他の画面の見た目は変わらない（DataTable 55画面・Drawer 27画面・仕入先詳細の比較表）。例外（意図）: 原文ペインの凡例「見出しの範囲」は、範囲を渡していない V102PostEditModal でも出なくなる。

## 2. 現在地（recon の要約。全文は docs/handoff/review-drawer-one-line/recon.md）
- 折れる理由（作業3）: frontend/src/components/DataTable.css:46-51 の td に white-space 指定がなく、長い文字は折り返す。frontend/src/features/tcg-analysis-review/review-row-actions.css:2-8 が `flex-wrap: wrap` で選択欄とボタンが2段になる。
- 狭い理由（作業4）: frontend/src/components/Drawer.css:30 `width: var(--drawer-panel-width, 480px)` で変数は未定義＝常に 480px。比較表は item-comparison-readonly.css:3-9 で最小 632px 必要。
- 間隔がそろわない理由: 項目の間隔の CSS が frontend/src/features/tcg-analysis-review/supplier-detail-view.css:314-369 で `.supplier-detail-items` の下に限定され、body へポータルされる Drawer（Drawer.tsx:114）には効かない。
- 原文は API から届いている（backend/app/services/tcg_analysis_review_svc.py:260-279 の raw_text と gemini.span `L{start}-{end}`）が、ReviewItemDrawer.tsx:31-32 は原文を出していない。
- 関連 ADR: docs/adr/ADR-144-ui-component-governance.md（金型）・docs/adr/ADR-067-design-token-enforcement.md（トークン）・docs/adr/ADR-027-ui-internationalization.md（i18n）。DataTable/Drawer の仕様を定める ADR はない（recon §ADR 検索）。

## 3. 直し方

### 3-1. Drawer に幅の段階を足す（金型拡張・作業4）
- frontend/src/tokens.css（:444-445 の modal 幅の近く）に追加:
```
--drawer-panel-w-default: 480px;
--drawer-panel-w-wide: var(--modal-xwide-w);   /* 1100px */
```
- frontend/src/components/Drawer.css:30
```
変更前: width: var(--drawer-panel-width, 480px);
変更後: width: var(--drawer-panel-w-default);
```
  （値は同じ 480px＝既存 27 画面は変わらない）
- Drawer.css に追加（767px 以下の @media より **前** に置き、スマホは従来どおり 100%）:
```
.comp-drawer-panel--wide { width: min(var(--drawer-panel-w-wide), 100vw); }
```
- frontend/src/components/Drawer.tsx: props に `size?: 'default' | 'wide'`（既定 'default'）。'wide' のとき panel の className に `comp-drawer-panel--wide` を足す。他の props・動きは変えない。
- frontend/src/components/Drawer.stories.tsx に `Wide` を追加。

### 3-2. DataTable に列ごとの1行・省略表示を足す（金型拡張・作業3）
- frontend/src/components/DataTable.tsx:29-40 `DataTableColumn` に `ellipsis?: boolean` を追加（説明コメント: 「true で1行に収め、はみ出しは … にする。width があればその幅まで」）。
- :272 の td:
```
変更前: <td className="comp-table__td">{content}</td>
変更後: ellipsis が true のとき
  <td className="comp-table__td comp-table__td--ellipsis">
    <div className="comp-table__cell-ellipsis"
         style={col.width ? { maxWidth: col.width } : undefined}
         title={typeof content === 'string' ? content : undefined}>{content}</div>
  </td>
  false/未指定のときは変更前と同じ
```
  （実際の変数名は実装時に該当行に合わせる。ellipsis 未指定の列の出力 HTML は1文字も変えない）
- tokens.css に `--comp-table-ellipsis-max-w: var(--col-width-medium);`（200px）。
- DataTable.css に追加:
```
.comp-table__td--ellipsis { white-space: nowrap; }
.comp-table__cell-ellipsis {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: var(--comp-table-ellipsis-max-w);
}
```
- DataTable.stories.tsx に `Ellipsis`（長い文字の列あり）を追加。
- 文字列でない中身（バッジ等）は title を付けない。全文は「行を押して出るスライド」で見られる。

### 3-3. 要確認一覧に適用（作業3）
- frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:111-167
  - 商品名・仕入先・出どころ・理由・日付の5列に `ellipsis: true`。
  - 商品名 `width: "var(--col-width-wide)"`（360px）、理由 `width: "var(--col-width-medium)"`（200px）。
  - :24 `INLINE_FIX_COLUMN_WIDTH = "320px"` の直書きを、tokens.css の新トークン `--review-inline-fix-col-w: 320px` を参照する `"var(--review-inline-fix-col-w)"` に置き換え（値は同じ）。
- frontend/src/features/tcg-analysis-review/review-row-actions.css:2-8 `flex-wrap: wrap` → `flex-wrap: nowrap`。ボタン（中の Button のクラス名は実装時に実物で確認）に `flex-shrink: 0`。
- 長い一時的なエラー表示が列からはみ出す可能性は受け入れる（表の外枠 DataTable.css:14 が横スクロール）。
- DataTable の props コメントに「width が max-width として無効な値（例 "1fr"）のときは CSS 既定（--comp-table-ellipsis-max-w 200px）になる」と明記。`.comp-table__td--ellipsis` は DataTable.css §2（:53-56 `--check` の隣）に置く。

### 3-4. 確認スライドを3列＋下段にする（作業4）
- frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:61-99 を次の並びに変える:
```
<Drawer size="wide" …既存のまま>
  <Stack gap="4">
    {Callout（既存のまま・条件も同じ）}
    <TwoColumn ratio="1:2" gap="3" align="start" className="review-item-top">
      <section className="review-item-source">
        <h3>{t("reviewItem.sourceHeading")}</h3>        // 「原文」/"Source text"
        <ShadowSourcePane rawText={item.raw_text}
                          blockRange={parseSourceLineRange(item.gemini.span)} />
      </section>
      <ItemComparison readOnly … 既存の props のまま />   // 中で Gemini | システム の2列
    </TwoColumn>
    <section className="review-item-fix">
      <h3>{t("reviewItem.fixHeading")}</h3>             // 「直す」/"Fix"
      <Stack gap="3">
        {ConditionReviewPanel（既存のまま）}
        {「商品を直す」ボタン（既存のまま）}
        {理由の一覧（既存のまま）}
      </Stack>
    </section>
  </Stack>
</Drawer>
```
  - 3列は「TwoColumn（原文｜比較表）＋比較表の中の2列」で作る。新しい3列の金型は作らない（PO 許可の3件のうち使うのは2件。§4 代替案）。
  - :31-32 のコメントを「原文ペインはその商品の行へ自動で送るため、行ジャンプは何もしない」に直す（noJump は残す）。
  - raw_text が空・span が読めないときは ShadowSourcePane の既存の空表示に任せる（blockRange は null）。
  - 幅の計算（Fable 審査で実物から算出）: 1100 − 本文 padding 24×2 = 1052、右列 (1052−12)×2/3 = 693.3、比較表の内側 693.3 − 24 = 669.3 ≥ 最小 632。画面幅 768〜1099px では Drawer＝画面幅となり右列が 632 を下回るため、画面側 CSS（review-item-drawer.css 新規・features 配下）で `@media (max-width: 1279px) /* = --breakpoint-tablet-max */ { .comp-two-column.review-item-top { grid-template-columns: 1fr; } }`（原文が上・比較表が下の縦積み）にする。ブレークポイントは tokens.css:102/:113-117 の規約どおり既存値 1279px を使う（新しい値を足すと check-breakpoint-sync.js の同期対象になるため足さない）。セレクタは特異度 0,2,0 にして TwoColumn.css:10 との読み込み順に依存させない。review-item-drawer.css の import は ReviewItemDrawer.tsx で TwoColumn より後に置く。
- frontend/src/features/tcg-analysis-review/sourceRawNavigation.ts に追加:
```
export function parseSourceLineRange(value: string | null | undefined): { start: number; end: number } | null
// "L12-15" → {12,15}、"L12" → {12,12}、それ以外・start>end・0以下 → null
```
  戻り値は構造的な型（ShadowSourcePane を import しない＝循環を作らない）。
- frontend/src/features/tcg-analysis-review/ShadowSourcePane.tsx:43-50 凡例: 範囲が null の項目は出さない（V102PostEditModal.tsx:229 は headingRange を渡していないのに「見出しの範囲」が出ている不整合も同時に直る）。
- 間隔の SSOT 化: supplier-detail-view.css:314-369 の比較表用ルールを item-comparison-readonly.css へ移し、前置きを `.supplier-detail-items` → `.item-comparison--readonly` に付け替える（readOnly 時の根要素は ItemComparison.tsx:36 で `item-comparison item-comparison--readonly` と確定）。宣言の中身は変えない。
  - 例外: :317 `.supplier-detail-items .item-comparison { padding: var(--space-3) }` は機械的に置換すると同じ要素を指せないため `.item-comparison--readonly { padding: var(--space-3); }` とし、item-comparison-readonly.css の先頭（既存 :3-9 の前）に置く。
  - source-raw-pane.css:80-89 の `.comparison-metadata-row` 2ルール（ItemComparison が使う）も item-comparison-readonly.css へ移し、source-raw-pane.css から削除する（Drawer・story でも読み込まれるようにする。宣言は不変）。
  - 72px は tokens.css の新トークン `--comparison-label-col-w: 72px` に置き換え、移したルール（元 supplier-detail-view.css:338/:365 と元 source-raw-pane.css:82）で参照。
  - 原文の見出し `.review-item-source h3` は、比較表の見出し（`.item-comparison--readonly .item-head-grid h3`）と同じセレクタ群に並べて同じ見た目にする（値の重複を作らない）。
- 文言 frontend/src/locales/ja.json・en.json に同じキーで追加: `reviewItem.sourceHeading`「原文」/"Source text"、`reviewItem.fixHeading`「直す」/"Fix"。

触らない範囲: backend 全部・API・DB／DataTable のソート・選択・ページ送り／Drawer の開閉・フォーカス・ポータル・フッター／ItemComparison の項目と中身／ConditionReviewPanel・ProductMasterDrawer の中身／SupplierDetailView の構造（CSS の置き場所だけ変わる）／`--drawer-width`（ユーザードロワー用・tokens.css:175）／`--max-width-truncate`。

## 4. 代替案と選ばなかった理由
- 3列の新しい金型（ThreeColumn）を作る → 比較表の中身はすでに Gemini｜システムの2列で、項目ごとに行の高さをそろえる仕組み（aligned-fields）を持つ。3列金型に分けると項目の高さそろえが崩れる。TwoColumn＋既存2列で同じ見た目が作れ、前例（V102PostEditModal.tsx:227）もあるため不採用（YAGNI）。
- 表を折り返したまま行の高さを固定する → 文字が隠れて読めなくなるだけで「…」の目印も全文も出ない。不採用。
- Drawer をやめて全画面ページにする → 一覧を見ながら確認する今の流れが変わる。PO の依頼は Drawer の中の並べ方。不採用。
- `--drawer-panel-width` という今の名前をそのまま定義する → 段階（default/wide）を表せず、使う側が値を直書きしがち。tokens の命名（`--modal-wide-w` 等の `-w`）に合わせ新名にする。

## 5. 受入条件
| 基準 | 検証方法 |
|---|---|
| KGI-1 各行 44px・長い文字は … | 実装担当が手元で `storybook dev` を起動し、一回限りの Playwright スクリプト（repo 外 ~/CC報告ファイル-keep/review-page-20261013/ に置き、生出力も同所へ保存）で Storybook `DataTable/Ellipsis` を 1440x900 で開き、全 tr の高さ 44±1px、長いセルで scrollWidth > clientWidth、title に全文 |
| KGI-1 実画面 | 本番の要確認一覧を PO が目視（○×） |
| KGI-2 3列の並び | 同スクリプトで Storybook `ReviewItemDrawer`（新規 story。item は `condition_review: null`・`gemini.span: "L12-15"`・raw_text 20行程度・`review_reason_details` 1件以上。condition_review を入れると ConditionReviewPanel.tsx:37 が fetch して Storybook では失敗表示になるため入れない）1440x900: Drawer の幅 1100px、原文見出し.x < Gemini見出し.x < システム見出し.x、3つの h3 の上端の差 ≤1px、原文に範囲の色付き行がある |
| KGI-2 スマホ | 同 story を 390px 幅: Drawer の幅 390px |
| KGI-3 項目の高さ | 同 story: 各項目で Gemini 側とシステム側の行の y と高さの差 ≤1px、ラベル列の幅 72px。下段は「商品を直す」ボタンと理由一覧が原文・比較表より下にあること（「状態の確認」欄は story では出ないため測定対象外・本番で PO 目視） |
| 縦積み | 同 story を 1024px 幅: 原文の下に比較表が来る（原文.bottom ≤ 比較表.top）・横スクロールなし |
| KGI-4 他画面 | (a) ellipsis 未指定の DataTable の出力が変わらない（単体試験）(b) Drawer 既定の幅 480px（単体試験＋Storybook 既存 story の実測）(c) 移した CSS の宣言が移動前と一致し、`.supplier-detail-items .comparison-` で始まるルールが残っていない（`git grep` と diff） |
| 型・試験・lint | CI（tsc・vitest・eslint・stylelint・i18n 同一キー・design token チェック） |

実測の生出力は ~/CC報告ファイル-keep/review-page-20261013/ に保存。寸法の実測は CI に入れない（既存 CI は build-storybook のみで Storybook を開く harness がない。frontend-check.yml:75-92）。CI の守り手は §7 の単体試験。単体試験では DataTable の `style.maxWidth` に var() の文字列が残ることを assert する（jsdom での保持は未確認のため試験で確かめる）。

## 6. 弊害とリスク
- 省略表示で文字が見えなくなる → title の全文とスライドで見られる。ellipsis は指定した列だけ。
- 幅 1100px のスライドは 1100〜1280px の画面で一覧をほぼ覆う → 一覧へ戻るのは閉じるだけ。スマホは従来どおり全幅。
- CSS の移動で仕入先詳細の見た目が変わる恐れ → 宣言は変えずセレクタの前置きだけ変え、§5 KGI-4(c) で確かめる。
- 一時的な長いエラー表示ははみ出し得る（受け入れ）。
- 画面幅 1100〜1279px では3列が出ず縦積みになる（ブレークポイント規約に合わせるための受け入れ）。1280px 以上で3列。

## 7. 維持の仕組み
- 守り手: CI の vitest（新規 frontend/src/components/DataTable.test.tsx・frontend/src/components/Drawer.test.tsx、sourceRawNavigation の parseSourceLineRange 試験、ShadowSourcePane の凡例試験、ReviewItemDrawer.test.tsx の原文表示と wide 試験）と Storybook の story（Drawer/Wide・DataTable/Ellipsis・ReviewItemDrawer）。
- 値はすべて tokens.css のトークン（直書きなし）。金型の使い方は各 story と props のコメントで示す。

## 8. 外部・過去事例の参照と我々への応用
- 自社の前例: frontend/src/features/tcg-analysis-review/V102PostEditModal.tsx:227-229 が TwoColumn の左に ShadowSourcePane（原文）・右に編集欄を置く並べ方で稼働中。今回はこれと同じ組み合わせを Drawer に使う。
- CSS の text-overflow: ellipsis は white-space: nowrap と overflow: hidden が揃って初めて効く（MDN text-overflow の説明）。td に直接ではなく中の div に付けるのは、表の列幅計算で td の max-width が効かないため。他社事例の数値は使わない（判断は自社画面の実測で足りるため）。

## 9. 戻し方
- フロントのみの変更。PR の revert で戻る。DB・API 変更なし。

## 審査
- 2026-10-13 Fable（設計審査）1回目: REVISE。指摘8件（padding の移し方・測定手段・metadata 行 CSS の置き場・768〜1099px・story データ・ellipsis の無効値・凡例の例外・根要素クラス確定）を本版で反映。
- 2026-10-13 Fable 2回目: APPROVE（条件2点＝ブレークポイントを 1279px に・セレクタを 0,2,0 に。本版で反映済み、再審査不要と判定）。
