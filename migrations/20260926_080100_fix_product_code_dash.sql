-- ============================================================================
-- Migration 20260926_080100: product_id=61 の product_code='-' を修正
--
-- 30th BOX のバグ根本原因: product_code が '-' のため _resolve_pid が
-- 商品を特定できなかった。'S-PS' に修正する（条件付き・冪等）。
-- ============================================================================
UPDATE public.products
SET product_code = 'S-PS', updated_at = NOW()
WHERE id = 61 AND product_code = '-';

-- ============================================================================
-- Rollback:
--   UPDATE public.products SET product_code = '-', updated_at = NOW()
--   WHERE id = 61 AND product_code = 'S-PS';
-- ============================================================================
