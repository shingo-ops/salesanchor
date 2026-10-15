# AY-3a 受入結果（商品編集ページの選択欄9・複数行欄1を種類 product-edit へ）

- 基準: 597a1a80d（origin/main）。設計: docs/handoff/ay3a-product-edit-select-textarea/design.md §4〜§5。
- 実測の生出力: /tmp/CC報告ファイル/ssot-ay3a/impl/measure-before/・measure-after/（JSON・スクショ、8条件 = 幅390/1280 × ja/en × ライト/ダーク）。要約 JSON は docs/handoff/design-system-recon/evidence-20260910/ay3a-measure-before.json と ay3a-measure-after.json。
- 実測方法: 一時 spec（frontend/tests-e2e/ay3a-measure.spec.ts、コミットせず /tmp/CC報告ファイル/ssot-ay3a/impl/ay3a-measure.spec.ts に保存）。比較は /tmp/CC報告ファイル/ssot-ay3a/impl/compare.mjs、出力 compare.txt。Chromium、vite dev、installAuthBypass + mockApi。route は /admin/products/123/edit。
- 測った要素: button 1 + input 14 + select 9 + textarea 1（計25）を、通常・focus（600ms 待つ）・hover の3状態で。取った値: font-family、font-size、line-height、height、width、min-height、max-width、padding 4辺、border 4辺、border-radius、background-color、color、outline、box-shadow、transition、box-sizing、appearance、-webkit-appearance、background-image、background-repeat、background-position、cursor、resize、rect、class 以外の DOM 属性、option の value・text・selected、選択値、親要素の tag と class。class 属性は別欄で記録。
- ログ: pw-before.txt、pw-after.txt（各 8 件 pass）。変更前は設計 r2 の追加項目（background-repeat・background-position）を含めて取り直した。

## 受入表

| 基準 | 結果 | 数値・根拠 |
|---|---|---|
| select 9・textarea 1 が種類 product-edit を持つ | ○ | ProductEditPage.inputs.test.tsx pass。実測 DOM の class は select が `comp-select__control comp-select__control--full comp-select--product-edit`、textarea が `comp-field__textarea comp-textarea--product-edit` |
| 見た目が変わらない（B1） | ○ | 8条件 × 3状態 × 25要素 = 600 組で、computed style と rect の差 0（compare.txt「差分(class除外): 0」） |
| DOM・選択肢が class 以外で同じ・ラッパー増なし（B2） | ○ | 600 組で attrs・option の value/text/selected・選択値・tag・親 tag・親 class の差 0 |
| input・ボタンが変わらない（B3） | ○ | 同じ 600 組に含む。差 0 |
| 既存試験が書き換えなしで通る（B5） | ○ | CommerceSubmitButtonMigration.test.tsx・CommerceNavigationButtonMigration.test.tsx は無修正で pass。Select.test.tsx・Textarea.test.tsx は VARIANTS / it.each に product-edit を足しただけ |
| 新しい色・数値なし、直書きなし（B4・B6） | ○ | /tmp/CC報告ファイル/ssot-ay3a/impl/checks.txt 参照 |
| 他ページへの影響なし（B7） | ○ | `.product-edit-form` の利用は ProductEditPage.tsx:210、company-forms.css、試験の data-testid のみ |
| 本番 | 未実施（merge 後に Opus が確認） | 本番 CSS に `.comp-select__control.comp-select--product-edit` と `.comp-field__textarea.comp-textarea--product-edit`、`.product-edit-form .form-group select` / `textarea` が 0 件 |

## 別欄: class 属性の差（設計どおりの変更）
- 変更前は select・textarea とも class なし（null）。変更後は 10 要素 × 3状態 × 8条件 = 240 件が金型の class に変わった（compare.txt 末尾）。DOM 属性（class 以外）の差は 0。

## 記録した値（変更前 = 変更後）
- 1280・ja・ライト、通常: select は font-family Arial、font-size 14.4px、height 36px、border 1px solid rgb(203, 213, 224)、border-radius 4px、max-width none、background-image none、background-repeat repeat、background-position 0% 0%、appearance auto、cursor default。textarea は font-family monospace、height 80px、min-height 80px、resize vertical、cursor text。focus: box-shadow rgba(30, 58, 138, 0.15) 0px 0px 0px 3px、枠色は通常と同じ。
- 390・ja・ダークの select: height 36px（モバイルの 44px にならない）、border 1px solid rgb(71, 85, 105)。
