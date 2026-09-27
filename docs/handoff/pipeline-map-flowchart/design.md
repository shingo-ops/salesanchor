# design — pipeline-map-flowchart

## KGI

非エンジニアが「上流から下流に何が起きているか」をパイプラインマップを見るだけで理解できる。

| 基準 | 検証方法 |
|------|---------|
| 4つのフェーズヘッダーが左→右に表示される | 画面で目視確認 |
| メインフロー6本が太いアニメーション矢印で表示される | 画面で目視確認 |
| 各矢印に日本語ラベルが付いている | 画面で目視確認 |
| ノードクリックでテーブル詳細が開く | 動作確認 |
| 言語切り替えで英語表示になる | 言語切り替えで確認 |

## ADR参照

- ADR-027: i18n強制 — TABLE_NODE_DEFSから日本語ハードコードを排除しt()経由に統一
- ADR-144: CSS変数強制 — `--opacity-soft` / `--size-pipeline-phase-w` / `--cat-*` を使用

## recon参照

docs/handoff/pipeline-map-flowchart/recon.md

## 変更内容

### 新規ノードタイプ: PhaseNode

フェーズヘッダー（PhaseNode）を追加。`nodeTypes` に `phase` を登録。
フェーズヘッダーは `selectable: false` / `draggable: false`。

### TABLE_NODE_DEFSのi18n化

既存の `NODE_METADATA`（ハードコードラベル）を廃止。
`TABLE_NODE_DEFS` はID・座標・カテゴリのみ保持し、ラベル/説明は
`t(\`analysisRules.pipelineMap.nodeLabel_${id}\`)` で取得。

### エッジの二種類分け

- メインフロー6本: strokeWidth=3 / animated=true / 日本語ラベル
- 補助フロー16本: strokeWidth=1.5 / animated=false / ラベルなし

### tokens.css追加

`--size-pipeline-phase-w: 380px` を追加（PhaseNodeの幅）

## 触るファイル

- frontend/src/pages/super-admin/components/PipelineMapPanel.tsx
- frontend/src/pages/super-admin/components/PipelineMapPanel.css
- frontend/src/tokens.css
- frontend/src/locales/ja.json
- frontend/src/locales/en.json
- docs/handoff/pipeline-map-flowchart/recon.md（本ファイル）
- docs/handoff/pipeline-map-flowchart/design.md（本ファイル）

## 削除するファイル

なし

## 外部事例

- React Flow (xyflow) の公式ドキュメント: `nodeTypes` 登録によるカスタムノード定義
- xyflow の `selectable: false` でクリック不可ノードを実装するパターン

## 維持の仕組み（守り手）

- ADR-027 ESLint rule `local/no-japanese-literal` が新しいハードコード日本語を検出する
- ADR-144 `scripts/check-css-hardcoded-values.js` がopacity直書きを検出する
- 守り手ファイル: `frontend/eslint.config.js:1`
