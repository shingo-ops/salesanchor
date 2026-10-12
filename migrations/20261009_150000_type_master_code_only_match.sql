-- 試作版 v102: 中分類マスタに「型番だけでも商品を決めてよいか」の印を足す（構造のみ。値は入れない）
-- 既定は TRUE（match_by_code = TRUE の中分類は、名前の候補が無いとき型番だけでも決めてよい）。
-- FALSE を付けた中分類（match_by_code = TRUE のもの）は、型番を名前の候補の絞り込みだけに使う。
-- 値の INSERT/UPDATE/DELETE は含めない（デプロイ後に運用の手順で付ける。ADR-155・ADR-1007 の方針）

-- CI test-run 用スタブ（空 DB では type_master が無い。本番では既存のため何もしない。
-- 書き方は migrations/20261009_100000_type_master_match_by_code.sql と同じ）
CREATE TABLE IF NOT EXISTS public.type_master (id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name_ja VARCHAR(100) NOT NULL, name_en VARCHAR(100), sort_order INTEGER NOT NULL DEFAULT 100, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

ALTER TABLE public.type_master
    ADD COLUMN IF NOT EXISTS code_only_match BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN public.type_master.code_only_match
    IS '試作版 v102 の商品照合で、名前の候補が無いとき型番（品番・マーク）だけで商品を決めてよいか。TRUE=決めてよい、FALSE=型番は名前の候補の絞り込みだけに使う。match_by_code=FALSE の中分類では使わない。既定 TRUE';
