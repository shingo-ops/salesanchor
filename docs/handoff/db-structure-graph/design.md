# DB構造グラフ — design

参照: docs/handoff/db-structure-graph/recon.md

## 目的
LINE解析パイプラインのテーブル関連を視覚的なマップで表示し、POがシステム構造を直感的に把握できるようにする。

## 変更内容
1. @xyflow/react（React Flow）ライブラリを導入
2. PipelineMapPanel コンポーネントを新規作成（ADR-144: components/金型先確認済み・既存Drawer流用）
3. サイドメニューに「パイプラインマップ」を追加
4. ノードクリックでDrawer経由のテーブル詳細表示
5. tokens.css にパイプラインマップ専用サイズトークンを追加（ADR-067・ADR-144準拠）

## 受け入れ基準

| 基準 | 検証方法 |
|------|----------|
| パイプラインマップが表示される | 管理画面 > 解析状況 > パイプラインマップ |
| テーブルが箱で表示される | ブラウザ確認 |
| FK関係が矢印で接続される | ブラウザ確認 |
| メインフローが太線で強調される | ブラウザ確認 |
| ノードクリックでカラム詳細が見える | ブラウザ確認 |
| ズーム・パン・ドラッグが動作する | ブラウザ確認 |
| CI全緑 | GitHub Actions |

## 対象外
- テナントスキーマのテーブル表示（CRMテーブル等はこのマップの対象外）
- テーブル構造の編集機能

## 外部・過去事例の参照と我々への応用
- React Flow（@xyflow/react）: GitHub Stars 27k+、npm 週間DL 400k+ の実績あるグラフ描画ライブラリ。DAGや有向グラフのインタラクティブ表示において業界標準的な選択。カスタムノード・エッジ・ミニマップ・ズーム制御など本用途に必要な機能がすべて揃っている。
- 本プロジェクトの既存実装: DbViewerPanel.tsx（スプレッドシート形式）は行列表示に特化しており関係性の可視化が困難。マップ形式を別パネルとして追加することでUIを壊さずに機能拡張できる。

## 維持の仕組み

守り手: frontend/src/pages/super-admin/components/PipelineMapPanel.tsx

- tokens.css の `--size-pipeline-map-min-h` / `--size-pipeline-node-max-w` をCSS変数化済み → デザインシステム変更時に一元更新可能（ADR-067準拠）
- FK関係はバックエンドAPI（super_admin_db_schema.py）から取得 → DBスキーマ変更が自動反映される（ハードコードなし）
- i18n: ja.json/en.json 両キー同一必須（ADR-027）→ CI チェックで強制
- UIコンポーネント新設時はcomponents/金型先確認（ADR-144）→ CI UI governance gate で強制。既存Drawer・Button等を流用し、生select/生input/自作タブ禁止
