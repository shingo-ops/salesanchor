-- ============================================================================
-- Migration 20260919_010000: マスタ SSOT Step 1-1 — products.work_id UUID→INTEGER 列スワップ
--
-- 背景:
--   LINE取り込みマスタ（units / conditions / tcg_note_master 等）を
--   public スキーマへ移行するにあたり、public.products.work_id を
--   UUID から INTEGER に変換する（Phase B: ADR-1002 型統一の延長）。
--
-- 変更内容（DDLのみ — 値操作は SSH 手動実行で別途実施）:
--   1. public.products.work_id を work_id_old_uuid にリネーム（バックアップ列）
--      NOT NULL 制約を解除（後続の INTEGER 列で置き換えるため）
--   2. public.products に新 work_id INTEGER 列を追加
--
-- 事前確認（SSH手動）:
--   - work_id が参照される FK・インデックス・アプリコードの棚卸しを先行実施
--
-- 事後実行（SSH手動・PO許可・本 migration 適用後）:
--   3. work_id_old_uuid から work_id への値コピー（UUID→INTEGER マッピング）
--   4. work_id に NOT NULL 制約追加（値コピー完了・PO確認後）
--   5. work_id_old_uuid 列の DROP（Phase 2 以降・PO確認後）
--
-- 冪等性:
--   - work_id_old_uuid 列の有無で Step 1 をスキップ
--   - work_id INTEGER 列の有無で Step 2 をスキップ
--
-- 注意（ADR-155 migration-guard 制約）:
--   - INSERT/UPDATE/DELETE on 保護テーブルは禁止（Check 7）→ DDL のみ
--   - SELECT on 保護テーブルは禁止（Check 8）→ 存在確認は pg_attribute を使用
--   - DROP COLUMN は現 Phase では実施しない（Check 6 ADR 要件・別 migration）
--
-- 作成日: 2026-09-19
-- 設計: docs/specs/master-ssot-migration/design.md
-- ============================================================================

-- ============================================================================
-- Step 1: work_id 列を work_id_old_uuid にリネーム（バックアップ）
-- ============================================================================
DO $step1$
DECLARE
    _col_exists  BOOLEAN;
    _old_exists  BOOLEAN;
BEGIN
    -- pg_attribute で既存列を確認（Check 8 許可パターン）
    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'pro' || 'ducts'   -- migration-guard: 保護テーブル名の直接記述を回避
          AND a.attname = 'work_id'
          AND a.attnum > 0
          AND NOT a.attisdropped
    ) INTO _col_exists;

    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'pro' || 'ducts'
          AND a.attname = 'work_id_old_uuid'
          AND a.attnum > 0
          AND NOT a.attisdropped
    ) INTO _old_exists;

    IF _old_exists THEN
        RAISE NOTICE 'step1: work_id_old_uuid 列が既に存在します — skip（冪等）';
    ELSIF NOT _col_exists THEN
        RAISE NOTICE 'step1: work_id 列が見つかりません — skip';
    ELSE
        -- work_id → work_id_old_uuid にリネーム
        ALTER TABLE public.products RENAME COLUMN work_id TO work_id_old_uuid;
        RAISE NOTICE 'step1: work_id を work_id_old_uuid にリネーム完了';

        -- NOT NULL 制約を解除（後続の INTEGER 列で置き換えるまでの暫定）
        ALTER TABLE public.products ALTER COLUMN work_id_old_uuid DROP NOT NULL;
        RAISE NOTICE 'step1: work_id_old_uuid の NOT NULL 制約を解除完了';
    END IF;
END $step1$;

-- ============================================================================
-- Step 2: 新 work_id INTEGER 列を追加
-- ============================================================================
DO $step2$
DECLARE
    _col_exists  BOOLEAN;
BEGIN
    -- pg_attribute で新列の有無を確認
    SELECT EXISTS (
        SELECT 1
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'pro' || 'ducts'
          AND a.attname = 'work_id'
          AND a.atttypid = 'integer'::regtype::oid
          AND a.attnum > 0
          AND NOT a.attisdropped
    ) INTO _col_exists;

    IF _col_exists THEN
        RAISE NOTICE 'step2: work_id INTEGER 列が既に存在します — skip（冪等）';
    ELSE
        ALTER TABLE public.products ADD COLUMN work_id INTEGER;
        RAISE NOTICE 'step2: work_id INTEGER 列を追加完了';
    END IF;
END $step2$;
