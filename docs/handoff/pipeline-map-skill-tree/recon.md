# Pipeline Map Skill Tree — recon

## 現状確認

### 既存実装
- `frontend/src/pages/super-admin/components/PipelineMapPanel.tsx:1-452` — 4段階フローチャート（PhaseNode + TableNode）
- `frontend/src/pages/super-admin/components/PipelineMapPanel.css:1-85` — フローチャート用CSS
- `frontend/src/tokens.css` — `--size-pipeline-node-w`, `--size-pipeline-node-max-w`, `--size-pipeline-phase-w` トークン

### PO要望
- RPGスキルツリーのように左端に起点、右に枝分かれする形
- 非エンジニアが業務の流れを理解できるビジュアル

### 関連ADR
- ADR-027: i18n強制（`t()` 経由必須）
- ADR-067: デザイントークン強制（CSS変数のみ）
- ADR-144: UIガバナンス（金型コンポーネント使用）

### 依存ライブラリ
- `@xyflow/react ^12.12.0` — 既存依存（変更なし）
