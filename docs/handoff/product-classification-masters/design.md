# 商品分類マスタ拡張 — Design

- recon: docs/handoff/product-classification-masters/recon.md
- 対象ADR: ADR-155（マスタ値INSERT禁止）、ADR-156（商品分類ツリー）

## 目的

商品の4階層分類（大→中→小→細）と入数・重量マスタを整備し、管理画面から CRUD 操作可能にする。

## 対象と対象外

### 対象

1. DDL: product_lines に kind_id FK 追加
2. DDL: quantity_units テーブル新規作成
3. DDL: weight_classes テーブル新規作成
4. DDL: products に quantity_unit_id, weight_class_id FK 追加
5. Backend: 4テーブルの CRUD API（super_admin ルーター）
6. Frontend: 4テーブルの管理パネル（super-admin 画面）
7. CI: migration-guard.yml に quantity_units, weight_classes を保護テーブル追加
8. i18n: ja.json, en.json にキー追加

### 対象外

- マスタ値の投入（ADR-155: アプリ/CSV経由で投入）
- 既存商品への分類値の紐づけ（別PR）
- CSV取り込みフローの改修（別PR）

## 変更詳細

### Migration: 20260921_140000_product_classification_masters.sql

```sql
-- 1. product_lines に kind_id 追加
ALTER TABLE public.product_lines
  ADD COLUMN IF NOT EXISTS kind_id INTEGER REFERENCES public.product_kinds(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_product_lines_kind_id ON public.product_lines (kind_id);

-- 2. quantity_units（入数マスタ）
CREATE TABLE IF NOT EXISTS public.quantity_units (
  id            SERIAL PRIMARY KEY,
  code          VARCHAR(50)  NOT NULL UNIQUE,
  name          VARCHAR(100) NOT NULL,
  name_en       VARCHAR(100),
  value         INTEGER      NOT NULL,
  display_order INTEGER      NOT NULL DEFAULT 100,
  is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quantity_units_sort ON public.quantity_units (display_order, id);

-- 3. weight_classes（重量マスタ）
CREATE TABLE IF NOT EXISTS public.weight_classes (
  id            SERIAL PRIMARY KEY,
  code          VARCHAR(50)  NOT NULL UNIQUE,
  name          VARCHAR(100) NOT NULL,
  name_en       VARCHAR(100),
  min_grams     INTEGER      NOT NULL DEFAULT 0,
  max_grams     INTEGER,
  display_order INTEGER      NOT NULL DEFAULT 100,
  is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_weight_classes_sort ON public.weight_classes (display_order, id);

-- 4. products に FK 追加
ALTER TABLE public.products
  ADD COLUMN IF NOT EXISTS quantity_unit_id INTEGER REFERENCES public.quantity_units(id) ON DELETE SET NULL;
ALTER TABLE public.products
  ADD COLUMN IF NOT EXISTS weight_class_id INTEGER REFERENCES public.weight_classes(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_products_quantity_unit_id ON public.products (quantity_unit_id);
CREATE INDEX IF NOT EXISTS idx_products_weight_class_id ON public.products (weight_class_id);

-- updated_at トリガ
CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_quantity_units_updated_at') THEN
    CREATE TRIGGER trg_quantity_units_updated_at BEFORE UPDATE ON public.quantity_units
      FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_weight_classes_updated_at') THEN
    CREATE TRIGGER trg_weight_classes_updated_at BEFORE UPDATE ON public.weight_classes
      FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
  END IF;
END $$;
```

### Backend CRUD

4テーブルとも `super_admin_product_kinds.py` と同一パターン:
- GET /super-admin/{resource} — 一覧（is_active フィルタ、ページング）
- POST /super-admin/{resource} — 新規作成
- PATCH /super-admin/{resource}/{id} — 部分更新
- DELETE /super-admin/{resource}/{id} — soft delete（is_active=FALSE）

quantity_units は value カラム（INTEGER）を追加。
weight_classes は min_grams, max_grams カラムを追加。

### Frontend 管理パネル

ProductKindsMasterPanel.tsx と同一パターンで4パネル作成:
- DataTable + Modal + ConfirmModal（ADR-144 金型）
- 全文字列 t() 経由（ADR-027）
- quantity_units: value フィールド追加（数値入力）
- weight_classes: min_grams, max_grams フィールド追加（数値入力）

### migration-guard.yml

Check 8 PROTECTED_TABLES に `quantity_units|weight_classes` を追加。
Check 4 PUBLIC_TABLES に `quantity_units` `weight_classes` を追加。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| product_lines に kind_id カラムが存在する | `\d public.product_lines` で kind_id INTEGER 確認 |
| quantity_units テーブルが存在する | `\d public.quantity_units` で全カラム確認 |
| weight_classes テーブルが存在する | `\d public.weight_classes` で全カラム確認 |
| products に quantity_unit_id, weight_class_id がある | `\d public.products` で確認 |
| CRUD API が動作する | 各エンドポイント GET/POST/PATCH/DELETE 200応答 |
| 管理画面で4テーブルの一覧・追加・編集・削除ができる | ブラウザ操作で確認 |
| migration-guard が quantity_units, weight_classes を保護する | テスト migration で CI が赤になる |
| i18n キーが ja.json, en.json に存在する | grep で確認 |

## 外部事例

該当なし（内部マスタCRUDの標準パターン踏襲。外部事例が不要な理由: 既存の product_kinds CRUD が本リポジトリ内の実証済みパターン）

## 守り手

- migration-guard.yml Check 8: quantity_units, weight_classes への値INSERT を CI で自動ブロック
- super_admin 権限ガード: 全エンドポイントに require_super_admin 依存
- 既存パターン踏襲のため新規の仕組み不要
