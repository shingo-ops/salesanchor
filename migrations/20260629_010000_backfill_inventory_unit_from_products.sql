-- スコープ②Phase2: public.products.unit を DROP する前に、在庫(public.inventory)で
-- 単位が空のまま商品マスタの unit にフォールバック表示していた行を、在庫側へ退避する。
-- 冪等: i.unit が空(NULL/'')の行だけを対象。既存値は上書きしない。再実行で no-op。
-- 想定影響行数: 62（2026-06-29 本番実測）。
UPDATE public.inventory i
   SET unit = p.unit
  FROM public.products p
 WHERE i.product_id = p.id
   AND (i.unit IS NULL OR i.unit = '')
   AND p.unit IS NOT NULL;
