# 実装カード 段階3 便4 — pages の残り（login から）と featuresのボタンを「丸＋元の言葉」へ（40 か所以下）

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」、便3 着手 2026-10-25「1」、便4 着手 2026-10-25「1」
- 起点: 最新の origin/main（便3 #4725 合流 3698f91d8 を含む）。ブランチ `release/loading-button-bin4`
- 根拠: /tmp/CC報告ファイル/loading-button-recon/targets.cjs・targets.tsv（調査時点）、design.md 段階3、card-8〜card-10
- 対象ADR: ADR-144・ADR-067・ADR-027・ADR-069

## 1. 対象の決め方（実物で決める）
1. 最新 worktree で /tmp/CC報告ファイル/loading-button-recon/targets.cjs を再実行し、今の対象一覧を作る（生出力を impl/targets-now.tsv）。スクリプトが動かない・列が targets.tsv と違う → BLOCKED:
2. 便3 までに外した行（card-10 §2 の外した 5 行と、tag が raw button の行）を除く
3. 並べ順: まず `frontend/src/pages/` の残り全部（ディレクトリ名の辞書順）、次に `frontend/src/features/` をディレクトリ名の辞書順。ディレクトリ単位で足していき、合計が 40 を超える手前のディレクトリまでを対象にする（ディレクトリを途中で切らない）。components/ は便5
4. 決めた一覧を impl/bin4-targets.tsv に保存し、PR 本文と card-11.md の §2 に「ファイル:行」で書き写す

## 2. 置き換えの規則（card-9 と同じ）
- 規則1: `{X ? t(L) : t(O)}` → 要素に `loading={X}`、中身は `{t(O)}`
- 規則2: `{t(X ? L : O)}` → `loading={X}`、`{t(O)}`（テンプレート文字列のキーも同じ）
- X は元の式をそのまま使う。disabled は消さない
- 次のどれかに当たる行は直さずに対象から外し、理由を付けて一覧で報告する（全体は止めない）: 要素に既に loading がある／HeaderButton が variant="icon"／上の2形に当てはまらない（入れ子の三項など）

## 2-1. 対象一覧（実物で決めた 34 行。調査: 2026-10-25、起点 origin/main 6a5047685）
- 方法: targets.cjs を再実行（59 行 = components 12・pages 28・features 19）→ components/ 12 行（便5）と、便3 までの対象ディレクトリ・外した行（pages 5 行）を除く。pages の残り 23 行 + features 19 行 = 42 行から下の外した行（8 行）を除くと 34 行（40 以下）
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:312
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:321
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:412
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:438
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:539
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:559
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:562
  - frontend/src/features/tcg-import-review/ReviewSection.tsx:357
  - frontend/src/features/tcg-product-import/TcgProductImportPanel.tsx:83
  - frontend/src/features/tcg-product-import/TcgProductImportPreview.tsx:40
  - frontend/src/features/tcg-review-csv/ReviewCsvPanel.tsx:84
  - frontend/src/features/tcg-review-csv/ReviewCsvPreviewTable.tsx:32
  - frontend/src/pages/login/LoginPage.tsx:124
  - frontend/src/pages/login/LoginPage.tsx:150
  - frontend/src/pages/note-master/NoteMasterImportPage.tsx:96
  - frontend/src/pages/note-master/NoteMasterImportPage.tsx:120
  - frontend/src/pages/note-master/NoteMasterPage.tsx:367
  - frontend/src/pages/product-categories/ProductCategoriesImportPage.tsx:102
  - frontend/src/pages/product-categories/ProductCategoriesImportPage.tsx:126
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:286
  - frontend/src/pages/quote-detail/QuoteDetailPage.tsx:148
  - frontend/src/pages/register/RegisterAddressPage.tsx:459
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:406
  - frontend/src/pages/register/RegisterPage.tsx:533
  - frontend/src/pages/roles/RolesPage.tsx:379
  - frontend/src/pages/staff/StaffPage.tsx:301
  - frontend/src/pages/status-master/StatusMasterImportPage.tsx:96
  - frontend/src/pages/status-master/StatusMasterImportPage.tsx:120
  - frontend/src/pages/status-master/StatusMasterPage.tsx:320
  - frontend/src/pages/suppliers/SupplierImportPage.tsx:96
  - frontend/src/pages/suppliers/SupplierImportPage.tsx:120
  - frontend/src/pages/units/UnitImportPage.tsx:96
  - frontend/src/pages/units/UnitImportPage.tsx:120
  - frontend/src/pages/units/UnitsPage.tsx:213
- 外した行:
  - 生 button（便6）: pages/admin/ChannelMastersPage.tsx:141・pages/inbox/ManualRecordSection.tsx:197・pages/inbox/OutboundTranslationPreview.tsx:178（便3 で外した行）、features/tcg-analysis-review/ItemComparison.tsx:112（2 件）・features/tcg-distribution/DistributionPreview.tsx:128・DistributionTargetForm.tsx:256・DistributionTargetList.tsx:179
  - 入れ子の三項: pages/products/ProductEditPage.tsx:189・features/supplier-master/SupplierDetailDrawer.tsx:307・features/tcg-product-import/TcgProductDetailDrawer.tsx:305
  - 便3 で外した入れ子・文字列三項: pages/admin/DiscordConfigPage.tsx:374・pages/buyback-prices/BuybackPricesPage.tsx:302

## 3. 押せる・押せないの変化
- disabled に X が入っていない行は、直すと読み込み中に押せなくなる（design.md 段階3 の弊害として承認済み）。直してよいが、該当行を一覧で報告する

## 4. 試験
- 変更するファイルを描く試験を、置き場所に関係なく `frontend/src` 全体から探す（import している試験・`*ButtonMigration.test.tsx` など）。見つけた試験ファイルの一覧を impl/tests-found.txt に保存し、全部を実行する（便3 で src/components の移行試験を見落とした教訓）
- 最後に `npx vitest run -c vitest.unit.config.ts` を全体で1回回し、落ちたファイルは単独・`--testTimeout=30000` で再実行して両方の生出力を残す
- 対象の画面の試験が、ボタンの中の読み込み中の言葉を期待して落ちた場合は、期待を「元の言葉のまま・そのボタンが aria-busy="true"」に直してよい。直した試験はファイル:行と前後を報告する
- それ以外の理由で落ちた試験は直さない。単独・`--testTimeout=30000` で再実行して通れば負荷とみなし両方の生出力を残す。それでも落ちれば BLOCKED:

## 5. 触らない範囲
- 対象外の行（components/・便5 以降の対象）、生 `<button>`、辞書（使われなくなるキーも消さない）、CSS、scripts/、金型
- 対象ファイルにもともとある lint 警告で止まったら直さず BLOCKED:

## 6. 文書
- 本カード（§2 の一覧を埋めたもの）を docs/handoff/loading-indicator/card-11.md として同じ PR に入れる。design.md 段階3 の 3-3 の便3の行の下に「便4（card-11）= pages の残りと features ほか N か所。」と1行足す
- 台帳 .claude-pipeline/active-work.d/release-loading-button-bin4.md（便3 と同じ形）

## 7. 検証（生出力を /tmp/CC報告ファイル/loading-button-bin4/impl/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象が消える | targets.cjs を再実行し、bin4-targets.tsv の行（外した行を除く）が 0 件 |
| 丸＋元の言葉 | tests-found.txt の試験と全体の unit 試験が pass（§4 の再実行を含む） |
| 型・lint・i18n・UI | tsc 0・eslint（変更ファイル --max-warnings=0）0・check-i18n-missing-keys.js exit 0・scripts/check-ui-governance.js exit 0（BASE_SHA/HEAD_SHA 指定） |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象ファイル＋直した試験＋§6 の文書・台帳だけ |

## 8. 想定分岐
- 行がずれた → 文面が一致すれば進め、新旧の行を報告
- schema.d.ts が無い → `npm run generate:api-types` を先に
- 対象が 40 を超える1ディレクトリだけになる → そのディレクトリだけで止めず NEEDS_DECISION:
