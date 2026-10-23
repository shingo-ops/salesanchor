# 実装カード 段階2 便4 — features/・components/ の 24件・19ファイルを LoadingBlock へ

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認 2026-10-23 PO「1」（部品の中に残る読み込み中の文字も同じ丸へ）
- 起点: origin/main 13576c09c。ブランチ `release/loading-mold-features`、worktree /Users/tanizawashingo/worktrees/salesanchor/release-loading-mold-features
- 根拠: 調査生出力 /tmp/CC報告ファイル/loading-stage2-bin4/（targets.tsv・excluded.tsv・context.txt・keys.txt・tests.txt・css.txt・counts.txt）
- 対象ADR: ADR-144・ADR-067・ADR-027

## 1. 置換の規則（card-6.md と同じ A/B/E/F。今回の判断を追加）
- 規則A: 読み込み中の文字だけを持つ要素（className・style・role="status" を含む）を要素ごと `<LoadingBlock />` に替える（role=status は金型の Spinner が持つ）
- 規則E: 外側の枠は残し、中の読み込み中の要素だけ替える
- 規則F: 枠自身が文字を持つ場合、枠（className・style・data-testid）を残して文字だけ `<LoadingBlock … />` に替える
- 判断1（文言保持）: キーが common.loading でない3件は label で今の文言を保つ（第1組と同じ扱い）
  - ExtractionAttemptHistory:43 → `<LoadingBlock label={t("pmgAttempt.loading")} />`
  - ProductMasterDrawer:175 → `<LoadingBlock label={t('tcgAnalysisReview.productMasterDrawer.formLoading')} />`
  - ReviewSection:182 → `<LoadingBlock label={t("tcgLineImport.loading")} />`
- 判断2（全画面）: ProtectedRoute:15 は規則F → `return <div className="loading-screen"><LoadingBlock /></div>;`（全画面の中央寄せを残す）
- 判断3（選択肢の一覧の中）: 次の3件は規則F・小さい丸 → 枠を残し中身を `<LoadingBlock size="sm" inline />`
  - ChannelTypeCombobox:164-166、CountryCombobox:163-165（div と style を残す）
  - InventorySearchBar:376-381（li・data-testid・style を残す）
- import: features/ 配下は `import { LoadingBlock } from "../../components/loading";`、components/ 直下は `import { LoadingBlock } from "./loading";`（targets.tsv 列8のとおり）
- 規則に当てはまらない形・行の文面不一致は止まって BLOCKED:

## 2. 対象 24件・19ファイル（行は 13576c09c 時点・各件のコードは targets.tsv）
- 規則A（20）: SupplierDetailDrawer:326、ExtractionAttemptHistory:43（判断1）、TcgProductDetailDrawer:314、SupplierQualityList:50、ProductMasterDrawer:175（判断1）、InventoryRowDrawer:123・181、ReviewRegisterProductForm:291、DiagnosticsDrawer:101、V102PostsTab:70、SupplierDetailView:95、MergeLeadModal:182、MergeContactModal:190、MergeCompanyModal:192、OrderFinancialPanel:210、ShippingDetailPanel:384、PurchaseDetailPanel:311、CommissionPanel:188
  - targets.tsv で A に入っている ChannelTypeCombobox:165・CountryCombobox:164 は判断3で規則Fとして扱う
- 規則E（2）: ReviewSection:182（判断1。section を残す）、DistributionPreview:67-69（div.dist-preview-card を残し中の p を替える）
- 規則F（2＋判断3の3）: ProtectedRoute:15、InventorySearchBar:380、ChannelTypeCombobox:165、CountryCombobox:164

## 3. 触らない範囲
- excluded.tsv の10件（loadingText 属性3・ボタン内の三項5・downloading 1・placeholder 関数1）
- CSS（`.loading`・`.loading-screen` などの規則は消さない。整理は別便）、辞書、金型（components/loading）、scripts/（countLoadingText の対象を広げない）
- 対象ファイルにもともとある lint 警告で commit が止まった場合は直さず BLOCKED: で全文報告

## 4. 文書（同じ PR に入れる）
- docs/handoff/loading-indicator/recon.md に節 C9（本便の調査結果・生出力の場所・件数 36行→本体34→属性3除き31、targets 24/excluded 10）
- docs/handoff/loading-indicator/design.md に節 2-13（本カードの判断1〜3と理由: 1=文言を変えない、2=認証待ちの全画面配置を保つ、3=一覧の行の高さと data-testid を保つ）
- 本カードを docs/handoff/loading-indicator/card-7.md として保存
- 台帳 .claude-pipeline/active-work.d/release-loading-mold-features.md（前便 release-loading-mold-pages-3.md と同じ形）

## 5. 検証（生出力を /tmp/CC報告ファイル/loading-stage2-bin4/impl/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象24件が消える | counts.txt と同じ方法（countLoadingText を対象19ファイルへ直接適用）で置換前→後が 24 減る。features+components 本体 31→7 |
| 試験 | 対象ファイルのディレクトリの vitest と tests.txt の試験を全件 pass。特に NeedsReviewTabsPanel.view.test.tsx・ReviewRegisterProductForm.test.tsx（getByRole("status") の複数一致）・InventorySearchBar 系・ProtectedRoute 系。tsc と同時に走らせない。時間切れは単独・`--testTimeout=30000` で切り分け、両方の生出力を残す |
| 型・lint・i18n | tsc 0・eslint（変更ファイル・--max-warnings=0）0・frontend/scripts/check-i18n-missing-keys.js exit 0・scripts/check-ui-governance.js exit 0 |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象19ファイル＋§4 の文書・台帳だけ |

## 6. 想定分岐
- 試験が読み込み中の文字・role=status・class loading を見ていて落ちた → 直さず BLOCKED: で試験名と生出力（Opus が判断）
- getByRole("status") が複数一致で落ちた → 同上
- tsc で schema.d.ts が無い → `npm run generate:api-types` を先に
- 行がずれた → 文面が一致すれば進め新旧の行を報告。不一致なら止まる
