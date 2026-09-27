# recon — pipeline-map-flowchart

## 調査対象ファイル

- `frontend/src/pages/super-admin/components/PipelineMapPanel.tsx:1-467` — 既存のER図スタイルマップ全文
- `frontend/src/pages/super-admin/components/PipelineMapPanel.css:1-81` — 既存スタイル全文
- `frontend/src/tokens.css:242-254` — --size-pipeline-* / --cat-* トークン定義
- `frontend/src/locales/ja.json:4053-4078` — 既存 pipelineMap i18n キー
- `frontend/src/locales/en.json:4053-4064` — 既存 pipelineMap i18n キー

## ADR確認

- ADR-027 (`docs/adr/ADR-027-ui-internationalization.md`): 全UI文字列はt()経由必須
- ADR-144 (`docs/CC_UI_GOVERNANCE.md`): CSS変数のみ使用・ハードコード禁止

## 既存実装の確認

- `@xyflow/react` は `frontend/package.json` に `"@xyflow/react": "^12.12.0"` で追加済み
- `nodeTypes` は `tableNode` のみ登録されていた → `phase` / `table` の2種類に拡張
- `NODE_METADATA` にラベル/説明がハードコードされていた → i18nキーに移行
- `--cat-import` / `--cat-pipeline` / `--cat-product` / `--cat-distribution` の4色が tokens.css で定義済み
- `--opacity-soft: 0.9` が tokens.css で定義済み
