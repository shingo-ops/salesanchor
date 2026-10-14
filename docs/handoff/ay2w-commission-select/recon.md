# AY-2w recon: CommissionPanel の担当者 select

- 基準コミット: f353bb437（origin/main、Merge pull request #4264 from shingo-ops/release/ay2v-unused-tokens）
- 作業コピー: /Users/tanizawashingo/worktrees/salesanchor/release-ay2w-commission-select（ブランチ release/ay2w-commission-select）
- 生出力: /tmp/CC報告ファイル/ssot-ay2w/recon/（以下、各見出しにファイル名を併記）。参照は全てリポジトリ根からのパス:行番号。
- ADR 検索: docs/handoff/ay2w-commission-select/recon.md の H 節に結果を記載。

## A. 作業コピーと前提（worktree.txt, preflight.txt）
- 作業コピーは origin/main から新規作成され、ブランチ release/ay2w-commission-select は origin/main を追跡する（worktree.txt 末尾「branch 'release/ay2w-commission-select' set up to track 'origin/main'.」）。
- executor-preflight は PREFLIGHT OK（preflight.txt）。本店は origin/main より 2229 コミット遅れ・未保存 25 件の WARN あり（本便は本店に書き込まない）。

## B. FormField.css の金型規則（B_css.txt）
- 生出力ファイル B_css.txt は 0 行（空）。この節の事実は実装時にリポジトリから直接確認した次のものに限る。
- frontend/src/components/FormField.css:49 `.comp-select__control,`、:75 `.comp-select__control {`、:89 `.comp-select__control {`、:97 focus、:107 disabled、:137 と :145 `.comp-select__control--sm`、:177 `--full`、:188 `--sm.comp-select--no-indicator`。
- 767px 以下の min-height（設計 design.md §3 が引く frontend/src/components/FormField.css:443-449）と frontend/src/tokens.css:482 は設計時の recon による。本便の実測（ay2w-acceptance.md）で 390px の select 高さ 44px を確認した。

## C. SelectControl の既存利用（C_usage.txt）
- 利用例（children モード）: frontend/src/pages/account-settings/PreferencesSection.tsx:39（`size="sm"`）、frontend/src/pages/admin/TenantPolicyPage.tsx:169・:269・:287、frontend/src/pages/admin/TenantProfilePage.tsx:237、frontend/src/pages/bots/BotsPage.tsx:235・:243。
- import の手本: frontend/src/components/CompanyContactSelector.tsx:31（`import { SelectControl } from "./Select";`）。
- `git grep -c SelectControl -- frontend/src` が一致するファイル数: 52（実装時の実測）。

## D. CommissionPanel と過去の保留記録（D_commission.txt, D_aj.txt, D_AJ_1252-1270.txt）
- 変更前の生 select: frontend/src/components/CommissionPanel.tsx:209 `<select`、:225 `</select>`（設計 design.md §2）。import 追加位置は :20 の直後。
- 台帳上の保留行: docs/specs/design-system/design.md:2056「報酬 CommissionPanel.tsx:205 | 1 | §AJ :1252-1270 の 390px 横 overflow 保留（表統一便）」。
- §AJ: docs/specs/design-system/design.md:1252-1270。390px・英語の実 CommissionPanel で旧から横 overflow があり body clientWidth390 に対し scrollWidth 528→537（docs/specs/design-system/design.md:1254）。表 CSS・横スクロール修正をボタン移管へ混載しない（docs/specs/design-system/design.md:1256）。
- §AW-2b: docs/specs/design-system/design.md:2156 生 select 63 から保留 10（ProductEditPage 9、CommissionPanel 1）を除く 53 を移管。:2176 保留 10 件の見た目不変を測る基準。
- docs/specs/design-system/design.md:2403 報酬の保留は select 1 件だけで同ファイルに生 input は無い。
- docs/specs/design-system/migration.md:100（TB-01 の記載先は frontend/src/components/CommissionPanel.tsx:186）、docs/specs/design-system/migration.md:219（AJ 分割）。
- 既存試験: frontend/src/components/SharedButtonMigration.test.tsx（CommissionPanel の解除・再計算の操作試験）。

## E. Select.tsx の型（Select.tsx.txt）
- frontend/src/components/Select.tsx:21 `SelectSize = "sm" | "md" | "lg"`、:25 `SelectControlOwnProps`（options/size/fullWidth/placeholder/appearance）、:33 `SelectControlNativeProps`、:38 options モード、:43 children モード。
- children モードでは native の `aria-label`・`data-testid`・`value`・`disabled`・`onChange` が select 要素へ届く（実測: ay2w-acceptance.md の DOM 差分 0）。

## F. UI ガバナンスの検出範囲（F_gov.txt, F.txt）
- scripts/check-ui-governance.js:36 `PAGES_DIR = 'frontend/src/pages/'`。検出対象は pages 配下のみで components 配下（CommissionPanel.tsx）は対象外。:153 `countSelect`、:155 正規表現 `/<select[\s>/]/g`。
- F.txt は 0 行（空）。

## G. 関連 handoff 一覧（G_list.txt）
- docs/handoff/ 配下に同種の recon.md / design.md がある（例: docs/handoff/dashboard-chart-period/design.md）。構成の手本として参照。

## H. ADR 検索（H_adr.txt）
- 検索で出た ADR: docs/adr/ADR-067-design-token-enforcement.md ほか（H_adr.txt 10 件）。本便の対象 ADR は design.md 冒頭のとおり ADR-144・ADR-067・ADR-027。
