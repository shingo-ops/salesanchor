-- ===========================================================================
-- cleanup-product-duplicates.sql
-- 一回限り実行スクリプト: unify_tcg_products_to_public.sql (PR #3503) で
-- 発生した public.products の重複レコード 203 件を削除し、
-- FK 参照を正しい keep_id へ付け替える。
--
-- 実行方法（本番サーバーで SSH 越しに実行）:
--   ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@49.212.137.46 \
--     "cd /home/ubuntu/salesanchor && docker compose exec -T postgres \
--      psql -U jarvis -d jarvis_db" \
--     < scripts/one-time/cleanup-product-duplicates.sql
--
-- 冪等性: 2回目以降は mapping が空になるため UPDATE/DELETE は 0 行で安全。
-- ===========================================================================

-- ===========================================================================
-- Step 0: ドライランカウント (SELECT のみ・変更なし)
-- 実際に BEGIN する前に影響行数を目視確認すること。
-- 期待値: deletes=203 / ar=~5032 / psk=~430 / pek=~133
-- ===========================================================================

\echo '=== Step 0: ドライラン (変更なし) ==='

\echo '--- 削除対象の PM0### 重複レコード数 (期待値: 203) ---'
SELECT COUNT(*) AS pm_duplicates_to_delete
FROM public.products p_new
WHERE p_new.product_code ~ '^PM[0-9]'
AND EXISTS (
  SELECT 1 FROM public.products p_old
  WHERE p_old.name = p_new.name
    AND p_old.id != p_new.id
    AND (p_old.product_code IS NULL OR p_old.product_code !~ '^PM[0-9]')
);

\echo '--- analysis_results の付け替え対象数 (期待値: ~5032) ---'
SELECT COUNT(*) AS analysis_results_refs
FROM tenant_004.analysis_results ar
JOIN public.products p_new ON ar.product_id = p_new.id
WHERE p_new.product_code ~ '^PM[0-9]'
AND EXISTS (
  SELECT 1 FROM public.products p_old
  WHERE p_old.name = p_new.name
    AND p_old.id != p_new.id
    AND (p_old.product_code IS NULL OR p_old.product_code !~ '^PM[0-9]')
);

\echo '--- product_search_keywords の付け替え対象数 (期待値: ~430) ---'
SELECT COUNT(*) AS search_keywords_refs
FROM tenant_004.product_search_keywords psk
JOIN public.products p_new ON psk.product_id = p_new.id
WHERE p_new.product_code ~ '^PM[0-9]'
AND EXISTS (
  SELECT 1 FROM public.products p_old
  WHERE p_old.name = p_new.name
    AND p_old.id != p_new.id
    AND (p_old.product_code IS NULL OR p_old.product_code !~ '^PM[0-9]')
);

\echo '--- product_exclude_keywords の付け替え対象数 (期待値: ~133) ---'
SELECT COUNT(*) AS exclude_keywords_refs
FROM tenant_004.product_exclude_keywords pek
JOIN public.products p_new ON pek.product_id = p_new.id
WHERE p_new.product_code ~ '^PM[0-9]'
AND EXISTS (
  SELECT 1 FROM public.products p_old
  WHERE p_old.name = p_new.name
    AND p_old.id != p_new.id
    AND (p_old.product_code IS NULL OR p_old.product_code !~ '^PM[0-9]')
);

-- ===========================================================================
-- ここから BEGIN...COMMIT ブロック (全 Step が成功した場合のみ COMMIT)
-- ===========================================================================
BEGIN;

-- ---------------------------------------------------------------------------
-- Step 1: 重複マッピングテーブルを作成
--   delete_id: 削除対象 (PM0### コードを持つ後から追加されたレコード)
--   keep_id  : 残す既存レコード (PM0### コードを持たない、IDが最小のもの)
-- ---------------------------------------------------------------------------

CREATE TEMP TABLE duplicate_mapping AS
SELECT
  p_new.id AS delete_id,
  (
    SELECT p_old.id
    FROM public.products p_old
    WHERE p_old.name = p_new.name
      AND p_old.id != p_new.id
      AND (p_old.product_code IS NULL OR p_old.product_code !~ '^PM[0-9]')
    ORDER BY p_old.id ASC
    LIMIT 1
  ) AS keep_id
FROM public.products p_new
WHERE p_new.product_code ~ '^PM[0-9]'
AND EXISTS (
  SELECT 1 FROM public.products p_old
  WHERE p_old.name = p_new.name
    AND p_old.id != p_new.id
    AND (p_old.product_code IS NULL OR p_old.product_code !~ '^PM[0-9]')
);

-- 安全チェック: keep_id が NULL の行があれば即ロールバック
DO $$
DECLARE
  null_count INT;
  mapping_count INT;
BEGIN
  SELECT COUNT(*) INTO null_count
  FROM duplicate_mapping
  WHERE keep_id IS NULL;

  IF null_count > 0 THEN
    RAISE EXCEPTION
      'keep_id が NULL の行が % 件あります。マッピング条件を見直してください。ROLLBACK します。',
      null_count;
  END IF;

  SELECT COUNT(*) INTO mapping_count FROM duplicate_mapping;
  RAISE NOTICE 'Step 1 完了: mapping 行数 = % (期待値 203)', mapping_count;
END $$;

-- ---------------------------------------------------------------------------
-- Step 2: FK 参照を keep_id へ付け替える (3 テーブル)
-- ---------------------------------------------------------------------------

-- 2-a. analysis_results
DO $$
DECLARE affected INT;
BEGIN
  UPDATE tenant_004.analysis_results ar
  SET product_id = m.keep_id
  FROM duplicate_mapping m
  WHERE ar.product_id = m.delete_id;
  GET DIAGNOSTICS affected = ROW_COUNT;
  RAISE NOTICE 'Step 2-a: analysis_results 更新行数 = % (期待値 ~5032)', affected;
END $$;

-- 2-b. product_search_keywords
DO $$
DECLARE affected INT;
BEGIN
  UPDATE tenant_004.product_search_keywords psk
  SET product_id = m.keep_id
  FROM duplicate_mapping m
  WHERE psk.product_id = m.delete_id;
  GET DIAGNOSTICS affected = ROW_COUNT;
  RAISE NOTICE 'Step 2-b: product_search_keywords 更新行数 = % (期待値 ~430)', affected;
END $$;

-- 2-c. product_exclude_keywords
DO $$
DECLARE affected INT;
BEGIN
  UPDATE tenant_004.product_exclude_keywords pek
  SET product_id = m.keep_id
  FROM duplicate_mapping m
  WHERE pek.product_id = m.delete_id;
  GET DIAGNOSTICS affected = ROW_COUNT;
  RAISE NOTICE 'Step 2-c: product_exclude_keywords 更新行数 = % (期待値 ~133)', affected;
END $$;

-- ---------------------------------------------------------------------------
-- Step 3: 重複レコード (PM0### 側) を削除
-- ---------------------------------------------------------------------------
DO $$
DECLARE deleted_count INT;
BEGIN
  DELETE FROM public.products
  WHERE id IN (SELECT delete_id FROM duplicate_mapping);
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RAISE NOTICE 'Step 3 完了: 削除行数 = % (期待値 203)', deleted_count;
END $$;

-- ---------------------------------------------------------------------------
-- Step 4: 検証クエリ (COMMIT 前に目視確認)
-- ---------------------------------------------------------------------------

\echo '=== Step 4: 検証 ==='

-- 4-a. 残存重複ゼロ確認 (PM0### vs 非 PM0### の同名ペア)
--   期待値: 0 行
\echo '--- 4-a: PM0### vs 非PM0### の残存重複 (期待値: 0 行) ---'
SELECT name, COUNT(*) AS dup_count
FROM public.products
WHERE name IN (
  SELECT p1.name
  FROM public.products p1
  JOIN public.products p2 ON p1.name = p2.name AND p1.id != p2.id
  WHERE p1.product_code ~ '^PM[0-9]'
    AND (p2.product_code IS NULL OR p2.product_code !~ '^PM[0-9]')
)
GROUP BY name
HAVING COUNT(*) > 1
ORDER BY dup_count DESC;

-- 4-b. 総レコード数確認
\echo '--- 4-b: 総レコード数 ---'
SELECT COUNT(*) AS total_products FROM public.products;

-- 4-c. 'ムニキスゼロ' が 1 件であることを確認 (期待値: 1)
\echo '--- 4-c: ムニキスゼロ検索 (期待値: 1 件) ---'
SELECT id, product_code, name, mark
FROM public.products
WHERE name LIKE '%ムニキスゼロ%';

-- ===========================================================================
-- 問題なければ COMMIT。疑問があれば ROLLBACK に変更して再実行。
-- ===========================================================================
\echo '=== 上記結果を確認してください。問題なければ COMMIT が実行されます。 ==='
COMMIT;
\echo '=== COMMIT 完了 ==='
