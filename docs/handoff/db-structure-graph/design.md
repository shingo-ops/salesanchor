# DB構造グラフ — design

参照: docs/handoff/db-structure-graph/recon.md

## 目的
LINE解析パイプラインのテーブル関連を視覚的なマップで表示し、POがシステム構造を直感的に把握できるようにする。

## 変更内容
1. @xyflow/react（React Flow）ライブラリを導入
2. PipelineMapPanel コンポーネントを新規作成
3. サイドメニューに「パイプラインマップ」を追加
4. ノードクリックでDrawer経由のテーブル詳細表示
5. tokens.css にパイプラインマップ専用サイズトークンを追加（ADR-067準拠）

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

## 外部事例
React Flow は GitHub Stars 27k+、npm 週間DL 400k+ の実績あるグラフ描画ライブラリ。

## 守り手
- frontend/src/pages/super-admin/components/PipelineMapPanel.tsx — UI側
- frontend/src/tokens.css — デザイントークン定義
- backend/app/routers/super_admin_db_schema.py — API側（テーブル詳細取得）
- CI: ADR-067 dark mode check, UI governance gate
