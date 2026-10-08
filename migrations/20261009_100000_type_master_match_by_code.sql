-- 試作版 v102: 中分類マスタに「型番で商品を決めるか」の印を足す（構造のみ。値は入れない）
-- 既定は TRUE（今まで通り）。FALSE を付けた中分類は、品番・マーク・それと同じ検索ワードを当たりに使わない。
-- 値の INSERT/UPDATE/DELETE は含めない（デプロイ後に運用の手順で付ける。ADR-155 の方針）

ALTER TABLE public.type_master
    ADD COLUMN IF NOT EXISTS match_by_code BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN public.type_master.match_by_code
    IS 'FALSE の中分類は試作版 v102 の商品照合で品番・マーク・型番と同じ検索ワードを使わない（商品名だけで決める）。既定 TRUE';
