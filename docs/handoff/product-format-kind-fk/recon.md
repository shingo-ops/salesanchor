# 商品分類ハイブリッド型FK追加 — Recon

## 目的

細分類（product_formats）を大分類（product_kinds）で絞り込めるようにし、商品（products）から中分類（type_master）を直接参照できるようにする。

## 現状（2026-09-22 実測）

| テーブル.カラム | 状態 |
|---|---|
| product_formats.kind_id | 存在しない（grep -rn "kind_id" migrations/ で product_formats への追加なし） |
| products.type_master_id | 存在しない（grep -rn "type_master_id" migrations/ で 0件） |
| product_formats.line_id | 存在する（migrations/20260920_130000:59） |
| type_master.kind_id | 存在する（migrations/20260921_070000） |
| product_lines.kind_id | 存在する（migrations/20260921_140000） |

## 関連ADR

- ADR-155: マイグレーションでのマスタ値INSERT禁止
- ADR-156: 商品分類ツリー設計
