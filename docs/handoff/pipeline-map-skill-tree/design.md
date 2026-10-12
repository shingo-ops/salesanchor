# Pipeline Map Skill Tree — design

## 目的
パイプラインマップをRPGスキルツリー形式に変換し、非エンジニアが直感的にデータフローを理解できるようにする。

## 参照
- recon: docs/handoff/pipeline-map-skill-tree/recon.md
- ADR-027: docs/adr/ADR-027-ui-internationalization.md
- ADR-067: docs/adr/ADR-067-design-tokens.md
- ADR-144: docs/adr/ADR-144-ui-governance.md

## 対象
- `frontend/src/pages/super-admin/components/PipelineMapPanel.tsx` — 全面書き換え
- PipelineMapPanel.css — 全面書き換え
- tokens.css — トークン入れ替え
- ja.json / en.json — キー追加・削除

## 対象外
- バックエンドAPI変更
- DBマイグレーション
- 他ページへの影響

## 変更前後

### Before
- 4つのPhaseNode（フェーズヘッダー帯）+ 23個のTableNode（矩形カード）
- 左→右のフローチャート形式

### After
- 起点ノード + 5幹ノード + 17枝ノード = 24個のSkillNode（円形オーブ）
- RPGスキルツリー形式（左端起点→右に枝分かれ）
- 幹ノード: 大オーブ(52px) + 強発光
- 枝ノード: 小オーブ(38px) + 控えめ発光
- smoothstepエッジ（なめらかな曲線）

## 受入条件

| 基準 | 検証方法 |
|------|----------|
| 起点ノードが左端に表示される | ブラウザで確認 |
| 幹ノード6個が横一列に並ぶ | ブラウザで確認 |
| 枝ノードが幹から上下に分岐する | ブラウザで確認 |
| ノードクリックでテーブル詳細ドロワーが開く | ブラウザで確認 |
| 言語切替で英語表示になる | ブラウザで確認 |
| ズーム・パンが正常動作する | ブラウザで確認 |
| CI全緑 | GitHub Actions |

## リスクと対処
- リスク: レイアウト座標の微調整が必要になる可能性
- 対処: 座標はコード内定数で管理、調整容易

## 維持の仕組み
- 守り手: `frontend/scripts/check-color-token-sync.js`（ADR-067）、`.github/workflows/frontend-check.yml`（ADR-027 i18n）、`.github/workflows/ui-governance-gate.yml`（ADR-144）
- テーブル追加時: TABLE_NODE_DEFSに行追加 + i18nキー追加

## 外部・過去事例の参照と我々への応用

- 事例1: RPGスキルツリーUI（Path of Exile / Civilization）→ ゲーム業界で広く使われるスキルツリー型のビジュアルは、非専門家がシステムの依存関係・分岐構造を直感的に理解するための確立されたUIパターン。応用: パイプラインの幹（メインデータフロー）と枝（参照データ）の関係を同じ視覚メタファーで表現。
- 事例2: React Flow公式Examples（Interactive skill tree）→ @xyflow/react公式ドキュメントにスキルツリー型インタラクティブグラフ実装例あり。応用: smoothstepエッジ・カスタムノード・ズーム/パン操作の実装パターンを踏襲。
- 数値エビデンス: 本変更はUI表示形式の変更であり、パフォーマンス改善やコンバージョン率等の数値指標は対象外。
