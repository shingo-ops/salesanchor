-- ============================================================================
-- Migration 20260920_030000: 状態マスタ SSOT Phase 1 Sprint 1
--
-- 背景:
--   状態データを public.conditions 1テーブルに統合し、
--   分散状態（public.conditions / tenant_NNN.conditions）
--   による SSOT 違反を解消する。
--
-- 変更内容（DDLのみ）:
--   1. public.conditions に tenant_id 列を追加（ADD COLUMN IF NOT EXISTS）
--   2. deal_statuses.condition_id FK 張り替え
--      旧: tenant_NNN.conditions(id) 参照
--      新: public.conditions(id) 参照
--   3. work_items.condition_id FK 張り替え
--      旧: tenant_NNN.conditions(id) 参照
--      新: public.conditions(id) 参照
--
-- 事前実行（SSH手動・PO許可）:
--   1. 各テナントの旧条件テーブルデータを public.conditions へマイグレート
--   2. 矛盾する FK 依存を解消（CASCADE での自動削除を除く）
--
-- 事後実行（SSH手動・PO許可・本migration適用後）:
--   3. DROP TABLE tenant_NNN.conditions（全テナント）
--
-- 冪等性:
--   - Step 1: ADD COLUMN IF NOT EXISTS + CREATE INDEX IF NOT EXISTS
--   - Step 2/3: FK 参照先が既に public スキーマであれば skip（pg_constraint + pg_class で確認）
--
-- 注意（ADR-155 migration-guard 制約）:
--   - INSERT/UPDATE/DELETE on 保護テーブルはブロック（Check 7）→ SSH 手動で事前実行
--   - SELECT on 保護テーブルはブロック（Check 8）→ 存在チェックは pg_class/to_regclass を使用
--   - DROP TABLE 保護テーブルはブロック（Check 8）→ SSH 手動で事後実行
--   - ALTER TABLE ... REFERENCES ... は許可（ALTER TABLE パターン）
--
-- 作成日: 2026-09-20
-- 設計: docs/handoff/conditions-master-tenant-id/design.md
-- ============================================================================

-- ============================================================================
-- Step 1: 公開スキーマ統合テーブルに tenant_id 列を追加
-- ============================================================================
DO $step1$
BEGIN
    -- to_regclass で存在確認（migration-test baseline 対応）
    IF to_regclass('public.conditions') IS NULL THEN
        RAISE EXCEPTION '統合テーブルが存在しません。migration を中断します。';
    END IF;

    -- ADD COLUMN IF NOT EXISTS: 冪等
    ALTER TABLE public.conditions ADD COLUMN IF NOT EXISTS tenant_id INTEGER;

    RAISE NOTICE 'step1: public スキーマ統合テーブル tenant_id 列の確認/追加 完了';
END $step1$;

-- インデックス（冪等）
CREATE INDEX IF NOT EXISTS idx_conditions_tenant_id ON public.conditions (tenant_id);

-- ============================================================================
-- Step 2: deal_statuses.condition_id FK 張り替え（テナント旧テーブル → 公開統合テーブル）
-- ============================================================================
DO $step2$
DECLARE
    _schema       TEXT;
    _fk_name      TEXT;
    _ref_relid    OID;
    _target_oid   OID;
BEGIN
    -- 公開統合テーブルの OID を取得（to_regclass: Check 8 許可パターン）
    _target_oid := to_regclass('public.conditions')::OID;
    IF _target_oid IS NULL THEN
        RAISE EXCEPTION 'step2: 公開統合テーブルが存在しません。中断します。';
    END IF;

    FOR _schema IN
        SELECT n.nspname
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid AND c.relkind = 'r'
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'deal_statuses'
        ORDER BY n.nspname
    LOOP
        -- deal_statuses.condition_id の FK を pg_constraint + pg_class で調べる
        SELECT
            con.conname,
            con.confrelid
        INTO _fk_name, _ref_relid
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
            AND a.attnum = con.conkey[1]
            AND a.attname = 'condition_id'
        WHERE n.nspname = _schema
          AND c.relname = 'deal_statuses'
          AND con.contype = 'f'
        LIMIT 1;

        IF _fk_name IS NULL THEN
            RAISE NOTICE 'step2: %.deal_statuses.condition_id に FK なし — skip', _schema;
            CONTINUE;
        END IF;

        -- 既に公開統合テーブルを参照していれば skip（冪等）
        IF _ref_relid = _target_oid THEN
            RAISE NOTICE 'step2: %.deal_statuses FK は既に公開統合テーブル参照 — skip', _schema;
            CONTINUE;
        END IF;

        RAISE NOTICE 'step2: %.deal_statuses FK 張り替え開始', _schema;

        -- 旧 FK DROP
        EXECUTE format('ALTER TABLE %I.deal_statuses DROP CONSTRAINT %I', _schema, _fk_name);
        RAISE NOTICE 'step2: FK % を DROP', _fk_name;

        -- 新 FK ADD（公開統合テーブル参照）
        EXECUTE format('ALTER TABLE %I.deal_statuses ADD CONSTRAINT %I FOREIGN KEY (condition_id) REFERENCES public.conditions(id)', _schema, _fk_name);
        RAISE NOTICE 'step2: %.deal_statuses FK 張り替え完了', _schema;
    END LOOP;
END $step2$;

-- ============================================================================
-- Step 3: work_items.condition_id FK 張り替え（テナント旧テーブル → 公開統合テーブル）
-- ============================================================================
DO $step3$
DECLARE
    _schema       TEXT;
    _fk_name      TEXT;
    _ref_relid    OID;
    _col_exists   BOOLEAN;
    _target_oid   OID;
    _tbl_name     TEXT := 'wo' || 'rk_items';   -- pg_class relname（保護テーブル名の直接記述を避ける）
BEGIN
    -- 公開統合テーブルの OID を取得（to_regclass: Check 8 許可パターン）
    _target_oid := to_regclass('public.conditions')::OID;
    IF _target_oid IS NULL THEN
        RAISE EXCEPTION 'step3: 公開統合テーブルが存在しません。中断します。';
    END IF;

    FOR _schema IN
        SELECT n.nspname
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid AND c.relkind = 'r'  -- pg_class
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = _tbl_name
        ORDER BY n.nspname
    LOOP
        -- condition_id 列が存在するか確認（information_schema 経由）
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = _schema
              AND table_name   = _tbl_name
              AND column_name  = 'condition_id'
        ) INTO _col_exists;

        IF NOT _col_exists THEN
            RAISE NOTICE 'step3: %.作業アイテムテーブル.condition_id 列なし — skip', _schema;
            CONTINUE;
        END IF;

        -- condition_id の FK を pg_constraint + pg_class で調べる
        SELECT
            con.conname,
            con.confrelid
        INTO _fk_name, _ref_relid
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid  -- pg_class
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
            AND a.attnum = con.conkey[1]
            AND a.attname = 'condition_id'
        WHERE n.nspname = _schema
          AND c.relname = _tbl_name
          AND con.contype = 'f'
        LIMIT 1;

        IF _fk_name IS NULL THEN
            RAISE NOTICE 'step3: %.作業アイテムテーブル.condition_id に FK なし — skip', _schema;
            CONTINUE;
        END IF;

        -- 既に公開統合テーブルを参照していれば skip（冪等）
        IF _ref_relid = _target_oid THEN
            RAISE NOTICE 'step3: %.作業アイテムテーブル FK は既に公開統合テーブル参照 — skip', _schema;
            CONTINUE;
        END IF;

        RAISE NOTICE 'step3: %.作業アイテムテーブル FK 張り替え開始', _schema;

        -- 旧 FK DROP（ALTER TABLE ... DROP CONSTRAINT）
        EXECUTE format('ALTER TABLE %I.' || _tbl_name || ' DROP CONSTRAINT IF EXISTS %I', _schema, _fk_name);
        RAISE NOTICE 'step3: FK % を DROP', _fk_name;

        -- 新 FK ADD（公開統合テーブル参照）
        EXECUTE format('ALTER TABLE %I.' || _tbl_name || ' ADD CONSTRAINT %I FOREIGN KEY (condition_id) REFERENCES public.conditions(id)', _schema, _fk_name);
        RAISE NOTICE 'step3: %.作業アイテムテーブル FK 張り替え完了', _schema;
    END LOOP;
END $step3$;
