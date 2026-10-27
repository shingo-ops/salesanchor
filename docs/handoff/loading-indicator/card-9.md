# 実装カード 段階3 便2 — pages/super-admin と pages/integrations のボタン 34 か所を「丸＋元の言葉」へ

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」、便2 着手 2026-10-25「2」（目で確かめずに2回目へ）
- 起点: 最新の origin/main（便1 #4709 合流 69721d365 を含む）。ブランチ `release/loading-button-bin2`
- 根拠: /tmp/CC報告ファイル/loading-button-recon/bin2-targets.tsv（34 行・行番号は 50d7f52da 時点）・targets.tsv、design.md 段階3、card-8.md
- 対象ADR: ADR-144・ADR-067・ADR-027・ADR-069

## 1. 置き換えの規則（読み込み中の言葉を外し、loading に条件を渡す）
- 規則1: `{X ? t(L) : t(O)}` → 要素に `loading={X}`、中身は `{t(O)}`
- 規則2: `{t(X ? L : O)}` → `loading={X}`、`{t(O)}`（テンプレート文字列のキーも同じ。例 `` t(X ? `${f}.exporting` : `${f}.export`) `` → `` {t(`${f}.export`)} ``）
- X は元の式をそのまま使う（例 `saving[key]`、`uploadBusy.letterhead`）。括弧で包む必要があれば包む
- disabled は消さず、そのまま残す（Button が disabled||loading で重ねる）
- 要素に既に loading がある、HeaderButton が variant="icon"、上の2形に当てはまらない、のどれかなら止まって BLOCKED:

## 2. 対象 34 か所（23 ファイル）
- pages/integrations（12）: CarrierCredentialForm:148、CarrierIntegrationPage:276、FedexEtdSetupGuide:523・552、FedexLabelValidationTab:261・366・382、GoogleDriveIntegrationPage:133・176、PaypalIntegrationPage:187・202・226
- pages/super-admin（22）: ConditionImportPage:96・120、ExtractionPromptConfigTab:235、FxRatePage:103、NoteMasterImportPage:96・120、ProductCategoriesImportPage:102・126、StatusMasterImportPage:96・120、SupplierImportPage:96・120、TcgLineImportPage:415、UnitImportPage:96・120、ViewerTemplatesPage:239、components/ConditionsMasterPanel:273・NoteMasterPanel:211・ProductMasterPanel:96・RuleManagementPanel:192・SupplierMasterPanel:249・UnitMasterPanel:225
- 34 か所とも disabled に読み込み中の変数が入っている（bin2-targets.tsv 3列目）。押せる・押せないの変化はない。実物で違っていたら報告する

## 3. 試験
- 対象の画面の試験が、ボタンの中の読み込み中の言葉（例「読み込み中」「保存中」）を期待して落ちた場合は、期待を「元の言葉のまま・そのボタンが aria-busy="true"」に直してよい。直した試験はファイル:行と前後を報告する
- それ以外の理由で落ちた試験は直さず BLOCKED:

## 4. 触らない範囲
- 便3以降の対象（targets.tsv の残り）、生 `<button>`、辞書（使われなくなるキーも消さない。便7）、CSS、scripts/、金型
- 対象ファイルにもともとある lint 警告で止まったら直さず BLOCKED:

## 5. 文書
- 本カードを docs/handoff/loading-indicator/card-9.md として同じ PR に入れる。design.md 段階3 の 3-3 に「便2 = pages/super-admin 22・pages/integrations 12（card-9）」と1行足す
- 台帳 .claude-pipeline/active-work.d/release-loading-button-bin2.md（便1 release-loading-button-mold.md と同じ形）

## 6. 検証（生出力を /tmp/CC報告ファイル/loading-button-bin2/impl/ へ）
| 基準 | 検証方法 |
|---|---|
| 34 か所が消える | /tmp/CC報告ファイル/loading-button-recon/ の抽出スクリプトを対象 23 ファイルに再実行し 0 件（スクリプトが無ければ、各行の旧文面が `git grep -F` で 0 件） |
| 丸＋元の言葉 | 対象の試験が全件 pass |
| 型・lint・i18n・UI | tsc 0・eslint（変更ファイル --max-warnings=0）0・check-i18n-missing-keys.js exit 0・check-ui-governance.js exit 0 |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象 23 ファイル＋直した試験＋§5 の文書・台帳だけ |

## 7. 想定分岐
- 行がずれた → 文面が一致すれば進め、新旧の行を報告。一致しなければ止まる
- vitest が負荷で時間切れ → 単独・`--testTimeout=30000` で切り分け、両方の生出力を残す
- schema.d.ts が無い → `npm run generate:api-types` を先に
