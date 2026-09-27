# パイプラインマップ改善 — design

参照: docs/handoff/pipeline-map-readability/recon.md

## 目的
非エンジニアのPOがLINE解析パイプラインの構造を直感的に理解できるよう改善する。

## 変更内容
1. テーブル名を日本語の業務名に変更（ADR-027 i18n準拠）
2. カラム名列挙を廃止し、テーブルの役割説明文に置換
3. ノードサイズを拡大（240px幅）
4. カテゴリ別色分け（8色、CSS変数で定義）
5. ADR-144（UIガバナンス）準拠: CSS変数のみ使用

## 受け入れ基準

| 基準 | 検証方法 |
|------|----------|
| ノードに日本語の業務名が表示される | ブラウザ確認 |
| 各ノードに役割説明が表示される | ブラウザ確認 |
| カテゴリ別に色分けされている | ブラウザ確認 |
| 文字が十分な大きさで読める | ブラウザ確認 |
| CI全緑 | GitHub Actions |

## 対象外
- テナントスキーマテーブルの追加
- マップのインタラクティブ編集機能

## 外部事例
該当なし（既存機能のUI改善のため）

## 維持の仕組み
守り手: frontend/src/pages/super-admin/components/PipelineMapPanel.tsx
CI: ADR-067 dark mode check, UI governance gate, ADR-144準拠
