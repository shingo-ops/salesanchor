-- 試作版 v102: 中分類マスタに「型番で商品を決めるか」の印を足す（構造のみ。値は入れない）
-- 既定は TRUE（今まで通り）。FALSE を付けた中分類は、品番・マーク・それと同じ検索ワードを当たりに使わない。
-- 値の INSERT/UPDATE/DELETE は含めない（デプロイ後に運用の手順で付ける。ADR-155 の方針）

-- CI test-run 用スタブ（空 DB では type_master が無い。本番では既存のため何もしない。
-- 書き方は migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql と同じ）
CREATE TABLE IF NOT EXISTS public.type_master (id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name_ja VARCHAR(100) NOT NULL, name_en VARCHAR(100), sort_order INTEGER NOT NULL DEFAULT 100, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

ALTER TABLE public.type_master
    ADD COLUMN IF NOT EXISTS match_by_code BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN public.type_master.match_by_code
    IS 'FALSE の中分類は試作版 v102 の商品照合で品番・マーク・型番と同じ検索ワードを使わない（商品名だけで決める）。既定 TRUE';
