# 実装カード 段階2 便3（第2組）— 仕入元・単位・チーム・スタッフなど 18画面 28件を LoadingBlock へ

- 状態: Opus 作成。PO 承認 2026-10-22 PO「１」（残り87か所を40か所以下の組で順に）。第1組 #4654 の本番目視合格 2026-10-22 PO「1,でた」
- 起点: origin/main（第1組合流 9e2133283 以降）。ブランチ `release/loading-mold-pages-2`
- 根拠: 調査生出力 /tmp/CC報告ファイル/loading-bin3-recon/（targets.tsv・groups.txt「第2組」・keys.txt・css.txt・tests.txt）
- 対象ADR: ADR-144・ADR-067・ADR-027

## 1. 置換の規則（card-4.md §1 と同じ）
- 規則A: 読み込み中の文字だけを持つ要素（`<p>` / `<div className="loading">`）を要素ごと `<LoadingBlock />` に替える
- 規則B: 三項・`&&`・`return` の形は残し、表示部分だけ替える
- 28件すべて文言キーは `common.loading`（keys.txt）なので label は渡さない。size も既定のまま
- 規則E（第2組で追加）: `roles/RolesPage.tsx:303` `if (loading) return <div className="page"><div className="loading">{t("common.loading")}</div></div>;` は外側の `<div className="page">` を残し、内側だけ替える → `if (loading) return <div className="page"><LoadingBlock /></div>;`
- import は各ファイルに `import { LoadingBlock } from "../../components/loading";` を1行
- 規則に当てはまらない形が出たら止まって BLOCKED:

## 2. 対象 28件・28ファイル（frontend/src/pages/ 配下。行は origin/main 44c34a488 時点）
- archives/ArchivesPage:35、badges/BadgesPage:74、bots/BotEditPage:84、bots/BotsPage:291、buddy/BuddyPage:75、channels/ChannelsPage:421
- conditions/ConditionImportPage:132、conditions/ConditionsPage:559、erp/ERPPage:66、goal-setting/GoalSettingPage:647
- note-master/NoteMasterImportPage:132、note-master/NoteMasterPage:387、product-categories/ProductCategoriesImportPage:138、product-categories/ProductCategoriesPage:347
- roles/RolesPage:303（規則E）、shifts/ShiftsPage:86、staff/StaffEditPage:154、staff/StaffPage:327、staff-reports/StaffReportsPage:101
- status-master/StatusMasterImportPage:132、status-master/StatusMasterPage:416、suppliers/SupplierEditPage:75、suppliers/SupplierImportPage:132、suppliers/SuppliersPage:231
- teams/TeamEditPage:63、teams/TeamsPage:273、units/UnitImportPage:132、units/UnitsPage:367
- 各件の今のコードは targets.tsv

## 3. 触らない範囲
- excluded.tsv の件・第3組・features/・components/
- CSS: `.loading` などの規則は消さない（css 整理の別便）
- 辞書・金型・scripts/
- 対象ファイルにもともとある lint 警告で commit が止まった場合は、直さず BLOCKED: で警告の全文を報告（Opus が追補で判断する）

## 4. 検証（生出力を /tmp/CC報告ファイル/loading-stage2-bin3-g2/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象の28件が消える | countLoadingText で対象28ファイルの合計が置換前→後で 28 減る（前後の数を記録） |
| 試験 | 対象18ディレクトリの vitest を全件 pass（試験の無いディレクトリは「0本」と記録）。tsc と同時に走らせない |
| 型・lint・i18n | tsc 0・eslint（変更ファイル・--max-warnings=0）0・frontend/scripts/check-i18n-missing-keys.js exit 0・scripts/check-ui-governance.js exit 0 |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象28ファイル＋docs/台帳だけ |

## 5. 想定分岐
- 行がずれた → 文面が一致すれば進め、新旧の行を報告。一致しなければ止まる
- 試験が落ちた → 直さず BLOCKED: で試験名と生出力（触っていない試験の負荷落ちは単独再実行で切り分け、両方の生出力を残す）
- tsc で schema.d.ts が無い → `npm run generate:api-types` を先に
