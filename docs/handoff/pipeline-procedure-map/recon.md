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

## 2026-09-28 最新main統合後の最終検証

main 8862732e494ac5d92287d57aeea808cee05d3151を通常merge。競合はevidence-registry末尾1件で、AstraがLINEガイドとAQ/ARの独立した追記を逐語で両方保持し、markerだけ除去した。todoは自動統合し、mainの他テーマ内容を保持。unmerged path 0、origin/main比のfrontend変更はガイド8pathだけ。
Sol CARD13実測: check:all exit0（既存warning140/error0）、build exit0（1740 modules/729ms、既存Vite警告あり）、関連unit2files/17件成功（1.71秒）、workers指定なしの既定E2E6/6成功（14.5秒、各2.4/1.7/1.7/1.5/2.7/1.3秒）。run前lsofはexit1/空で他server再利用なし。製品/試験の追加変更0。
Astraはコード/CSS/接続差分を直接確認し、現在mainのlocaleキー保持・登録部品/token・業務書込0の設計と整合を確認。Solの実行結果を根拠とし、Astra自身の試験再実行とは称さない。画面画像の直接確認とモックE2E、本番/PO読解確認を区別する。
状態: 設計/実装レビュー済み、最新main統合後のローカル受入検証済み。正式PR提出・CI・本ガイドへの番号付きGO・マージ・本番反映・PO読解確認は未了。正式保存後CARD14/15でPRまで進める。

提出カード保存時の停止記録: CARD15のshell文書作成中、hookが本文中のPR操作例を検出しone literal PR command制約で2回拒否、PR送信0・ファイル作成0。カードを入口参照と固定入力欄を示す設計文書へ改めて保存し、card-lint exit0。実際の提出は独立tool callで正式wrapperと全hook/validatorを通す契約のまま。設定変更・直接CLI/API代替・GO代筆0。

## 2026-09-28 PR #3831提出と最新base追従

CARD13保存fb39d740bd6afd6faf104f88dd8f0acb85cf780a、parents3c198d435+8862732。CARD14通常push成功、local/tracking/remoteの3SHA一致。CARD15は正式wrapperで1回作成、exit0、.pr-numberと実PR番号3831一致。PRはOPEN/ready、base main、head release/line-workflow-guide-resume、作者shingo-cc。AstraもGitHub GETで番号/HEAD/状態を直接確認。URL https://github.com/shingo-ops/salesanchor/pull/3831 。
初回CI: process-artifacts gate run36398169706/job108849430510はGO節欠落だけで失敗（Solが実ログ確認）。guard evaluation run36398169228/job108849430274はbase157cd679非包含によるancestor検査error。評価文書の不一致を示すfailureではなかった。Astraの実required checks取得は13件中12pass/guard evaluation1fail。これは提出時HEADfb39d740への結果であり、更新後HEADへ流用しない。
追加main157cd6799480e34481bdcc4a04804dc1e4732be7はbackend抽出リトライの旧明細整理2ファイルと設計文書2ファイルだけ。別Solの意味監査でガイド原稿修正0、frontend/部品/token/locale変更0、競合候補0。ガイドは再試行を実行せず既存エラーログへ案内するため、通常手順の意味は維持される。
CARD16で実fetch後固定SHA一致、通常mergeは競合0。backend2/文書2をmainどおり保持し、追加変更しない。ローカル最終検証と更新後HEADのCIは後続結果を参照する。

## 2026-09-28 PR #3831の提出後検証記録

PR https://github.com/shingo-ops/salesanchor/pull/3831 は正式提出済み。CARD16でmain157cd6799480e34481bdcc4a04804dc1e4732be7を競合0で統合。frontend treeは統合前と完全一致、origin/main比の製品差分はガイド8pathだけ。main由来backend2/文書2を保持し、本ガイドでDB/API/抽出処理を追加変更していない。
Solの最新実測: 直前lsof出力空/exit1、既定E2E6/6成功（13.7秒）。同一frontendに対するcheck:all/build成功・unit17成功はCARD13の実測を保持し、不要な重複実行をしていない。Astraはこの境界と限定意味監査を照合して実装レビューAPPROVEを維持する。
保存時点: 設計/実装/ローカル検証済み、PR提出済み。更新後のCI・承認・マージ・配備状態はPRの最新HEADと記録を正本として確認する。本文中の提出時CI失敗は過去HEADの観測であり、最新結果へ流用しない。POによる読みやすさの確認は未実施。本ガイドの番号付きGOは未受領、#3824のGOを流用しない。

## 2026-09-28 承認後の全文検査

PO原文「GO #3831」を08:59:38 UTCに確認しHEAD c0cf2d446へ転記した。項目名を正式書式へ修正後、run36400948572/job108858404625はGO確認成功。その先で設計docのADR-113相互参照不足を検出した。製品コードを変えず設計の参照欄を補う。変更後HEADへ旧承認を流用せず、全文検査とCIを再確認し、POへ版変更を報告する。マージ・本番反映は未実施。

## 2026-09-28 再GO受領後のmain前進

11:30:08 UTCにPO原文「GO #3831」をHEAD25e9ffca6への再承認として確認。実mainは1675bfaへ前進しPRはCONFLICTINGだったためマージ送信をしなかった。Sol調査では前進は別テーマの台帳・文書7件だけで製品変更0。実通常mergeではevidence-registryだけが競合し、双方の追記を逐語保持してmarkerを除去。todoの別テーマ完了行は自動統合でmain版になり、LINE行を保持した。評価のbaseを最新mainへ更新し、旧GOを統合後HEADへ流用せず再検証する。

main再前進追補: 88b495603保存直後にmainがb3cf1fdfへ前進し、必須CIは未報告、PRは再びCONFLICTINGとなった。fail/pending一覧が空でも全検査成功とは扱わない。Sol調査で追加はPR3834の共通Button移管と証跡、ガイド8pathは不変でリンク先の操作意味も不変。CARD17でSolが通常mergeを実行し、実競合2台帳はAstraがLINEとASの両方を保持して解消。評価base更新と必読blob一致を確認。旧HEADへのGOは履歴として維持し、統合後は再検証と再GOが必要。

CARD17再検証実測（Sol実行）: unmerged0、ガイド8pathは承認25e9比差分0。check:all exit0（既存警告140/error0）、build exit0（1740 modules、660ms）、単体2files17/17成功（1.56s）。直前5173 listener空/exit1を確認し、既定Chromium E2E6/6成功（12.5s、1 worker）。Astra直接task-state/diff-check成功。製品独自修正なし。統合後HEADのCIとPO再GO、マージ・本番反映・PO読解確認は別途。

PR3835結果記録追補: CARD17保存後、mainが0c060d3へ前進。追加はASの本番反映証跡・台帳9件のみでfrontend/backend/scripts/guards/CI差分0。guard評価run36417342020はstale-base-checkoutでskipし、必須status未報告を確認した。Astra実通常mergeは競合0で双方の記録を自動統合。評価base更新と同一blob照合を行い、製品treeがCARD17検証時と同一のため試験実測を保持する。新HEADのCIとPO再GOは別途確認する。

## 2026-09-28 PR3823統合の実処理照合

12:19:24 UTCにPO原文「GO #3831」をHEAD1b39bb461への承認として受領したが、実mainはaa74c018へ前進しPRはBEHIND。マージ送信0。追加4pathはskip_condition削除migration、seed撤去、既存実行登録、台帳。Sol初期REVISEは実処理を追加照合して訂正した。gemini_extraction_svc.py:295-311のskip_conditionと、tcg_extraction.py:164-220のmessage_exclude/message_exclude_no_digitは別category。後者の抽出前フィルタと同ファイル:306-371のempty/filtered/error記録が残るため、ガイドstep4のja/enは正しい。遷移先名称もsidebarと一致。推測で文言を変えずAPPROVE。
CARD18でSolが固定mainを競合0通常統合、frontend diff0/unmerged0を実確認。独自製品変更・DB実行なし。CARD17試験を同一frontendの証拠として保持。評価baseと必読blobを最新mainに照合。統合後HEADへの旧GO流用はせず、全CIと再GO確認後にのみマージする。

## 2026-09-28 PO追加実行指示とCARD19

12:39:26 UTCにPOから同一セッション完了・Astra/Sol分担・マージ/デプロイまでの明示指示を受領。原文末尾は「PRマージ、デプロイまで完走させてくれ。」。全文をPR3831へ保存する。従前の番号付きGOは各受領版の履歴として保持し、新しい番号付き発話を創作しない。今回のPO本人の追加指示に基づき、同じPRの目的・仕様を維持するmain追従と再検証を実施し、確定HEADの全検査と既存safe wrapperを通して実行する。代理GO権限の自己有効化やガード変更ではない。仕様変更・事業判断が必要なら停止する。
main a1cd9eaの追加5pathは試運転専用shadowテーブルと発送形式列/未配線prompt、migration登録、検査設定、台帳。Sol実物監査で現在の解析/配信queryとガイド8path変更0を確認しAPPROVE。CARD19で通常統合は競合0、frontend差分0、未解消0。DB実行なし。CARD17の同一frontend試験を維持し、新base評価と最新CIを確認する。
