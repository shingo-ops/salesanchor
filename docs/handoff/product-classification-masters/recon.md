# 商品分類マスタ拡張 — Recon

## 目的

商品を「大分類→中分類→小分類→細分類」の4階層で分類し、入数・重量も選択式マスタで管理する。売上分析・検索・集計の軸を整備する。

## 現状（2026-09-21 実測）

### 既存テーブル

| テーブル | 状態 | カラム | 行数 |
|---------|------|--------|------|
| product_kinds（大分類） | 稼働中 | id, code, name, name_en, display_order, is_active | 3件（TCG/FIGURE/GOODS） |
| type_master（中分類） | 稼働中 | id, code, name, name_en, kind_id→product_kinds, display_order, is_active | 12件 |
| product_lines（小分類） | DDL済み・空 | id, code, name, name_en, type_id→type_master, display_order, is_active | 0件 |
| product_formats（細分類） | DDL済み・空 | id, code, name, name_en, line_id→product_lines, display_order, is_active | 0件 |

### 不足

1. product_lines に kind_id（大分類FK）がない — 中分類と小分類は独立軸だが、小分類→大分類の直接リンクが未実装
   - 根拠: `migrations/20260921_080000_product_lines_add_type_id.sql` — type_id のみ追加、kind_id なし
2. quantity_units（入数マスタ）テーブルが存在しない
   - 根拠: `grep -rn "quantity_units" migrations/` — 0件
3. weight_classes（重量マスタ）テーブルが存在しない
   - 根拠: `grep -rn "weight_classes" migrations/` — 0件
4. products テーブルに quantity_unit_id, weight_class_id カラムがない
   - 根拠: `migrations/20260920_130000_create_product_classification.sql` — product_line_id, product_format_id のみ
5. 4テーブル（product_lines, product_formats, quantity_units, weight_classes）のCRUD API・管理画面がない
   - 根拠: `grep -rn "product_lines\|product_formats\|quantity_units\|weight_classes" backend/app/routers/` — 0件

### 関連ADR

- ADR-155: マイグレーションでのマスタ値INSERT禁止（CSV/アプリ経由のみ）
- ADR-156: 商品分類ツリー全体設計（Phase 1-5）
- ADR-027: UI文字列は t("key") 経由必須
- ADR-144: UI金型遵守（生select/生input禁止）

### 参照パターン

- CRUD API: `backend/app/routers/super_admin_product_kinds.py`（155行）
- Schema: `backend/app/schemas/product_kind.py`（37行）
- 管理画面: `frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx`（265行）
- ルーター登録: `backend/app/main.py:526` — `app.include_router(..., prefix="/api/v1", tags=["super-admin"])`
