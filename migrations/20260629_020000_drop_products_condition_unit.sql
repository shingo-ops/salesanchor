-- スコープ②Phase2: public.products から redundant な condition / unit 列を物理削除。
-- 正本は inventory 側（状態=4軸+raw_condition / 単位=inventory.unit）。
-- 冪等: IF EXISTS。依存ビュー等は事前確認で 0。再実行で no-op。
-- 前提: 20260629_010000 の backfill が先に適用済みであること。
ALTER TABLE public.products DROP COLUMN IF EXISTS condition;
ALTER TABLE public.products DROP COLUMN IF EXISTS unit;
