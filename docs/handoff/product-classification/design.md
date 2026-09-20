# design: 商品分類マスタ新設（小分類・細分類）

recon 参照: `docs/handoff/product-classification/recon.md`

---

## 目的

Sales Anchor の商品マスタにおいて、現状「大分類（product_kind）」と「中分類（tcg_type）」までしか  
構造化されていない分類を、RDB マスタテーブルとして「小分類」「細分類」まで拡張する。

4 階層分類の完成形:

| 階層 | 名称 | 実装 |
|------|------|------|
| 大分類 | 商材区分 | `public.products.product_kind`（既存・変更なし） |
| 中分類 | ブランド/種別 | `public.tcg_type_master`（既存・変更なし） |
| 小分類 | 商品系統 | `public.product_lines`（**本 migration で新設**） |
| 細分類 | 商品形態 | `public.product_formats`（**本 migration で新設**） |

---

## 対象と対象外

### 対象

- `public.product_lines` テーブル新設
- `public.product_formats` テーブル新設（`line_id` FK で product_lines に紐付く）
- `public.products` テーブルへの `product_line_id` / `product_format_id` カラム追加（NULLable FK）
- `scripts/run_all_migrations.sh` への migration 登録

### 対象外

- 値（seed データ）の INSERT — ADR-155 により禁止。アプリ UI / CSV import で別途投入
- 既存 products API・フロントエンドの変更 — NULLable カラム追加のみのため不要
- `tcg_type`・`product_kind` の変更 — 触らない

---

## 変更前後

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| `public.product_lines` | 存在しない | SERIAL PK / code UNIQUE / name / name_en / display_order / is_active |
| `public.product_formats` | 存在しない | SERIAL PK / code UNIQUE / name / name_en / line_id FK / display_order / is_active |
| `public.products.product_line_id` | 存在しない | INTEGER NULL REFERENCES product_lines(id) |
| `public.products.product_format_id` | 存在しない | INTEGER NULL REFERENCES product_formats(id) |
| `run_all_migrations.sh` | 最終行 `20260920_120000_analysis_rule_public_tables.sql` | + `20260920_130000_create_product_classification.sql` |

---

## 影響範囲

- 新テーブル: 既存テーブル・API への影響なし
- `products` への NULLable カラム追加: 既存データ行は NULL のまま。既存 SELECT/INSERT/UPDATE への影響なし
- FK `ON DELETE SET NULL`: 分類マスタ削除時も既存商品データは保全
- 呼び出し元全走査: `grep -r "product_line_id\|product_format_id" backend/ frontend/` → 0 件（新規カラムのため既存コードは未参照）

---

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| `product_lines` テーブルが存在する | `\d public.product_lines` でカラム一覧表示 |
| `product_formats` テーブルが存在する | `\d public.product_formats` でカラム一覧表示 |
| `product_formats.line_id` が `product_lines` を参照する | `\d public.product_formats` で FK 確認（"product_lines(id)"） |
| `products.product_line_id` カラムが存在する | `\d public.products` で確認 |
| `products.product_format_id` カラムが存在する | `\d public.products` で確認 |
| 既存 products データに影響なし | `SELECT count(*) FROM public.products` が変更前後で同一 |
| migration が冪等 | 2 回実行してエラーなし |
| `updated_at` トリガが動作する | `INSERT` 後に `UPDATE` して `updated_at` が更新されることを確認 |

---

## 外部事例

RDB の分類マスタ設計において「コード + 名前 + 表示順 + 有効フラグ」の構成は業界標準パターン。  
本プロジェクト内では `migrations/085_create_tcg_type_master.sql` が同一パターンを採用しており、  
`product_lines` / `product_formats` はそのパターンをそのまま踏襲する。  
細分類（`product_formats`）が小分類（`product_lines`）への FK を持つ「親子マスタ」構造は  
ECシステムやMDMの分類テーブルで広く採用される標準設計。

---

## 維持の仕組み（守り手）

- **migration**: `migrations/20260920_130000_create_product_classification.sql`  
  全 DDL が `IF NOT EXISTS` / `DO $$ ... END $$` で冪等。再実行しても安全。
- **registration**: `scripts/run_all_migrations.sh` の末尾に登録済み。  
  デプロイ時に自動実行される。
- **rollback**: migration ファイル末尾の Rollback コメントに手順記載。
