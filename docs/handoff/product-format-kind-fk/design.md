# 商品分類ハイブリッド型FK追加 — Design

- recon: docs/handoff/product-format-kind-fk/recon.md
- 対象ADR: ADR-155、ADR-156

## 目的

ハイブリッド型商品分類の完成。分類マスタは大分類で絞り込み、商品は6分類を全て直接持つ。

## 対象

1. DDL: product_formats に kind_id FK 追加
2. DDL: products に type_master_id FK 追加

## 対象外

- CRUD API の改修（既存の product_formats ルーターに kind_id 対応は別PR）
- 管理画面の絞り込みUI改修（別PR）
- 既存商品への値設定（別PR）

## 変更前後

| テーブル.カラム | 変更前 | 変更後 |
|---|---|---|
| product_formats.kind_id | なし | INTEGER FK → product_kinds(id) |
| products.type_master_id | なし | INTEGER FK → type_master(id) |

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| product_formats に kind_id カラムが存在する | \d public.product_formats で確認 |
| products に type_master_id カラムが存在する | \d public.products で確認 |
| 両カラムにインデックスが存在する | \di で確認 |

## 外部・過去事例の参照と我々への応用

該当なし（既存パターンの2カラム追加のみ）

## 維持の仕組み

- migration-guard.yml Check 4/8 で product_formats, type_master は既に保護対象
- 既存の CRUD API パターンで kind_id, type_master_id を公開予定（別PR）
