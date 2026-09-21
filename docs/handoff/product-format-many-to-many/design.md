# 細分類→中分類 多対多化 — Design

- recon: docs/handoff/product-format-many-to-many/recon.md
- 対象ADR: ADR-155、ADR-156

## 目的

細分類の重複排除。1つの細分類を複数の中分類に紐づけ可能にする。

## 対象

1. DDL: product_format_game_links 中間テーブル作成
2. CI: migration-guard.yml に保護テーブル追加

## 対象外

- 既存データの統合（本番DB直接操作で実施）
- CRUD API改修（別PR）
- 管理画面改修（別PR）

## 変更前後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 細分類→中分類 | product_formats.type_master_id（1対1） | product_format_game_links（多対多） |
| 細分類件数 | 38件（重複あり） | 16件（重複なし） |
| ゲーム別呼び名 | 別レコードとして存在 | alias カラムで管理 |

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| product_format_game_links テーブルが存在する | \d public.product_format_game_links で確認 |
| format_id + type_master_id の複合PK | \d で PK 確認 |
| alias カラムが存在する | \d で確認 |

## 外部・過去事例の参照と我々への応用

該当なし（標準的な多対多中間テーブルパターン）

## 維持の仕組み

- migration-guard.yml Check 4/8 で product_format_game_links を保護
- FK CASCADE で整合性保証
