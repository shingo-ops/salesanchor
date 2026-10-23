# 実装カード 段階2 便3（第3組）— 顧客・見込み客・商品・見積・請求・受注・登録など 17 画面 24 件を LoadingBlock へ

- 状態: Opus 作成。PO 承認 2026-10-22 PO「１」（残り87か所を40か所以下の組で順に）。第1組 #4654 本番目視合格 PO「1,でた」、第2組 #4658 本番反映済み
- 起点: origin/main（第2組合流 5d647f1e8 以降）。ブランチ `release/loading-mold-pages-3`
- 根拠: 調査生出力 /tmp/CC報告ファイル/loading-bin3-recon/（targets.tsv・context.txt・groups.txt「第3組」・keys.txt・css.txt・tests.txt）
- 対象ADR: ADR-144・ADR-067・ADR-027

## 1. 置換の規則（card-4.md §1・card-5.md §1 と同じ）
- 規則A: 読み込み中の文字だけを持つ要素（`<p>` / `<div>`。className・style を含む、複数行も含む）を要素ごと `<LoadingBlock />` に替える
- 規則B: 三項・`&&`・`return`・`if` の形は残し、表示部分だけ替える
- 規則E: 外側の枠（`<div className="page">` / `<div className="page-container" …>`）は残し、中の読み込み中の要素だけ替える
- 規則F（第3組で追加）: 枠の div 自身が文字を持つ `schedule/ScheduleSettingsPage.tsx:109` `return <div className="page">{t("common.loading")}</div>;` は、枠を残して文字だけ替える → `return <div className="page"><LoadingBlock /></div>;`
- 24件すべて文言キーは `common.loading`（keys.txt）なので label・size は渡さない
- import は各ファイルに `import { LoadingBlock } from "../../components/loading";` を1行
- 規則に当てはまらない形が出たら止まって BLOCKED:

## 2. 対象 24件・23ファイル（frontend/src/pages/ 配下。行は origin/main 44c34a488 時点）
- 規則A: commission-settings/CommissionSettingsPage:179、commissions/CommissionsPage:167-169（style の marginTop ごと消える）、companies/CompaniesPage:399、company-detail/CompanyConvLogsTab:92（`{loading && <p className="conv-logs-loading">…</p>}` → `{loading && <LoadingBlock />}`）、contacts/ContactEditPage:141、contacts/ContactsPage:386、invoice-create/InvoiceCreatePage:256、invoices/InvoicesPage:150、leads/LeadEditPage:169、leads/LeadsPage:479、notifications/NotificationsPage:173、orders/OrdersPage:111、products/ProductEditPage:199、products/ProductsPage:287、quotes/QuotesPage:145、sales/SalesPage:87、schedule/ScheduleSettingsPage:127
- 規則E: company-detail/CompanyDetailPage:64（`<div className="page-container"><LoadingBlock /></div>`）、invoice-detail/InvoiceDetailPage:191・quote-detail/QuoteDetailPage:119（`<div className="page"><LoadingBlock /></div>`）、register/RegisterAddressPage:264・register/RegisterChangeBillingPage:203・register/RegisterPage:249（`page-container` の div と style は残し、中の `<p>` だけ替える）
- 規則F: schedule/ScheduleSettingsPage:109
- 各件の今のコードは targets.tsv、前後は context.txt

## 3. 触らない範囲
- excluded.tsv の件（SchedulePageImpl:821 など）・features/・components/
- CSS: `.loading`・`.conv-logs-loading` などの規則は消さない（css 整理の別便）
- 辞書・金型・scripts/
- 対象ファイルにもともとある lint 警告で commit が止まった場合は、直さず BLOCKED: で警告の全文を報告（Opus が追補で判断する）

## 4. 検証（生出力を /tmp/CC報告ファイル/loading-stage2-bin3-g3/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象の24件が消える | countLoadingText で対象23ファイルの合計が置換前→後で 24 減る（前後の数を記録） |
| 試験 | 対象17ディレクトリの vitest と、対象ページを import する他の試験を全件 pass（tsc と同時に走らせない。負荷の時間切れは単独・`--testTimeout=30000` で切り分け、両方の生出力を残す） |
| 型・lint・i18n | tsc 0・eslint（変更ファイル・--max-warnings=0）0・frontend/scripts/check-i18n-missing-keys.js exit 0・scripts/check-ui-governance.js exit 0 |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象23ファイル＋docs/台帳だけ |

## 5. 想定分岐
- 行がずれた → 文面が一致すれば進め、新旧の行を報告。一致しなければ止まる
- 試験が読み込み中の文字・class `loading`・`conv-logs-loading` を見ていて落ちた → 直さず BLOCKED: で試験名と生出力
- tsc で schema.d.ts が無い → `npm run generate:api-types` を先に
