# 実装カード 段階3 便5 — components と残りのボタンを「丸＋元の言葉」へ（40 か所以下）

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」、便3 着手 2026-10-25「1」、便4 着手 2026-10-25「1」、便5 着手 2026-10-25「1」
- 起点: 最新の origin/main（便4 #4734 合流 43e8e3ab1 を含む）。ブランチ `release/loading-button-bin5`
- 根拠: /tmp/CC報告ファイル/loading-button-recon/targets.cjs・targets.tsv（調査時点）、design.md 段階3、card-8〜card-11
- 対象ADR: ADR-144・ADR-067・ADR-027・ADR-069

## 1. 対象の決め方（実物で決める）
1. 最新 worktree で /tmp/CC報告ファイル/loading-button-recon/targets.cjs を再実行し、今の対象一覧を作る（生出力を impl/targets-now.tsv）。スクリプトが動かない・列が targets.tsv と違う → BLOCKED:
2. 便4 までに外した行（card-10 §2 の 5 行・card-11 §2 の 8 行）と、tag が生 button の行を除く（便6 で扱う）
3. 並べ順: まず `frontend/src/components/` 全部、次に pages/・features/ 以外の残りのディレクトリ（辞書順）。pages/・features/ に残りが出たらそれも含める（行番号と理由を報告）。ディレクトリ単位で足していき、合計が 40 を超える手前のディレクトリまでを対象にする（ディレクトリを途中で切らない）。全部で 40 以下なら全部
4. 決めた一覧を impl/bin5-targets.tsv に保存し、PR 本文と card-12.md の §2 に「ファイル:行」で書き写す

## 2. 置き換えの規則（card-9 と同じ）
- 規則1: `{X ? t(L) : t(O)}` → 要素に `loading={X}`、中身は `{t(O)}`
- 規則2: `{t(X ? L : O)}` → `loading={X}`、`{t(O)}`（テンプレート文字列のキーも同じ）
- X は元の式をそのまま使う。disabled は消さない
- 次のどれかに当たる行は直さずに対象から外し、理由を付けて一覧で報告する（全体は止めない）: 要素に既に loading がある／HeaderButton が variant="icon"／上の2形に当てはまらない（入れ子の三項など）

## 2-1. 対象一覧（実物で決めた 8 行。調査: 2026-10-25、起点 origin/main 0bf518e0d）
- 方法: targets.cjs を再実行（25 行 = components 12・features 8・pages 5）→ components/ 12 行から下の外した行（4 行）を除く。pages 5 行・features 8 行は便3・便4 で外した行（card-10 §2・card-11 §2）と同じ行で、新しく出た行は無い。8 行（40 以下）
  - frontend/src/components/CommissionPanel.tsx:269
  - frontend/src/components/ContactChannelForm.tsx:304
  - frontend/src/components/MergeCompanyModal.tsx:331
  - frontend/src/components/MergeContactModal.tsx:327
  - frontend/src/components/MergeLeadModal.tsx:318
  - frontend/src/components/PriorityScoreOverride.tsx:111
  - frontend/src/components/PurchaseDetailPanel.tsx:281
  - frontend/src/components/ShippingDetailPanel.tsx:354
- 外した行（components）:
  - 生 button（便6）: components/GoogleCalendarStatusBar.tsx:144
  - 入れ子の三項 `saving ? t("common.saving") : existing ? t("common.update") : t("common.register")`: components/OrderFinancialPanel.tsx:294・components/PurchaseDetailPanel.tsx:298・components/ShippingDetailPanel.tsx:371
- 押せなくなる行（disabled に X が入っていない行）: なし（8 行とも disabled に X が入っている）
- 便3・便4 で外した pages/features の行（生 button・入れ子の三項・文字列三項）は引き続き対象外で、新しい行は出なかった

## 3. 押せる・押せないの変化
- disabled に X が入っていない行は、直すと読み込み中に押せなくなる（design.md 段階3 の弊害として承認済み）。直してよいが、該当行を一覧で報告する

## 4. 試験
- 変更するファイルを描く試験を、置き場所に関係なく `frontend/src` 全体から探す（import している試験・`*ButtonMigration.test.tsx` など）。見つけた試験ファイルの一覧を impl/tests-found.txt に保存し、全部を実行する（便3 で src/components の移行試験を見落とした教訓）
- 最後に `npx vitest run -c vitest.unit.config.ts` を全体で1回回し、落ちたファイルは単独・`--testTimeout=30000` で再実行して両方の生出力を残す
- 対象の画面の試験が、ボタンの中の読み込み中の言葉を期待して落ちた場合は、期待を「元の言葉のまま・そのボタンが aria-busy="true"」に直してよい。直した試験はファイル:行と前後を報告する
- それ以外の理由で落ちた試験は直さない。単独・`--testTimeout=30000` で再実行して通れば負荷とみなし両方の生出力を残す。それでも落ちれば BLOCKED:

## 5. 触らない範囲
- 対象外の行（便6 以降の対象）、生 `<button>`、辞書（使われなくなるキーも消さない）、CSS、scripts/、金型
- 対象ファイルにもともとある lint 警告で止まったら直さず BLOCKED:

## 6. 文書
- 本カード（§2 の一覧を埋めたもの）を docs/handoff/loading-indicator/card-12.md として同じ PR に入れる。design.md 段階3 の 3-3 の便4の行の下に「便5（card-12）= components と残り N か所。」と1行足す
- 台帳 .claude-pipeline/active-work.d/release-loading-button-bin5.md（便4 と同じ形）

## 7. 検証（生出力を /tmp/CC報告ファイル/loading-button-bin5/impl/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象が消える | targets.cjs を再実行し、bin5-targets.tsv の行（外した行を除く）が 0 件 |
| 丸＋元の言葉 | tests-found.txt の試験と全体の unit 試験が pass（§4 の再実行を含む） |
| 型・lint・i18n・UI | tsc 0・eslint（変更ファイル --max-warnings=0）0・check-i18n-missing-keys.js exit 0・scripts/check-ui-governance.js exit 0（BASE_SHA/HEAD_SHA 指定） |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象ファイル＋直した試験＋§6 の文書・台帳だけ |

## 8. 想定分岐
- 行がずれた → 文面が一致すれば進め、新旧の行を報告
- schema.d.ts が無い → `npm run generate:api-types` を先に
- 対象が 40 を超える1ディレクトリだけになる → そのディレクトリだけで止めず NEEDS_DECISION:
- 金型そのもの（components/ui 等で Button・Spinner・LoadingBlock を定義するファイル）に当たった → 直さず外して報告
