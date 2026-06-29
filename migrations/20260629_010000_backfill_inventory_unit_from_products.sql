-- スコープ②Phase2: public.products.unit を DROP する前に、在庫(public.inventory)で
-- 単位が空のまま商品マスタの unit にフォールバック表示していた行を、在庫側へ退避する。
-- 冪等: i.unit が空(NULL/'')の行だけを対象。既存値は上書きしない。再実行で no-op。
-- 列存在ガード: products.unit / inventory.unit が既に DROP 済みの環境（CI テスト DB 等）では
--   何も実行しない（本番は 2026-06-29 に適用済み・UPDATE 62 確認済み）。
-- 想定影響行数: 62（2026-06-29 本番実測）。
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'unit'
  ) AND EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = 'inventory' AND column_name = 'unit'
  ) THEN
    UPDATE public.inventory i
       SET unit = p.unit
      FROM public.products p
     WHERE i.product_id = p.id
       AND (i.unit IS NULL OR i.unit = '')
       AND p.unit IS NOT NULL;
  END IF;
END;
$$;
