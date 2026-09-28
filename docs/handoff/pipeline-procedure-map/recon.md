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
