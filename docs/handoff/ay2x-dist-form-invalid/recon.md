# AY-2x recon（配信先フォームの text 入力3件と TextFieldControl の invalid）

基準: origin/main 0fd56307e。生出力: /tmp/CC報告ファイル/ssot-ay2x/recon/、/tmp/CC報告ファイル/ssot-dtf/。設計: docs/handoff/ay2x-dist-form-invalid/design.md。

## 既存 ADR の検索
- 実行: `git grep -il "TextFieldControl\|配信先" -- docs/adr` と `git grep -il "dist-input\|DistributionTargetForm" -- docs/adr` はどちらも 0 件。ADR-144（UI 部品は金型へ）、ADR-067（デザイントークン）、ADR-027（i18n）は本便の継承元（CLAUDE.md の規定）。本便は新規トークン・文言なし。

## 仕様の正
- docs/specs/design-system/design.md:815 `invalid?: boolean`｜既存のエラー条件のまま外観へ接続。aria-invalid は呼び出し側の明示属性だけを通し、自動付与・上書きしない。
- docs/specs/design-system/design.md:2369 TextFieldControl の invalid は AY-2 以降の便で設計する（本便がその一つ）。

## 金型（変更前）
- frontend/src/components/TextField.tsx:35-39 `TextFieldControlProps`（size・variant の判別共用体）。
- frontend/src/components/TextField.tsx:41-54 `TextFieldControl`（forwardRef、class 配列は comp-field__input・size 修飾・comp-input--variant・className）。
- frontend/src/components/TextField.tsx:57-103 ラベル付き `TextField`（error は外側 comp-field--error で赤枠。内部の TextFieldControl に invalid を渡さない）。
- frontend/src/components/FormField.css:47 基本 (0,1,0)、:94-95 focus (0,2,0)、:114-119 §5 エラー border (0,2,0)、:433-440 §7 エラー focus (0,3,0)（:434 に既存の stylelint-disable コメント）、:443- モバイル min-height。

## 利用側（変更前）
- frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:182-189 クライアント名、:199-208 スプレッドシートID、:223-230 タブ名。いずれも `<input` に className=`dist-input${errors.X ? " dist-input--error" : ""}`（:184・:201・:225）。
- frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:209-211 dist-field-hint、:190・:213・:232 dist-field-error、:237- checkbox。
- frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:61-72 validate（空欄とスプレッドシートID形式）、:74- handleSave（検証失敗時は API 呼び出し前に戻る）。
- frontend/src/features/tcg-distribution/distribution.css:322-332 `.dist-input`、:334-338 `.dist-input:focus`、:340-342 `.dist-input--error`。
- `git grep -n "dist-input" -- frontend/src` の件数は、変更前 HEAD で DistributionTargetForm.tsx 3 行と distribution.css 3 行の計 6 行だけ（生出力 /tmp/CC報告ファイル/ssot-ay2x/recon/dist-class-users.txt）。

## 到達経路（測定に使用）
- frontend/src/App.tsx:300 `/super-admin/tcg-distribution` → frontend/src/pages/super-admin/TcgDistributionPage.tsx（useSuperAdmin: GET /me/permissions の is_super_admin、frontend/src/hooks/useSuperAdmin.ts）→ frontend/src/features/tcg-distribution/DistributionWorkspace.tsx（新規ボタン → DistributionTargetForm）。
- 必要な API（frontend/src/features/tcg-distribution/distributionApi.ts）: GET /tcg/distribution/targets、GET /tcg/distribution/preview。

## 試験の前例
- frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx:1-14 が `i18n.changeLanguage("en")` と vi.mock の書式の前例。
- frontend/src/components/TextField.test.tsx の既存試験（完全一致）は ラベル付き TextField の出力を固定している。
