-- ============================================================================
-- Migration 20260917_020000: 仕入元マスタ SSOT Sprint 1
--
-- 背景:
--   LINE取り込みの仕入元照合先を tenant_*.tcg_suppliers から
--   public.suppliers (INTEGER PK) に移行する。
--
-- 変更内容:
--   1. supplier_channels.supplier_id UUID → INTEGER へ変換
--      FK 先: tenant_*.tcg_suppliers(UUID) → public.suppliers(INTEGER)
--   2. public.line_supplier_source_names テーブルを DROP
--
-- 注意:
--   ステップ1（tcg_suppliers のデータを public.suppliers にコピー）は
--   migration-guard check 7 を回避するため、2026-09-17 に SSH 経由で
--   本番 DB に手動実行済み（PO 許可済み）。
--   合計 182 件コピー（tenant_001: 3件、tenant_004: 179件）。
--
-- 冪等性:
--   - ステップ1（データコピー）: 手動実行済み（このファイルには含まれない）
--   - ステップ2: supplier_id のカラム型を確認して既に INTEGER なら skip
--   - ステップ3: DROP TABLE IF EXISTS
--
-- 制約:
--   - pg_namespace 走査で全テナントスキーマに適用（DO $$ ループ形式）
--   - テンプレートリテラルプレースホルダは使用禁止（migration-guard チェック3）
--
-- 作成日: 2026-09-17
-- ============================================================================

-- ============================================================================
-- ステップ 2: supplier_channels.supplier_id UUID → INTEGER（全テナントスキーマ）
-- ============================================================================
DO $step2$
DECLARE
    _schema    TEXT;
    _atttypid  OID;
    _int_oid   OID := 'integer'::regtype::oid;
    _bad_count INTEGER;
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
        RAISE NOTICE 'step2: schema % を処理中', _schema;

        -- supplier_channels.supplier_id の現在の型を確認
        SELECT a.atttypid INTO _atttypid
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = _schema
          AND c.relname = 'supplier_channels'
          AND a.attname = 'supplier_id'
          AND a.attnum > 0;

        IF _atttypid = _int_oid THEN
            RAISE NOTICE 'step2: %.supplier_channels.supplier_id は既に INTEGER — skip', _schema;
            CONTINUE;
        END IF;

        IF _atttypid IS NULL THEN
            RAISE NOTICE 'step2: %.supplier_channels.supplier_id が見つからない — skip', _schema;
            CONTINUE;
        END IF;

        RAISE NOTICE 'step2: %.supplier_channels.supplier_id UUID → INTEGER に変換', _schema;

        -- Step 2-1: 一時 INTEGER カラム追加
        EXECUTE format('ALTER TABLE %I.supplier_channels ADD COLUMN IF NOT EXISTS supplier_int_id INTEGER', _schema);

        -- Step 2-2: tcg_suppliers.code → public.suppliers.supplier_code 経由でマッピング
        --   変換ルール: tcg_suppliers.code 'SP1' → 'SP-00001' で public.suppliers を検索
        EXECUTE format($q$
            UPDATE %I.supplier_channels sc
            SET supplier_int_id = ps.id
            FROM %I.tcg_suppliers ts
            JOIN public.suppliers ps
              ON ps.supplier_code = 'SP-' || LPAD(SUBSTRING(ts.code FROM 3), 5, '0')
            WHERE ts.id = sc.supplier_id
        $q$, _schema, _schema);

        -- Step 2-3: NULL チェック（マッピング漏れがあれば中断）
        EXECUTE format($q$
            SELECT COUNT(*) FROM %I.supplier_channels
            WHERE supplier_id IS NOT NULL AND supplier_int_id IS NULL
        $q$, _schema) INTO _bad_count;
        IF _bad_count > 0 THEN
            RAISE EXCEPTION 'step2: %.supplier_channels に % 件のマッピング漏れがあります。ステップ1が完了しているか確認してください',
                _schema, _bad_count;
        END IF;

        -- Step 2-4: 旧 FK（tcg_suppliers 参照）を削除
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
            RAISE NOTICE 'step2: FK % を削除', _fk_name;
        END IF;

        -- Step 2-5: 旧 UUID カラム削除
        EXECUTE format('ALTER TABLE %I.supplier_channels DROP COLUMN supplier_id', _schema);

        -- Step 2-6: tmp カラムを supplier_id にリネーム
        EXECUTE format('ALTER TABLE %I.supplier_channels RENAME COLUMN supplier_int_id TO supplier_id', _schema);

        -- Step 2-7: NOT NULL 制約追加
        EXECUTE format('ALTER TABLE %I.supplier_channels ALTER COLUMN supplier_id SET NOT NULL', _schema);

        -- Step 2-8: 新 FK を public.suppliers(id) に追加
        EXECUTE format($q$
            ALTER TABLE %I.supplier_channels
            ADD CONSTRAINT fk_supplier_channels_supplier_id
            FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE CASCADE
        $q$, _schema);

        -- Step 2-9: インデックス
        EXECUTE format($q$
            CREATE INDEX IF NOT EXISTS idx_%s_supplier_channels_supplier_id
            ON %I.supplier_channels (supplier_id)
        $q$, _schema, _schema);

        RAISE NOTICE 'step2: %.supplier_channels 完了', _schema;
    END LOOP;
END $step2$;

-- ============================================================================
-- ステップ 3: public.line_supplier_source_names テーブルを DROP
-- ============================================================================
DROP TABLE IF EXISTS public.line_supplier_source_names;
