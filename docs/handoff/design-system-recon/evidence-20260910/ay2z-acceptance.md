# AY-2z 受入結果（商品編集ページの入力14欄を TextFieldControl の種類 product-edit へ）

- 基準: 4c9d037ef（origin/main）。設計: docs/handoff/ay2z-product-edit-inputs/design.md §5〜§7。
- 実測の生出力: /tmp/CC報告ファイル/ssot-ay2z/impl/measure-before/・measure-after/（JSON・スクショ、8条件 = 幅390/1280 × ja/en × ライト/ダーク）。要約 JSON は docs/handoff/design-system-recon/evidence-20260910/ay2z-measure-before.json と ay2z-measure-after.json。
- 実測方法: 一時 spec（frontend/tests-e2e/ay2z-measure.spec.ts、コミットせず /tmp/CC報告ファイル/ssot-ay2z/impl/ay2z-measure.spec.ts に保存）。Chromium、vite dev、installAuthBypass + mockApi（product-edit-tcg-type.spec.ts の mock に release_date・unit_price の値を入れた状態）。route は /admin/products/123/edit。
- 測った要素: ページ内の button 1 + input 14 + select 9 + textarea 1（計25）を、通常・focus（600ms 待つ）・hover の3状態で。取った値: font-family、font-size、line-height、height、width、min-height、padding 4辺、border 4辺、border-radius、background-color、color、outline、box-shadow、transition、box-sizing、rect、class 以外の DOM 属性、親要素の tag と class。
- ログ: pw-before.txt、pw-after.txt（各 8 件 pass）。機械比較: compare.txt。

## 受入表

| 基準 | 結果 | 数値・根拠 |
|---|---|---|
| 14欄が種類 product-edit を持つ | ○ | 新規試験 ProductEditPage.inputs.test.tsx pass（14欄すべて class が `comp-field__input comp-input--product-edit`、select 9・textarea 1 は金型 class なし） |
| 見た目が変わらない（B1） | ○ | 8条件 × 3状態 × 25要素 = 600 組で、computed style 21 項目と rect の差 0 |
| DOM 属性が class 以外で同じ・ラッパー増なし（B2） | ○ | 600 組で attrs・tag・親 tag・親 class の差 0 |
| select・textarea・ボタンが変わらない（B3） | ○ | 同じ 600 組に含む。差 0 |
| 既存試験が書き換えなしで通る（B5） | ○ | TextField.test.tsx・CommerceSubmitButtonMigration.test.tsx・CommerceNavigationButtonMigration.test.tsx は無修正で pass（TextField.test.tsx は VARIANTS に product-edit を足しただけ） |
| 新しい色・数値なし、直書きなし（B4・B6） | ○ | checks.txt 参照 |
| 本番 | 未実施（merge 後に Opus が確認） | 本番 CSS に `.comp-field__input.comp-input--product-edit` があり、`.product-edit-form .form-group input:not(` が 0 件 |

## 記録した値（変更前 = 変更後）

- date 欄（ProductEditPage.tsx の type="date"）の font-family は monospace。それ以外の input 13 と select・textarea は Arial。どちらも前後で同じ。
- line-height は normal、min-height は 0px（auto の computed 値）、transition は all（ブラウザ既定の値）で、前後同じ。
- 1280・ja・ライト、通常: font-size 14.4px、border 1px solid rgb(203, 213, 224)、border-radius 4px。focus: box-shadow rgba(30, 58, 138, 0.15) 0px 0px 0px 3px、枠色は通常と同じ。390・ja・ダークの通常: border 1px solid rgb(71, 85, 105)、height 34px（モバイルの 44px にならない）。
