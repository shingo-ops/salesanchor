-- ============================================================================
-- 仕入元マスタ重複解消 — クリーンアップ SQL
--
-- 用途: public.suppliers の line_name 重複を解消する
-- 実行タイミング: UNIQUE インデックス追加のマイグレーション「前」に手動実行
-- 実行先: prod1 (49.212.137.46) jarvis_db
-- 実行者: PO（SSH手動）
-- 冪等: 重複がなければ何もしない
--
-- 本番テナント:
--   tenant_004 = highlife-jpn（本番運用）
--   tenant_006 = tenant_review（デモ用）
--
-- 手順:
--   1. まず DRY-RUN（BEGIN → 確認 → ROLLBACK）で影響を確認
--   2. 問題なければ BEGIN → COMMIT で実行
-- ============================================================================

-- ============================================================================
-- Step 0: 現状確認（DRY-RUN 前に必ず実行）
-- ============================================================================

-- 重複グループの一覧（tenant_004 + tenant_006 の参照件数を表示）
SELECT
    s.line_name,
    s.id,
    s.supplier_code,
    s.name,
    s.created_at,
    (SELECT COUNT(*) FROM tenant_004.source_messages sm WHERE sm.supplier_id = s.id) AS t004_msg,
    (SELECT COUNT(*) FROM tenant_004.supplier_channels sc WHERE sc.supplier_id = s.id) AS t004_ch,
    (SELECT COUNT(*) FROM tenant_006.source_messages sm WHERE sm.supplier_id = s.id) AS t006_msg,
    (SELECT COUNT(*) FROM tenant_006.supplier_channels sc WHERE sc.supplier_id = s.id) AS t006_ch
FROM public.suppliers s
WHERE s.is_active = TRUE
  AND s.tenant_id IS NULL
  AND s.line_name IS NOT NULL
  AND s.line_name IN (
      SELECT line_name
      FROM public.suppliers
      WHERE is_active = TRUE AND tenant_id IS NULL AND line_name IS NOT NULL
      GROUP BY line_name
      HAVING COUNT(*) > 1
  )
ORDER BY s.line_name, s.created_at;

-- ============================================================================
-- Step 1: FK再割当て + 重複の無効化（トランザクション内で実行）
-- ============================================================================

BEGIN;

-- 各重複グループで「最も参照が多い ID」を kept とし、他を duplicate とする
-- kept の選定基準: 全テナント合計の参照数が最大 → 同値なら created_at が最古
WITH dup_groups AS (
    SELECT
        s.id,
        s.line_name,
        s.supplier_code,
        (SELECT COUNT(*) FROM tenant_004.source_messages sm WHERE sm.supplier_id = s.id)
        + (SELECT COUNT(*) FROM tenant_006.source_messages sm WHERE sm.supplier_id = s.id) AS msg_count,
        (SELECT COUNT(*) FROM tenant_004.supplier_channels sc WHERE sc.supplier_id = s.id)
        + (SELECT COUNT(*) FROM tenant_006.supplier_channels sc WHERE sc.supplier_id = s.id) AS ch_count,
        ROW_NUMBER() OVER (
            PARTITION BY s.line_name
            ORDER BY
                (SELECT COUNT(*) FROM tenant_004.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_004.supplier_channels sc WHERE sc.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.supplier_channels sc WHERE sc.supplier_id = s.id) DESC,
                s.created_at ASC
        ) AS rn
    FROM public.suppliers s
    WHERE s.is_active = TRUE
      AND s.tenant_id IS NULL
      AND s.line_name IS NOT NULL
      AND s.line_name IN (
          SELECT line_name
          FROM public.suppliers
          WHERE is_active = TRUE AND tenant_id IS NULL AND line_name IS NOT NULL
          GROUP BY line_name
          HAVING COUNT(*) > 1
      )
),
kept AS (
    SELECT id, line_name FROM dup_groups WHERE rn = 1
),
dupes AS (
    SELECT dg.id AS dup_id, dg.line_name, dg.supplier_code, k.id AS kept_id
    FROM dup_groups dg
    JOIN kept k ON k.line_name = dg.line_name
    WHERE dg.rn > 1
)
-- 確認: kept と dupes の対応表を出力
SELECT
    d.line_name,
    d.kept_id AS "kept (移行先)",
    d.dup_id AS "duplicate (無効化対象)",
    d.supplier_code AS "dup_supplier_code"
FROM dupes d
ORDER BY d.line_name, d.dup_id;

-- FK再割当て: tenant_004.source_messages
WITH dup_groups AS (
    SELECT s.id, s.line_name,
        ROW_NUMBER() OVER (
            PARTITION BY s.line_name
            ORDER BY
                (SELECT COUNT(*) FROM tenant_004.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_004.supplier_channels sc WHERE sc.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.supplier_channels sc WHERE sc.supplier_id = s.id) DESC,
                s.created_at ASC
        ) AS rn
    FROM public.suppliers s
    WHERE s.is_active = TRUE AND s.tenant_id IS NULL AND s.line_name IS NOT NULL
      AND s.line_name IN (
          SELECT line_name FROM public.suppliers
          WHERE is_active = TRUE AND tenant_id IS NULL AND line_name IS NOT NULL
          GROUP BY line_name HAVING COUNT(*) > 1
      )
),
kept AS (SELECT id, line_name FROM dup_groups WHERE rn = 1),
dupes AS (
    SELECT dg.id AS dup_id, k.id AS kept_id
    FROM dup_groups dg JOIN kept k ON k.line_name = dg.line_name WHERE dg.rn > 1
)
UPDATE tenant_004.source_messages sm
SET supplier_id = d.kept_id
FROM dupes d
WHERE sm.supplier_id = d.dup_id;

-- FK再割当て: tenant_006.source_messages
WITH dup_groups AS (
    SELECT s.id, s.line_name,
        ROW_NUMBER() OVER (
            PARTITION BY s.line_name
            ORDER BY
                (SELECT COUNT(*) FROM tenant_004.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_004.supplier_channels sc WHERE sc.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.supplier_channels sc WHERE sc.supplier_id = s.id) DESC,
                s.created_at ASC
        ) AS rn
    FROM public.suppliers s
    WHERE s.is_active = TRUE AND s.tenant_id IS NULL AND s.line_name IS NOT NULL
      AND s.line_name IN (
          SELECT line_name FROM public.suppliers
          WHERE is_active = TRUE AND tenant_id IS NULL AND line_name IS NOT NULL
          GROUP BY line_name HAVING COUNT(*) > 1
      )
),
kept AS (SELECT id, line_name FROM dup_groups WHERE rn = 1),
dupes AS (
    SELECT dg.id AS dup_id, k.id AS kept_id
    FROM dup_groups dg JOIN kept k ON k.line_name = dg.line_name WHERE dg.rn > 1
)
UPDATE tenant_006.source_messages sm
SET supplier_id = d.kept_id
FROM dupes d
WHERE sm.supplier_id = d.dup_id;

-- FK再割当て: tenant_004.supplier_channels
WITH dup_groups AS (
    SELECT s.id, s.line_name,
        ROW_NUMBER() OVER (
            PARTITION BY s.line_name
            ORDER BY
                (SELECT COUNT(*) FROM tenant_004.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_004.supplier_channels sc WHERE sc.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.supplier_channels sc WHERE sc.supplier_id = s.id) DESC,
                s.created_at ASC
        ) AS rn
    FROM public.suppliers s
    WHERE s.is_active = TRUE AND s.tenant_id IS NULL AND s.line_name IS NOT NULL
      AND s.line_name IN (
          SELECT line_name FROM public.suppliers
          WHERE is_active = TRUE AND tenant_id IS NULL AND line_name IS NOT NULL
          GROUP BY line_name HAVING COUNT(*) > 1
      )
),
kept AS (SELECT id, line_name FROM dup_groups WHERE rn = 1),
dupes AS (
    SELECT dg.id AS dup_id, k.id AS kept_id
    FROM dup_groups dg JOIN kept k ON k.line_name = dg.line_name WHERE dg.rn > 1
)
UPDATE tenant_004.supplier_channels sc
SET supplier_id = d.kept_id
FROM dupes d
WHERE sc.supplier_id = d.dup_id;

-- FK再割当て: tenant_006.supplier_channels
WITH dup_groups AS (
    SELECT s.id, s.line_name,
        ROW_NUMBER() OVER (
            PARTITION BY s.line_name
            ORDER BY
                (SELECT COUNT(*) FROM tenant_004.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_004.supplier_channels sc WHERE sc.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.supplier_channels sc WHERE sc.supplier_id = s.id) DESC,
                s.created_at ASC
        ) AS rn
    FROM public.suppliers s
    WHERE s.is_active = TRUE AND s.tenant_id IS NULL AND s.line_name IS NOT NULL
      AND s.line_name IN (
          SELECT line_name FROM public.suppliers
          WHERE is_active = TRUE AND tenant_id IS NULL AND line_name IS NOT NULL
          GROUP BY line_name HAVING COUNT(*) > 1
      )
),
kept AS (SELECT id, line_name FROM dup_groups WHERE rn = 1),
dupes AS (
    SELECT dg.id AS dup_id, k.id AS kept_id
    FROM dup_groups dg JOIN kept k ON k.line_name = dg.line_name WHERE dg.rn > 1
)
UPDATE tenant_006.supplier_channels sc
SET supplier_id = d.kept_id
FROM dupes d
WHERE sc.supplier_id = d.dup_id;

-- 重複レコードを無効化（DELETE ではなく is_active=FALSE）
-- supplier_code を NULL に変更（UNIQUE 制約との衝突防止）
WITH dup_groups AS (
    SELECT s.id, s.line_name,
        ROW_NUMBER() OVER (
            PARTITION BY s.line_name
            ORDER BY
                (SELECT COUNT(*) FROM tenant_004.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.source_messages sm WHERE sm.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_004.supplier_channels sc WHERE sc.supplier_id = s.id)
                + (SELECT COUNT(*) FROM tenant_006.supplier_channels sc WHERE sc.supplier_id = s.id) DESC,
                s.created_at ASC
        ) AS rn
    FROM public.suppliers s
    WHERE s.is_active = TRUE AND s.tenant_id IS NULL AND s.line_name IS NOT NULL
      AND s.line_name IN (
          SELECT line_name FROM public.suppliers
          WHERE is_active = TRUE AND tenant_id IS NULL AND line_name IS NOT NULL
          GROUP BY line_name HAVING COUNT(*) > 1
      )
)
UPDATE public.suppliers
SET is_active = FALSE,
    supplier_code = NULL,
    line_name = line_name || '_dedup_' || id::text  -- 無効化した line_name を一意化
FROM dup_groups dg
WHERE public.suppliers.id = dg.id AND dg.rn > 1;

-- ============================================================================
-- Step 2: 検証（COMMIT 前に必ず確認）
-- ============================================================================

-- 残存する重複がないことを確認（0行であること）
SELECT line_name, COUNT(*)
FROM public.suppliers
WHERE is_active = TRUE AND tenant_id IS NULL AND line_name IS NOT NULL
GROUP BY line_name
HAVING COUNT(*) > 1;

-- deactivated ID を参照する FK が残っていないことを確認（全て0であること）
SELECT 'tenant_004.source_messages' AS tbl, COUNT(*)
FROM tenant_004.source_messages sm
JOIN public.suppliers s ON s.id = sm.supplier_id
WHERE s.is_active = FALSE AND s.line_name LIKE '%_dedup_%'
UNION ALL
SELECT 'tenant_004.supplier_channels', COUNT(*)
FROM tenant_004.supplier_channels sc
JOIN public.suppliers s ON s.id = sc.supplier_id
WHERE s.is_active = FALSE AND s.line_name LIKE '%_dedup_%'
UNION ALL
SELECT 'tenant_006.source_messages', COUNT(*)
FROM tenant_006.source_messages sm
JOIN public.suppliers s ON s.id = sm.supplier_id
WHERE s.is_active = FALSE AND s.line_name LIKE '%_dedup_%'
UNION ALL
SELECT 'tenant_006.supplier_channels', COUNT(*)
FROM tenant_006.supplier_channels sc
JOIN public.suppliers s ON s.id = sc.supplier_id
WHERE s.is_active = FALSE AND s.line_name LIKE '%_dedup_%';

-- 問題なければ:
-- COMMIT;
-- 問題があれば:
-- ROLLBACK;
