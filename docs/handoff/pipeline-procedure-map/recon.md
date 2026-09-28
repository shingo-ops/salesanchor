# Recon: PipelineMapPanel 業務手順書フローチャート

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
