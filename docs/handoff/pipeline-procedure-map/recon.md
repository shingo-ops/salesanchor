# Recon: PipelineMapPanel 業務手順書フローチャート

この文書は何か: LINE解析の流れと、利用者向け説明画面の根拠を残す記録。
親: [提供元フィード翻訳](../../specs/inventory-management/feed-translation/README.md)
現行追加作業は2026-09-28追補。冒頭の既存マップ刷新は履歴であり、本便の実装指示ではない。

## 調査日時
2026-09-27

## 変更対象ファイル（フルパス:行番号）

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/pages/super-admin/components/PipelineMapPanel.tsx:1-436` | 全体置換: RPGスキルツリー → 業務手順書フローチャート |
| `frontend/src/pages/super-admin/components/PipelineMapPanel.css:1-86` | 全体置換: skill-node スタイル → procedure/master/end-node スタイル |
| `frontend/src/tokens.css:242-245` | skill-orb/skill-label トークン削除、proc-card/proc-master トークン追加 |
| `frontend/src/locales/ja.json` | `analysisRules.pipelineMap` セクション置換（旧: nodeLabel_*/nodeDesc_*/edge*, 新: proc.*） |
| `frontend/src/locales/en.json` | 同上（英語） |

## 削除するコード

- `SkillNode` コンポーネント（全体）
- `SkillNodeData` 型定義
- `TABLE_NODE_DEFS` 定数（23ノード定義）
- `api` インポート（`../../../lib/api`）
- `Drawer` インポートと全ドロワー状態・ハンドラ
- `DataTable` インポートとカラム定義
- `DbColumn` 型定義
- `nodeTypes.skill`
- `handleNodeClick` コールバック

## 追加するコード

- `ProcedureNode` コンポーネント（6ステップカード）
- `MasterNode` コンポーネント（4マスタカード）
- `EndNode` コンポーネント（完了マーカー）
- フィードバックエッジ（STEP4 → マスタカラム、点線・警告色）
- i18n キー `analysisRules.pipelineMap.proc.*`（ja.json/en.json 両方）

## 既存ADR確認

- **ADR-027** (`docs/adr/ADR-027-ui-internationalization.md`): 全 UI 文字列 `t("key")` 経由 → 遵守
- **ADR-067** (デザイントークン): CSS 変数のみ、ハードコード色禁止 → 遵守
- **ADR-144** (`docs/CC_UI_GOVERNANCE.md`): 金型部品使用、生 select/input 禁止 → 対象外（ReactFlow ノード）

## ビルド確認（origin/main HEAD: 95164676e）

- `npm run build`: ✓ built in 1.32s（エラーなし）
- `npm run lint`: 0 errors, 140 warnings（PipelineMapPanel 由来ゼロ）


## 2026-09-28 LINE業務ガイド原稿証跡

この追補は、操作の順序と意味を説明するための実装照合表。
親: [提供元フィード翻訳](../../specs/inventory-management/feed-translation/README.md)
設計: [業務ガイド設計追補](./design.md)
固定SHA: ae783c7f583e2d5628c19d999ed7ce6c7944e9b8。調査担当Sol、照合・設計審査Astra。
旧調査95164676以後、今回調べた処理/画面群で変更があったのはPipelineMapPanel.tsx/.cssの2件。
現在のマップはDB表ノードではなく、マスタ4・手順6・完了の静的ReactFlow。旧DB図を現在形として説明しない。
以下はコードからの観測事実。実環境の環境変数値・POの画面確認は未確認であり、合格扱いしない。

| 観測 | 一次情報（上記SHAのファイルと行） |
|---|---|
| 現行mapは静的4マスタ/6手順、操作画面リンクなし | frontend/src/pages/super-admin/components/PipelineMapPanel.tsx:186-417 |
| hub section初期値はquery、同hub遷移はcallbackが必要 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx:122-135 |
| システム欄と既存キー | frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10-34,139-149 |
| 配信routeと配信preview | frontend/src/App.tsx:331-332; frontend/src/pages/super-admin/TcgDistributionPage.tsx:17-54; DistributionWorkspace.tsx:65 |
| Cardの本番標準/variants | docs/specs/component-standard.md:70-87; frontend/src/components/Card.tsx:16-45 |
| Card Preview限定文はコメントのみ。本番利用も実在 | docs/handoff/mobile-responsive/recon.md:24-31,113-119; frontend/src/pages/super-admin/components/DbViewerPanel.tsx:563,580 |
| 金型必須/未登録部品禁止 | docs/CC_UI_GOVERNANCE.md:9-27; ADR-144-ui-component-governance.md |
| Badge/Button契約 | frontend/src/components/Badge.tsx:16-59; frontend/src/components/Button.tsx:20-88 |
| typography/space/Card token実在 | frontend/src/tokens.css:14-18,48-77,452-459 |
| 手動取込の.txt/期間指定、既定24h | frontend/src/pages/super-admin/TcgLineImportPage.tsx:82,173,221,324; backend/app/routers/tcg_line_import.py:127-175 |
| 名前完全一致で仕入元解決、不明ならpending | backend/app/services/tcg_line_import_svc.py:122-267 |
| 既存仕入元割当はLINE名更新、新規登録別経路 | backend/app/routers/tcg_line_import.py:441-519 |
| 不明をすべて解決後commitで保存/queue、割当だけではenqueueしない | backend/app/routers/tcg_line_import.py:549-649; backend/app/services/tcg_line_import_svc.py:687-733 |
| 期間内で仕入元ごと最新を選び原文/job保存 | backend/app/services/tcg_line_import_svc.py:275-329 |
| 空文/除外/抽出失敗と明細保存の分岐 | backend/app/tasks/tcg_extraction.py:223-482 |
| 自動解析と自動配信は環境設定に依存 | backend/app/tasks/tcg_extraction.py:484-506 |
| 商品/単位/状態の照合 | backend/app/services/tcg_analyzer_svc.py:1182-1243,1294-1314,1366-1390 |
| 取込画面内で進捗/要確認を見る | frontend/src/features/tcg-import-workflow/ImportWorkflowPanel.tsx:50-119 |
| hub needs-reviewはcomingSoon | frontend/src/pages/super-admin/AnalysisRulesPage.tsx:103-110 |
| 配信は件数preview→確認→実行、個別行選択ではない | DistributionPreview.tsx:74-190 |
| 配信は既存対象シートをclearして全置換 | backend/app/services/tcg_distribution_svc.py:456-520 |
| 未完了解析/抽出・配信先なし・認証なしでは配信停止 | backend/app/services/tcg_distribution_svc.py:673-801 |

上表の短名DistributionWorkspace/DistributionPreviewとADRは索引またはimport経路から実在を確認した参照であり、新規ファイル名を仮定したものではない。
要確認からの自由編集/保存は動作確認できていないためガイドでは提供しない。エラーログへの導線だけを置き、ガイドから再試行しない。
部品の外観は金型に委譲。現状のマップの表示値はruntimeの配線SSOTではなく、ガイドへ業務設定値を複製しない。
既存feed-translation理想図の免許制など未実装の将来像を、今回の現在手順に混ぜない。
外部事例調査は不要: 本件の証拠は既存実装の分岐・画面導線・部品契約であり、他社効果値ではない。

## 2026-09-28 CARD-05/06 継続作業机と最新main統合の実測

- CARD-04は直接worktree復元がcard-lint L12でexit1、未実行。公式入口を維持する05/06へ変更し、両カードlint exit0。
- 05第1回はsandboxが.git/FETCH_HEAD書込を拒否してexit255、未作成。同じ公式操作の正規escalation後、第2回exit0。実ガード/設定の無効化0。
- 事前remote main / 実作成HEAD / 06開始時origin/mainはすべてfdf3b45a4c0423413e704694fb99700d94e1d5a7。
- 新path: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume。新UUID bce43041-c2fe-4179-a45b-16ddfd59ec66。
- 06でpwd/git登録/branch/UUID/公式claim一致をSolが確認。claim session 09AF2669-F9B1-49CC-B2A0-DBD3E134E5A8、claimed_at 2026-09-28T07:52:02.653130Z。分割台帳はIN_PROGRESS。
- 元branch local/remoteは87c4ad83a96e25dfab792a3b57dda75ba51a65ebのまま。元UUIDの退避は/private/tmp/line-guide-parked-20260928/worktree-id.json。元ref/台帳を削除・DONE化していない。
- 公式作成scriptはreaper --executeを伴う。05再実行時の回収はrelease/pr-create-phase-separationのみ。Sol実測: non-force worktree removeとbranch -d成功、台帳は既にDONE、削除時HEAD4bad43a4dは現在mainのancestor判定exit0。他の候補は保護された。これはPOのマージ済み作業机回収指示の範囲であり、一般削除許可ではない。
- 本店非台帳snapshotは作成前後で同じ18件。AnalysisDashboardPanel css/tsxと未追跡16件を変更していない。比較はSol実行報告。
- 06のgit merge --no-ff --no-commitはexit0、競合0、17files/1135行追加、commit前停止。Astraもgit statusで17pathを直接照合した。
- 共有pathはtasks/todo.md、evidence-registry.md、ja/enの4件。mainのextractionJobSupplier/Resolved/Unresolved/NeedsReviewを両言語で保持（Sol直接検査）。

### 最新mainによる業務説明への影響

Sol読取限定監査: 要修正0。mainのtcg_analysis_dashboard_svc.py:198-224とAnalysisDashboardPanel.tsx:1049-1075は最近の抽出結果の仕入元/解決・未解決・要確認件数表示を変更。empty/filteredを一覧から除外したが記録処理は変わらない。ガイド段階4は記録の区別を説明しており、一覧への表示を約束していない。段階3の取込処理、段階6の取込画面とマスタ導線に新差分なし。本番DB/設定の実値をこの監査で確認したとはしない。

### 手順整合の審査

Sol初回はREVISE: --claude、reaper副作用、fetch前後SHAの扱いを指摘。Astraは上位POのAstra/Sol限定、回収の明示許可、固定SHA不一致時停止を確認し、対象限定の根拠を提示。再査定APPROVE/blocking 0。通常規則の恒久解除、ガード/trustの回避、任意の新main受容は行わない。

## 2026-09-28 最新baseでの検証と時間切れの切り分け

CARD07: Sol実行でcheck:all exit0（既存警告140/error0）、build exit0（Viteの既存import/chunk警告あり）、関連unit2files/17件成功。npm ci後lockfile変更0。
既定並列E2Eは2/6成功、4件が30秒timeoutで失敗。合格扱いしない。失敗trace/画像は/tmp/reports/card-line-guide-resume-failedへ保存、旧base成功画像は/tmp/reports/card-line-guide-before-resumeへ退避。
Solのtrace読取: 初回goto24.29〜25.41秒、menu focus3.61〜3.97秒、初回4workerは各406〜407 request。スクリーンショット0.186〜0.965秒、timeout後teardown8.94〜12.45秒。後続2件は9.6/12秒。画面描画/期待値は進んでいたが全体30秒を超過した。
未mock背景APIの404が各15件あり、JS例外/pageError/warningは0。背景API404の遅延寄与を確定しない。ガイドの業務書込と別の既存GETであり、未確認payloadを創作してmockを増やさない。
CARD08: 失敗記録を保持し、同一timeout/assertのままworkers=1だけ指定。6/6成功、総55.0秒、各10.4/6.2/6.8/6.6/10.2/3.7秒。run前lsofはexit1/出力空で他server再利用なし。製品/lockfile副作用0。
この比較は同時実行を除いた条件での機能試験成功であり、原因全体や並列性能の保証ではない。
AstraがContext7 /microsoft/playwrightでworkers=1とmode defaultの仕様を照合。公式: https://github.com/microsoft/playwright/blob/main/docs/src/test-parallel-js.md 。defaultは同specのfullyParallelを上書きし、serialの後続skipを導入しない。
CARD09: 同specのmode defaultと観測に基づく理由コメントだけを許可。global設定/timeout/assert/mockを変更しない設計をAstra自己審査APPROVE、別Solの限定レビューも補正後APPROVE。
09初回編集は本店main/develop supervisionのPreToolUseガードで拒否、適用0。Solはexec/python等への変形再試行をせず停止した。正しい作業rootと正式起動手順を照合中。最終の既定コマンド6/6は未実施。

CARD10再開根拠: Sol読取でadapterは絶対target pathではなくevent.cwdからcontextを作り、本店/mainのmutationを拒否することを確認。targetのGit登録/branch/UUID/claimは有効。正式なcodex exec --cdで登録済みworktreeを起動rootに指定し、model gpt-5.6-solを明示する。AstraはOpenAI Docs MCPと実CLI helpを照合した。初回CLIはsandboxとapprove-for-meの重複指定をusageエラーexit2で拒否し、処理未開始。helpに従いworkspace-writeを内包するapprove-for-meのみへ整理した。起動headerは専用workdir/gpt-5.6-sol/approval on-request/sandbox workspace-write。hook/rules/trust無効化0、GO権限の有効化0。公式資料: https://learn.chatgpt.com/docs/developer-commands#codex-exec 。

### CARD10完了の実測

親のexecutor-preflight exit0後、子CLIも同一コマンドを正規escalationしてexit0。実装差分は観測コメント・test.describe.configure({ mode: "default" })・空行の3行のみ。既定E2E6/6、23.9秒。出力/private/tmp/line-guide-card10-sol-resume.log。eslintのexit0は設定対象外warning1を伴うのでlint合格根拠にしない。Astraは実差分と.worktree-idを直接確認し、カード記載のUUID/path/branch一致を確認。CODEX_THREAD_IDは別の識別子であり比較対象外。
CARD11草案をtmpへ書く初回コマンドは本店cwdでprotected mainガード拒否、未作成。共通ルールどおり実行cwdと先頭cdを専用worktreeに固定して、同じ文書作成を実施。ガード無効化なし。card-lint exit0（長行警告1件）。

### PR3828によるmain更新の限定影響監査

origin/main 8862732e494ac5d92287d57aeea808cee05d3151。Sol読取監査ではfdf..mainのガイド接触はKnowledgeAliasesTab.tsxのcancel/save4ボタンを既存Buttonへ移管した部分のみ。section key/API/業務意味は不変。ガイド8frontend path、共通Button/Badge/Card、token、localeのmain側変更0。ガイド本文/実装修正必要0。evidence-registryの同じ末尾への追記が競合候補、todoは同一pathだが別hunk。実統合前の観測であり、他テーマの途中状態文面を完了と読み替えない。
