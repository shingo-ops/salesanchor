# AY-5 前後実測 祖先の写し方（ay5-render.tsx）

前 = origin/main b6435490b の JSX（ファイルは `git show origin/main:<path>` で確認。行番号は origin/main 側）。後 = 本物の Radio / RadioControl。
CSS: 前 = origin/main の `vite build`（`/tmp/CC報告ファイル/ssot-radio/measure/before-out/assets/index-CNnO6Pwh.css`）、後 = 作業場所の `vite build`（同 `after-out/assets/index-tDC17Ice.css`）。どちらも CSS は 1 ファイルのみ。

## R1（RegisterPage）frontend/src/pages/register/RegisterPage.tsx
祖先の class・style の並び（外 → 内）:
1. `:278-279` div.page-container style=`maxWidth:600px; margin:0 auto; padding:var(--spacing-6)`（これを data-sample にした）
2. `:295` form
3. `:297` fieldset style=`border:1px solid var(--border-default); borderRadius:var(--radius-md); padding:var(--spacing-4); marginBottom:var(--spacing-4)`、`:298` legend style=`fontWeight:var(--font-weight-bold)`
4. div style=`display:flex; flexDirection:column; gap:var(--spacing-3)`（Section 1 の中身を包む div。`:301` 付近）
5. 配送先の質問 div style=`marginTop:var(--spacing-3)`（前 `:452` 付近「12. Shipping question」）
6. p style=`fontWeight:var(--font-weight-bold); marginBottom:var(--spacing-2)`＋requiredMark(span)
7. 前: label×2（前 `:456-475`、1つ目 style=`display:flex; alignItems:center; gap:var(--spacing-2); cursor:pointer`、2つ目は同じ＋`marginTop:var(--spacing-1)`）> input[type=radio]。
   後: div×2 > Radio（作業場所 `:456-475`）。
- 省いたもの: 他の項目（1〜11）、言語切替ボタン、h1。文言は ja.json の registration.shippingQuestion・proceedToRegister・shipToSameAddress・section1Title。
- `--spacing-*` は未定義のまま写している（実測で gap=normal・marginTop=0px を確認）。

## R3・R4（RolesPage）frontend/src/pages/roles/RolesPage.tsx
祖先（外 → 内）:
1. `:451-457` Modal（size=md）の中身 = div.comp-modal-dialog.comp-modal-dialog--md > div.comp-modal-header(h2.comp-modal-title) + div.comp-modal-body（frontend/src/components/Modal.tsx:120-144 の構造。オーバーレイ（position:fixed の暗幕）は省略し、dialog に margin:16px。dialog を data-sample にした）
2. `:457` form
3. `:461` div.form-group > label（「色」）
4. `:462` div.color-picker[role=radiogroup]
5. `:466-472`（legacy）label.color-swatch.selected.color-swatch-legacy style=background、title > input[type=radio] name=role-color checked readOnly
6. `:482-491`（パレット）label.color-swatch(+selected) style=background、title > input[type=radio] name=role-color checked/onChange
- 状態 unchecked = legacy 1 つ（選択・readOnly、R3）＋パレット 2 つ（未選択）。状態 checked = legacy なし・パレット 3 つの 1 つ目が選択（R4）。実画面では legacy があるときパレットは選択されないので、2 つの実在の形を unchecked / checked の名前で測っている。
- CSS の規則: frontend/src/pages-layout.css:304-345（.color-picker / .color-swatch / .color-swatch input[type="radio"]）、frontend/src/components.css:19（.form-group input[type="radio"]）。

## R5（MergeCompanyModal）frontend/src/components/MergeCompanyModal.tsx
祖先（外 → 内）:
1. `:146` Modal size=md（R3 と同じ dialog 構造。オーバーレイ省略）
2. `:147` div.modal-content-wide
3. `:181-189` div style=`maxHeight:var(--dropdown-list-h); overflowY:auto; border:1px solid var(--border-light); borderRadius:var(--radius-sm); marginTop:var(--space-2)`（`:156` の div.form-row（検索欄）とは兄弟。table は form-row の中ではない）
4. `:197` table.data-table style=`marginBottom:0`、`:198-205` thead（th 先頭は width:var(--col-width-checkbox)）
5. `:206` tbody > `:208` tr style=`cursor:pointer; background: 選択行は var(--warning-bg)` > `:219` td > `:221-222` input[type=radio] name=master-candidate
- 2 行（C-0001 選択 / C-0002）。後は input だけ RadioControl（作業場所 MergeCompanyModal.tsx の同じ位置）。

## R6（MergeContactModal）・R7（MergeLeadModal）は R5 と同じ形（JSX で確認）
| 項目 | R5 Company | R6 Contact | R7 Lead |
|---|---|---|---|
| Modal size=md → div.modal-content-wide | `:146-147` | `:145-146` | `:135-136` |
| 一覧を包む div（maxHeight var(--dropdown-list-h)・overflowY auto・border・borderRadius・marginTop） | `:183` | `:181` | `:173` |
| table.data-table style marginBottom:0 | `:197` | `:195` | `:187` |
| tbody > tr（cursor:pointer・選択行 background var(--warning-bg)）| `:206-208` | `:204-206` | `:196-198` |
| td > input[type=radio] name=master-candidate | `:219-222` | `:217-221` | `:209-212` |
- 違いは、行の内容（コード・名称列と状態バッジの class）、R6 の td 内の古いコメント 1 行（:218）、一覧の候補配列名（filteredCandidates / candidates）だけで、radio の祖先の class・style は同じ。よって R6・R7 は測らず R5 の結果で代表させた。

## 測り方
- Playwright(chromium 147)・幅 1280 / 390・ライト / ダーク（html.force-dark）・場面ごとの状態: R1 と R5 は unchecked / checked / focus（Tab キーで :focus-visible を当てる）、R3・R4 は unchecked / checked。
- 手順: `node ay5-measure.cjs <前CSS> <後CSS> ay5-measure.json <画像出力先>` → `python3 ay5-compare.py ay5-measure.json > ay5-measure-compare.txt`。
