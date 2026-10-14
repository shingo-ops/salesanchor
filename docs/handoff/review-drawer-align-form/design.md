<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — review-drawer-align-form

**対象ADR**: `docs/adr/ADR-144-ui-component-governance.md` / `docs/adr/ADR-067-design-token-enforcement.md` / `docs/adr/ADR-027-ui-internationalization.md`  
**recon**: `docs/handoff/review-drawer-align-form/recon.md`  
**日付**: 2026-10-14  
**担当**: Planner（Opus）。設計審査は Fable（architect）

---

## 0. PO の依頼と決定（原文）

- 依頼（2026-10-14）:「原文の枠やフレームも同じ高さに揃えられる？いまは原文のカードと右側のテーブルがズレていて見づらい、余白が多くなってもいいからテーブルと高さも位置も揃えてくれ…下の直す入力欄も簡素なのでフォームのように入力できるようにしてくれ」
- 決定（2026-10-14、PO「y」）: 「直す」欄は**今ある保存の仕組みで保存できる項目だけ**をフォームにする。商品名・数量・価格は表示のみ（保存先の新設はしない）。

## 1. 目的（KGI）

PO が要確認スライドを開いたとき、次がすべて ○ になる。

- A1: 左「原文」の枠の上端と、右の比較表の枠の上端の差が 0px（±1px）。
- A2: 左の枠の下端と、右の表の枠の下端の差が 0px（±1px）。
- A3: バッジ（要確認・除外対象）が有る件・無い件のどちらでも A1/A2 が成り立つ。
- B1: 「直す」欄に、ラベル付きの「商品」入力欄（候補検索）と「付け替える」ボタンが画面上に常に見える（ボタン1つだけの状態ではない）。
- B2: 「状態」の確定（ConditionReviewPanel）にラベルが付き、「商品」欄と同じフォームの見た目で並ぶ。
- B3: 保存すると既存 API `POST /tcg/items/{id}/corrections`（field_name=product_id）が呼ばれ、成功の Callout が出て一覧が再読み込みされる。

## 2. 変更前 → 変更後

### A. 原文の枠と表をそろえる

変更前（recon §1-1）: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:68` は `align="start"`。左は枠の外の h3「原文」の分だけ下がり、右はバッジ行の分だけ下がる（バッジ0件なら下がらない）。高さは左が「凡例＋最大320px」、右が「バッジ＋表」で無関係。

変更後:
1. 左右どちらの列にも、**同じ高さの見出し行**（`.review-item-pane-head`）を置く。
   - 左: 文言「原文」（既存キー）。
   - 右: 新キー `reviewItem.compareHeading`（ja「比較」／en「Comparison」）と、バッジ。バッジは見出し行の中に移す。
   - 見出し行の高さは、ファイル先頭で宣言する部品固有トークン `--review-pane-head-h` で固定する（ADR-067、前例 `frontend/src/features/tcg-analysis-review/shadow-source-pane.css:36`）。値は既存の Badge の高さ以上で、Generator が実測して決め、根拠を PR に書く。
   - 見出し行の中は `display:flex; align-items:center; gap: var(--space-2); flex-wrap: nowrap; overflow: hidden`。
   - バッジ0件の件も見出し行は出る（高さが変わらない）。
2. 右の見出し行は、**ItemComparison の readOnly 分岐の中に描く（第2案に固定。審査 REVISE #2）**。
   - 任意の props として `heading?: string` を足す。
   - `heading` を渡されたときだけ、article の中（padding の内側）の先頭に `.review-item-pane-head` を描く。その中に見出しとバッジを並べ、既存の `.item-comparison__badges` の div は出さない。
   - `heading` が無いときは、今の DOM のままにする。これで SupplierDetailView（`frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:116`）と既存の試験（`frontend/src/features/tcg-analysis-review/ItemComparison.test.tsx:64-99`）は変わらない。
   - 左も同じ形にする。`.review-item-source`（padding の内側）の先頭に `.review-item-pane-head` を置き、文言は「原文」にする。今の h3 はこの見出し行に置き換える。
3. 高さを右の表に合わせる（広い幅 ≥1280px のときだけ）。
   - TwoColumn を `align="stretch"` にする。
   - 左の列 `.review-item-source` に `position: relative` を付ける。padding は今の `var(--space-3)` のまま。
   - 左の列の中で、普通に並ぶ（位置の計算に入る）のは見出し行だけにする。
   - 左の枠 `.review-item-top .shadow-source-pane` は `position:absolute` にし、`inset: calc(var(--space-3) + var(--review-pane-head-h)) var(--space-3) var(--space-3) var(--space-3)` とする。absolute の inset は padding の外枠から測るため、padding の分を足す（審査 REVISE #1）。
   - 上端と下端の計算式（どちらも行の上端からの距離。H = 行の高さ。行の高さは右の列だけで決まる）:
     - 左の枠の上端 = space-3 + head-h
     - 右の表の上端 = space-3（article の padding）+ head-h
     - → 差は 0
     - 左の枠の下端 = H − space-3
     - 右の表の下端 = H − space-3（article の padding-bottom）
     - → 差は 0
   - 見出し行は左右とも `height: var(--review-pane-head-h); margin:0; box-sizing:border-box`。見出し行と枠の間の余白は 0 にする。今の `.item-comparison__badges` の margin-bottom は、見出し行の中では使わない。
   - 本文 `.review-item-top .shadow-source-lines` は `flex:1; min-height:0; max-height:none; overflow-y:auto` にする。原文が長ければ枠の中でスクロールし、短ければ枠の下に余白が残る（PO 了承済み）。
   - **上書きはすべて `.review-item-top` で始まるセレクタだけで書く**。`shadow-source-pane.css` は 1 行も変えない。これで V102PostEditModal（`frontend/src/features/tcg-analysis-review/V102PostEditModal.tsx:227-240`）には届かない。
4. 外側の余白は今のままにする。
   - 左: `frontend/src/features/tcg-analysis-review/review-item-drawer.css:4-6`
   - 右: `frontend/src/features/tcg-analysis-review/item-comparison-readonly.css:3`
   - どちらも `var(--space-3)`。
5. 狭い幅（<1280px。縦に積む。`frontend/src/features/tcg-analysis-review/review-item-drawer.css:8-12` の @media の中）では、次をすべて元に戻す（審査 REVISE #3）。
   - `.review-item-top .shadow-source-pane { position: static; inset: auto; }`
   - `.review-item-top .shadow-source-lines { flex: initial; max-height: var(--shadow-source-max-h); }`。overflow-y:auto は元から auto なので、そのままでよい。
   - `.review-item-source { position: static; }`
   - 見出し行の高さはそのまま残す。左右で同じなので問題ない。
6. スクショにある「翻訳」アイコンについて。
   - Generator はステップ1で DOM を調べ、自社の要素かどうかを報告する。
   - 自社の要素でない場合（ブラウザや拡張機能が出すもの）は対象外とし、その事実を測定結果に書いて続ける。
   - **自社の要素だった場合は、そこで止まって NEEDS_DECISION で報告する**。設計に差し戻し、実装には進まない（審査 REVISE #8）。

### B. 「直す」欄をフォームにする

変更前（recon §1-2）: ConditionReviewPanel、「修正する」ボタン（押すと自作の pmd-drawer が開く）、確認が必要な理由。

変更後（`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:75-113` の section の中を、上から順に）:
1. **商品の付け替え**（新しい部品 `ReviewProductFixForm.tsx`。同じフォルダに置く）
   - ラベル「商品」（新キー）。入力欄は既存の `.comp-field` / `.comp-field__label`（`frontend/src/components/FormField.css:19-40`）のマークアップ。`<label htmlFor>` と金型 AsyncCombobox（`frontend/src/components/AsyncCombobox.tsx:25-48`）をつなぐ。
   - 候補は既存の `searchProductOptions`（`frontend/src/features/tcg-analysis-review/reviewActions.ts:56-59`）で探す。
   - 入力欄の下の補助文に、今の商品を出す。値は `item.system.product_title` で、無ければ「—」（前例 `frontend/src/features/tcg-analysis-review/ReviewRowActions.tsx:87`）。
   - AsyncCombobox の文字（ariaLabel / placeholder / noResultsText / loadingText / errorText）は、`frontend/src/features/tcg-analysis-review/ReviewRowActions.tsx:86-95` が使う `needsReview.inline.*` のキーをそのまま使う。新しいキーは作らない。
   - 金型 Button（primary）「この商品に付け替える」。候補を選ぶまでは押せない。保存中は `loading`。
   - 保存は既存の `postProductCorrection(item, productUuid)`（`frontend/src/features/tcg-analysis-review/reviewActions.ts:30-38`）を使う。成功したら Callout（info）「付け替えました」を出し、`onRefresh()` を呼ぶ。失敗したら Callout（warning）を出す。ack の流れ（`ReviewItemDrawer.tsx:47-61`）と同じ型にする。
2. **状態**: ConditionReviewPanel に任意の props `label?: string` を足し、ReviewItemDrawer だけがそれを渡す。
   - `label` があるときは、金型 Select の `label` prop（`frontend/src/components/Select.tsx:21-28`）を使い、今の `aria-label`（`frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx:81`）は外す（読み上げが二重になるため）。
   - `label` が無いときは今のまま。これで SupplierDetailView（`frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:117`）の見た目は変わらない（審査 REVISE #6）。
   - 表示されない件（`condition_review` が無い）は、今と同じく何も出さない。
3. **商品マスタの登録・その他**: 既存の「修正する」ボタンは残す。新規登録・除外・検索キーワードは pmd-drawer にしか無いため。置き場所はフォームの下にし、補助文（新キー「商品マスタへの登録や除外はこちら」）を付ける。ProductMasterDrawer の中身は触らない（`docs/handoff/review-inline-edit/design.md` で別の課題とされている）。
4. **確認が必要な理由・このままで良い**: 今のまま。
5. 1〜3 は、金型 Card などの枠を新しく作らず、`Stack gap="3"` で縦に並べる。`.comp-field` の `margin-bottom` と Stack の gap が二重になる場合（recon §2 #5）は、`.review-item-fix` の下だけで `margin-bottom:0` にし、実測で確かめる。

### 新しい i18n キー（ja / en。ADR-027）

| キー | ja | en |
|---|---|---|
| reviewItem.compareHeading | 比較 | Comparison |
| reviewItem.productLabel | 商品 | Product |
| reviewItem.productCurrent | 今の商品: {{name}} | Current: {{name}} |
| reviewItem.reassign | この商品に付け替える | Reassign to this product |
| reviewItem.reassigned | 付け替えました | Reassigned |
| reviewItem.reassignFailed | 付け替えに失敗しました | Failed to reassign |
| reviewItem.conditionLabel | 状態 | Condition |
| reviewItem.masterHint | 商品マスタへの登録や除外はこちら | Register or exclude in the product master |

## 3. 対象と対象外

- 触るファイル（予定）:
  - `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`
  - `frontend/src/features/tcg-analysis-review/review-item-drawer.css`
  - `frontend/src/features/tcg-analysis-review/ItemComparison.tsx`
  - `frontend/src/features/tcg-analysis-review/item-comparison-readonly.css`
  - 新しく作る: ReviewProductFixForm.tsx と、その test
  - ConditionReviewPanel.tsx（任意の label props の追加だけ）と、その test
  - `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
  - ReviewItemDrawer の test と stories（バッジ有り・長い原文の story を追加）
  - 本 design.md と recon.md
- 対象外:
  - backend
  - API の新設
  - 商品名・数量・価格・単位・メモの保存
  - ProductMasterDrawer の中身
  - V102PostEditModal の見た目
  - shadow-source-pane.css の素の宣言（上書きは Drawer の下だけ）
  - L12-15 の line-jump ボタンの枠
  - 「要確認」バッジの重なり（別件）

## 4. 代替案と選択理由

- 左の本文に固定の高さ（例 360px）を付けて、右の高さに近づける案 → 右の高さはバッジの数・表の行の高さで変わるので、ずれが0にならない。不採用。
- 右の表を左の高さに伸ばす案 → 表の行の高さが伸び、ADR で決めた行の高さ 32px（`frontend/src/tokens.css:523`）が崩れる。不採用。
- 「直す」欄を ItemComparison の readOnly=false 版（死んだ経路。保存は disabled のまま固定、生の input あり）で復活させる案 → PO が「保存できる項目だけ」を選んだことと合わない。生の input も ADR-144 に反する。不採用。

## 5. 外部・過去事例の参照と我々への応用

- 事例1: PO 提供のお手本比較表（~/CC報告ファイル-keep/design-references/rules-from-po-samples.md、2026-10-13 共有）。「比べる項目が水平にそろう」「行の高さが一定」。→ 応用: 左右の見出し行を同じ高さにし、枠の上端と下端を 0px でそろえる。
- 事例2: 当リポジトリの前便 `docs/handoff/review-compare-table/design.md`（#4237、2026-10-13 本番反映）。部品固有トークンと実測の png で検証した。→ 応用: 同じ実測の型（getBoundingClientRect を 1440/1024 で測る）を使う。
- 外部の数値事例は使わない。今回は位置合わせとフォーム化で、成功は実測の px と画面で直接判定できるため、外部の数値は根拠として要らない。

## 6. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| A1 左右の枠の上端の差 ≤1px（バッジ有り・無しの両 story） | Playwright で Storybook を 1440px で開き、`.review-item-top .shadow-source-pane` と `.review-item-top .comp-table` の getBoundingClientRect().top を比べる。生出力は ~/CC報告ファイル-keep/review-page-20261013/align-form-measure.txt |
| A2 下端の差 ≤1px（短い原文・長い原文の両 story） | 同上。bottom を比べる |
| A3 バッジ有り・無しのどちらでも A1/A2 が成り立つ | 上の2行の実測を、バッジ有りとバッジ無しの両方の story で行う |
| A5 狭い幅（1024px）で縦に積んでも、はみ出し・重なりがない | 同上の 1024px で png を撮って目視し、scrollWidth ≤ clientWidth を確かめる |
| A6 V102PostEditModal に影響しない | PR で `git diff main...HEAD -- frontend/src/features/tcg-analysis-review/shadow-source-pane.css` の結果が空であることと、新しく足した CSS のセレクタがすべて `.review-item-top` または `.review-item-pane-head` で始まることを、grep の生出力で示す |
| B1 「商品」ラベル・入力欄・付け替えボタンが表示される | ReviewProductFixForm の vitest（label のテキストと、ボタンが押せない初期状態） |
| B3 付け替えで postProductCorrection が呼ばれ、成功の Callout と onRefresh が出る | vitest（reviewActions を mock して、呼び出し引数を確かめる） |
| B2 状態 Select にラベルが付く | ConditionReviewPanel.test.tsx に label の検査を追加 |
| i18n: 新キーが ja/en の両方にある | 既存の CI の i18n チェックと `npm run lint` |
| 金型・トークン: 生の input/select と色の直値が無い | 既存の CI（ADR-144 の lint・ADR-067 の stylelint） |
| 既存の試験が通る | `npm test -- tcg-analysis-review` と CI 全件 |

## 7. リスクと対処

- position:absolute で左の枠が見出し行に重なる → inset の上の値を `calc(var(--space-3) + var(--review-pane-head-h))`（§2-A-3）にして、実測 A1 で確かめる。
- バッジが多くて見出し行からはみ出す → nowrap と overflow:hidden にする。バッジの最大数（今は理由コード由来で3種）を story で確かめる。
- SupplierDetailView の比較表が変わる → props は任意にし、渡さないときは今の DOM のままにする。既存の試験とその story で確かめる。

## 8. 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 変更前の実測（1440/1024、バッジ有り・無し、原文の長短）を保存 | Generator（Sonnet） |
| 2 | A の実装と、story 2本の追加 | Generator |
| 3 | B の実装と試験 | Generator |
| 4 | 変更後の実測と png、vitest・lint・型検査 | Generator |
| 5 | コード審査 | Reviewer（Fable） |
| 6 | PR・GO・マージ・反映確認 | Opus |

## 9. 戻し方・測り方・維持

- 戻し方: PR を revert する（DB と API の変更は無い）。
- 測り方: §6 の実測スクリプトの生出力と png。
- 守り手: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`（見出し行と、フォームが出ていること）／見た目の位置は人手で守る（自動の位置検査は jsdom ではできないため）。
- 未解決ゼロ確認: recon §2 の #1・#2 は実装前の実測（ステップ1）で解消する。#3 は PO の決定で解消済み（保存できる項目だけ）。#4 は対象外（ProductMasterDrawer を触らない）。#5 はステップ4で確かめる。#6 は該当なし（Drawer の中の配置を定める ADR は見つからなかった。recon §1-5）。#7・#8 は Generator がステップ1で grep して報告する。
