# AY-2x 受入結果（配信先フォームの text 入力3件を TextFieldControl へ、金型に invalid を追加）

- 基準: 0fd56307e（origin/main）。設計: docs/handoff/ay2x-dist-form-invalid/design.md §6〜§7。
- 実測の生出力: /tmp/CC報告ファイル/ssot-ay2x/impl/measure-before/・measure-after/（JSON・スクショ、8条件 = 幅390/1280 × ja/en × ライト/ダーク）。要約 JSON は docs/handoff/design-system-recon/evidence-20260910/ay2x-measure-before.json と ay2x-measure-after.json。
- 実測方法: 一時 spec（frontend/tests-e2e/ay2x-measure.spec.ts、コミットせず /tmp/CC報告ファイル/ssot-ay2x/impl/ay2x-measure.spec.ts へ退避）。Chromium、vite dev（port 5199、E2E 用ダミー Firebase env）、installAuthBypass + mockApi。ログ: pw-before.txt、pw-after.txt（各 8 件 pass）。
- mock: GET /me/permissions（is_super_admin: true、frontend/src/hooks/useSuperAdmin.ts）、/staff/me、/tcg/distribution/targets（空）、/tcg/distribution/preview、/conversations、/conversations/stream。新規ボタンでドロワーを開き、通常 → 各欄 focus（600ms 待ってから測定）→ 空のまま保存（エラー）→ 1欄に入力、の順に測定。
- 注: 変更後の最初の2回の実測は、border-color・box-shadow の transition の途中値を拾ったため、待ち（600ms）を入れて取り直した（生出力 measure-after-run1〜run3 は残してある。採用は最終の measure-after）。変更前は transition が無く、待ち無しで測定済み。

## 受入表

| 基準 | 結果 | 数値・根拠 | 生出力 |
|---|---|---|---|
| 3欄が金型の class を持つ | ○ | 8条件すべてで3欄の class が `dist-input` → `comp-field__input`。試験 DistributionTargetForm.test.tsx「renders the 3 text inputs…」pass | measure-after.json、vitest |
| 空で保存すると3欄が赤枠（--danger）、入力すると外れる | ○ | エラー状態で3欄とも `comp-field__input comp-field__input--invalid`、border-color はライト rgb(229, 62, 62)（--danger）・ダーク rgb(248, 113, 113)。「名前」に入力後は name の invalid class が外れ、他2欄は残る（8条件とも） | measure-after.json の error・afterTyping |
| DOM 属性が class 以外で同じ、invalid 属性が出ない（B2） | ○ | 8条件 × 3状態 × 3欄で id・type・value・placeholder・autocomplete・spellcheck の差分 0。`invalid` 属性 0 | compare.txt |
| ほかの画面の class が変わらない（B3） | ○ | TextField.test.tsx の既存試験は全件そのまま pass。追加試験 §5-2（invalid 未指定は comp-field__input--invalid なし）pass。変更は invalid 指定時のみ class を足す（frontend/src/components/TextField.tsx:48） | q-vitest-targeted.txt |
| 既存試験が変わらない・落ちない（B4） | ○ | TextField.test.tsx と tcg-distribution の2ファイル 37 passed（追加 5 件を含む。TextField.test.tsx の追加 3、DistributionTargetForm.test.tsx 2） | q-vitest-targeted.txt |
| 横 overflow が増えない（B1） | ○ | ドロワー本体（dist-drawer-body）の scrollWidth − clientWidth は通常・エラーとも全条件で前後とも 0（下の表） | compare.txt |
| ハードコード文字列・直値の色がない（B5） | ○ | lint exit 0、check:all exit 0（stylelint 含む。新しい disable コメントなし）、check:new-tokens exit 0、check-ui-governance exit 0 | q-lint.txt、q-check-all.txt、q-check-new-tokens.txt、q-ui-governance.txt |
| 型・ビルド | ○ | tsc exit 0、build exit 0、build-storybook exit 0 | q-tsc.txt、q-build.txt、q-build-storybook.txt |
| test:coverage | 一部 ×（無関係の timeout） | exit 1。失敗 4 件はすべて 5000ms 級の timeout で、変更したファイルと無関係（StaffFormButtonMigration.test.tsx 2、InventoryPage.settings.test.tsx 1、ManagementCenterPage.test.tsx 1）。同 3 ファイルの単独再実行は 41 passed（exit 0） | q-test-coverage.txt、q-rerun-unrelated.txt |
| 本番 | 未実施（merge 後に Opus が確認） | 本番 CSS に `.comp-field__input.comp-field__input--invalid` があり `.dist-input{` が 0 件、app と api/health が 200 | - |

## computed style の前後表（先頭の欄 = クライアント名。before → after）

| 条件 | 状態 | font-size | height | min-height | padding | border-color | その他 |
|---|---|---|---|---|---|---|---|
| 1280-en-dark | normal | 13.6px → 14.4px | 39.75px → 39.6094px | auto → auto | 8px 12px → 8px 12px | rgb(51, 65, 85) → rgb(51, 65, 85) | 6px → 6px |
| 1280-en-dark | error | 13.6px → 14.4px | 39.75px → 39.6094px | auto → auto | 8px 12px → 8px 12px | rgb(248, 113, 113) → rgb(248, 113, 113) | 6px → 6px |
| 1280-en-dark | focus | 13.6px → 14.4px | 39.75px → 39.6094px | - | - | rgb(91, 141, 217) → rgb(91, 141, 217) | outline `solid 2px` → `none 3px`、box-shadow `none` → `rgba(91, 141, 217, 0.3) 0px 0px 0px 3px` |
| 1280-en-light | normal | 13.6px → 14.4px | 39.75px → 39.6094px | auto → auto | 8px 12px → 8px 12px | rgb(226, 232, 240) → rgb(226, 232, 240) | 6px → 6px |
| 1280-en-light | error | 13.6px → 14.4px | 39.75px → 39.6094px | auto → auto | 8px 12px → 8px 12px | rgb(185, 28, 28) → rgb(229, 62, 62) | 6px → 6px |
| 1280-en-light | focus | 13.6px → 14.4px | 39.75px → 39.6094px | - | - | rgb(30, 58, 138) → rgb(30, 58, 138) | outline `solid 2px` → `none 3px`、box-shadow `none` → `rgba(30, 58, 138, 0.15) 0px 0px 0px 3px` |
| 1280-ja-dark | normal | 13.6px → 14.4px | 39.75px → 39.6094px | auto → auto | 8px 12px → 8px 12px | rgb(51, 65, 85) → rgb(51, 65, 85) | 6px → 6px |
| 1280-ja-dark | error | 13.6px → 14.4px | 39.75px → 39.6094px | auto → auto | 8px 12px → 8px 12px | rgb(248, 113, 113) → rgb(248, 113, 113) | 6px → 6px |
| 1280-ja-dark | focus | 13.6px → 14.4px | 39.75px → 39.6094px | - | - | rgb(91, 141, 217) → rgb(91, 141, 217) | outline `solid 2px` → `none 3px`、box-shadow `none` → `rgba(91, 141, 217, 0.3) 0px 0px 0px 3px` |
| 1280-ja-light | normal | 13.6px → 14.4px | 39.75px → 39.6094px | auto → auto | 8px 12px → 8px 12px | rgb(226, 232, 240) → rgb(226, 232, 240) | 6px → 6px |
| 1280-ja-light | error | 13.6px → 14.4px | 39.75px → 39.6094px | auto → auto | 8px 12px → 8px 12px | rgb(185, 28, 28) → rgb(229, 62, 62) | 6px → 6px |
| 1280-ja-light | focus | 13.6px → 14.4px | 39.75px → 39.6094px | - | - | rgb(30, 58, 138) → rgb(30, 58, 138) | outline `solid 2px` → `none 3px`、box-shadow `none` → `rgba(30, 58, 138, 0.15) 0px 0px 0px 3px` |
| 390-en-dark | normal | 13.6px → 14.4px | 39.75px → 44px | auto → 44px | 8px 12px → 8px 12px | rgb(51, 65, 85) → rgb(51, 65, 85) | 6px → 6px |
| 390-en-dark | error | 13.6px → 14.4px | 39.75px → 44px | auto → 44px | 8px 12px → 8px 12px | rgb(248, 113, 113) → rgb(248, 113, 113) | 6px → 6px |
| 390-en-dark | focus | 13.6px → 14.4px | 39.75px → 44px | - | - | rgb(91, 141, 217) → rgb(91, 141, 217) | outline `solid 2px` → `none 3px`、box-shadow `none` → `rgba(91, 141, 217, 0.3) 0px 0px 0px 3px` |
| 390-en-light | normal | 13.6px → 14.4px | 39.75px → 44px | auto → 44px | 8px 12px → 8px 12px | rgb(226, 232, 240) → rgb(226, 232, 240) | 6px → 6px |
| 390-en-light | error | 13.6px → 14.4px | 39.75px → 44px | auto → 44px | 8px 12px → 8px 12px | rgb(185, 28, 28) → rgb(229, 62, 62) | 6px → 6px |
| 390-en-light | focus | 13.6px → 14.4px | 39.75px → 44px | - | - | rgb(30, 58, 138) → rgb(30, 58, 138) | outline `solid 2px` → `none 3px`、box-shadow `none` → `rgba(30, 58, 138, 0.15) 0px 0px 0px 3px` |
| 390-ja-dark | normal | 13.6px → 14.4px | 39.75px → 44px | auto → 44px | 8px 12px → 8px 12px | rgb(51, 65, 85) → rgb(51, 65, 85) | 6px → 6px |
| 390-ja-dark | error | 13.6px → 14.4px | 39.75px → 44px | auto → 44px | 8px 12px → 8px 12px | rgb(248, 113, 113) → rgb(248, 113, 113) | 6px → 6px |
| 390-ja-dark | focus | 13.6px → 14.4px | 39.75px → 44px | - | - | rgb(91, 141, 217) → rgb(91, 141, 217) | outline `solid 2px` → `none 3px`、box-shadow `none` → `rgba(91, 141, 217, 0.3) 0px 0px 0px 3px` |
| 390-ja-light | normal | 13.6px → 14.4px | 39.75px → 44px | auto → 44px | 8px 12px → 8px 12px | rgb(226, 232, 240) → rgb(226, 232, 240) | 6px → 6px |
| 390-ja-light | error | 13.6px → 14.4px | 39.75px → 44px | auto → 44px | 8px 12px → 8px 12px | rgb(185, 28, 28) → rgb(229, 62, 62) | 6px → 6px |
| 390-ja-light | focus | 13.6px → 14.4px | 39.75px → 44px | - | - | rgb(30, 58, 138) → rgb(30, 58, 138) | outline `solid 2px` → `none 3px`、box-shadow `none` → `rgba(30, 58, 138, 0.15) 0px 0px 0px 3px` |

- クラス: 変更前 `dist-input`（エラー時 `dist-input dist-input--error`）→ 変更後 `comp-field__input`（エラー時 `comp-field__input comp-field__input--invalid`）。
- 390px は高さが 44px（FormField.css のモバイル最小高）。1280px は 39.75px → 39.61px。
- エラー枠: ライトは #b91c1c（rgb(185, 28, 28)、--color-error）→ --danger（rgb(229, 62, 62)）。ダークは前後とも rgb(248, 113, 113)。
- focus: 変更前は outline 2px solid、変更後は outline なし + box-shadow 3px のリング（--focus-ring-shadow）。

## B1 表（ドロワー本体の横 overflow）

| 条件 | dist-drawer-body scrollWidth/clientWidth（通常、前 → 後） | scrollWidth − clientWidth（エラー、前 → 後） | document scrollWidth（前 → 後） |
|---|---|---|---|
| 1280-en-dark | 479/479 → 479/479 | 0 → 0 | 1280 → 1280 |
| 1280-en-light | 479/479 → 479/479 | 0 → 0 | 1280 → 1280 |
| 1280-ja-dark | 479/479 → 479/479 | 0 → 0 | 1280 → 1280 |
| 1280-ja-light | 479/479 → 479/479 | 0 → 0 | 1280 → 1280 |
| 390-en-dark | 389/389 → 389/389 | 0 → 0 | 390 → 390 |
| 390-en-light | 389/389 → 389/389 | 0 → 0 | 390 → 390 |
| 390-ja-dark | 389/389 → 389/389 | 0 → 0 | 390 → 390 |
| 390-ja-light | 389/389 → 389/389 | 0 → 0 | 390 → 390 |
