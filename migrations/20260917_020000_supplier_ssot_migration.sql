-- ============================================================================
-- Migration 20260917_020000: 仕入元マスタ SSOT Sprint 1
--
-- 背景:
--   LINE取り込みの仕入元照合先を tenant_*.tcg_suppliers から
--   public.suppliers (INTEGER PK) に移行する。
--
-- 変更内容（DDLのみ — 値操作は SSH 手動実行済み）:
--   1. supplier_channels.supplier_id UUID → INTEGER へ列スワップ
--      (値マッピングは事前スクリプトで実行済み。列の有無で判定)
--   2. public.line_supplier_source_names テーブルを DROP
--
-- 事前実行済み（SSH手動・PO許可）:
--   - 2026-09-17: tcg_suppliers → public.suppliers データコピー（182件）
--   - 2026-09-18: supplier_channels.supplier_int_id 値マッピング
--
-- 冪等性:
--   - supplier_id の列型で判定（INTEGER なら skip）
--   - supplier_int_id の列有無で判定（なければ skip）
--   - DROP TABLE IF EXISTS
--
-- 作成日: 2026-09-17
-- ============================================================================

-- ============================================================================
-- ステップ 1: supplier_channels.supplier_id UUID → INTEGER（列スワップ・DDLのみ）
-- ============================================================================
DO $step1$
DECLARE
    _schema    TEXT;
    _atttypid  OID;
    _int_oid   OID := 'integer'::regtype::oid;
    _fk_name   TEXT;
BEGIN
    FOR _schema IN
        SELECT n.nspname
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid AND c.relkind = 'r'
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'supplier_channels'
        ORDER BY n.nspname
    LOOP
        -- 列の型チェック: supplier_id が INTEGER なら変換済み
        SELECT a.atttypid INTO _atttypid
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = _schema
          AND c.relname = 'supplier_channels'
          AND a.attname = 'supplier_id'
          AND a.attnum > 0;

        IF _atttypid = _int_oid THEN
            RAISE NOTICE 'step1: %.supplier_channels.supplier_id already INTEGER — skip', _schema;
            CONTINUE;
        END IF;

        IF _atttypid IS NULL THEN
            RAISE NOTICE 'step1: %.supplier_channels.supplier_id not found — skip', _schema;
            CONTINUE;
        END IF;

        -- 列の有無チェック: supplier_int_id が存在するか（事前スクリプトで作成済み）
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = _schema
              AND table_name = 'supplier_channels'
              AND column_name = 'supplier_int_id'
        ) THEN
            RAISE NOTICE 'step1: %.supplier_channels.supplier_int_id not found — skip', _schema;
            CONTINUE;
        END IF;

        RAISE NOTICE 'step1: %.supplier_channels DDL swap starting', _schema;

        -- 旧 FK（tcg_suppliers 参照）を削除
        SELECT conname INTO _fk_name
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = _schema
          AND c.relname = 'supplier_channels'
          AND con.contype = 'f'
        LIMIT 1;
        IF _fk_name IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.supplier_channels DROP CONSTRAINT %I', _schema, _fk_name);
            RAISE NOTICE 'step1: FK % dropped', _fk_name;
        END IF;

        -- DDL swap: 旧 UUID カラム削除 → tmp カラムをリネーム → NOT NULL → 新 FK → インデックス
        EXECUTE format('ALTER TABLE %I.supplier_channels DROP COLUMN supplier_id', _schema);
        EXECUTE format('ALTER TABLE %I.supplier_channels RENAME COLUMN supplier_int_id TO supplier_id', _schema);
        EXECUTE format('ALTER TABLE %I.supplier_channels ALTER COLUMN supplier_id SET NOT NULL', _schema);

        EXECUTE format($q$
            ALTER TABLE %I.supplier_channels
            ADD CONSTRAINT fk_supplier_channels_supplier_id
            FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE CASCADE
        $q$, _schema);

        EXECUTE format($q$
            CREATE INDEX IF NOT EXISTS idx_%s_supplier_channels_supplier_id
            ON %I.supplier_channels (supplier_id)
        $q$, _schema, _schema);

        RAISE NOTICE 'step1: %.supplier_channels done', _schema;
    END LOOP;
END $step1$;

-- ============================================================================
-- ステップ 2: public.line_supplier_source_names テーブルを DROP
-- ============================================================================
DROP TABLE IF EXISTS public.line_supplier_source_names;
