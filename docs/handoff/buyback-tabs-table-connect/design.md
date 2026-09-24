# Design: カテゴリタブのテーブル連結

## recon参照
docs/handoff/buyback-tabs-table-connect/recon.md

## ADR参照
ADR-144

## 目的
カテゴリタブをDataTableの直上に配置し、タブとテーブルを視覚的に一体化させる。

## 変更内容
- Tabs を ContentToolbar left から DataTable 直上に移動
- variant を "pill" → "underline" に変更（テーブル上辺との視覚的接続）
- DataTable の上角丸を 0 に（CSS modules で border-top-*-radius: 0）
- レイアウト wrapper: CSS modules の .buybackFilterGroup（flex column）

## 対象外
- Tabs コンポーネント本体の変更
- DataTable コンポーネント本体の変更
- バックエンド変更（なし）
- i18n変更（なし）

## 受入条件
| 基準 | 検証方法 |
|------|---------|
| タブがテーブル直上に表示 | 目視確認 |
| タブとテーブルが視覚的に一体化 | 下線とテーブル上辺が接続 |
| タブ切替でデータが切り替わる | 各タブクリックで確認 |
| ADR-144準拠 | classNameに"tab"語なし・色直値なし |

## 維持の仕組み
- 守り手: ADR-144 CI ゲート（自作タブ検出）
- DataTable.className prop は公式APIとして定義済み（DataTable.tsx:65）

## 外部・過去事例
該当なし（レイアウト変更のみ）
