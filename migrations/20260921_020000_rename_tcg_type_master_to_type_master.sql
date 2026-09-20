-- ============================================================================
-- Migration 20260921_020000: tcg_type_master → type_master リネーム
--
-- ADR-156: 商品分類ツリー Phase 1
--   tcg_type_master を中分類マスタ type_master として汎用化する。
--   移行期間中（2026-12-21 まで）は互換ビュー public.tcg_type_master を残す。
--
-- 関連トリガ: trigger_set_updated_at_tcg_type_master（migration 085 で作成）
--   → DB 上のトリガはテーブルに紐付くため、テーブルリネームで自動追従する。
--   → 関数 public.set_updated_at_tcg_type_master() はリネームして整合性を保つ。
--
-- ADR-155 準拠: seed なし（値の投入は CSV アプリ経由）
-- 冪等性: DO $$ BEGIN ... END $$ ガード / CREATE OR REPLACE / IF NOT EXISTS
-- ============================================================================

-- === 1. テーブルリネーム（冪等ガード付き）===
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'tcg_type_master'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'type_master'
    ) THEN
        ALTER TABLE public.tcg_type_master RENAME TO type_master;
        RAISE NOTICE 'Renamed public.tcg_type_master → public.type_master';
    ELSE
        RAISE NOTICE 'Rename skipped: tcg_type_master absent or type_master already exists';
    END IF;
END $$;

-- === 2. トリガ関数リネーム（冪等ガード付き）===
-- 既存関数 set_updated_at_tcg_type_master を set_updated_at_type_master に置き換える
CREATE OR REPLACE FUNCTION public.set_updated_at_type_master()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

-- type_master テーブルが存在する場合にトリガを再作成（リネーム後の整合）
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'type_master'
    ) THEN
        DROP TRIGGER IF EXISTS trigger_set_updated_at_tcg_type_master ON public.type_master;
        DROP TRIGGER IF EXISTS trg_type_master_updated_at ON public.type_master;
        CREATE TRIGGER trg_type_master_updated_at
            BEFORE UPDATE ON public.type_master
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_type_master();
        RAISE NOTICE 'trigger_set_updated_at_tcg_type_master replaced with trg_type_master_updated_at';
    END IF;
END $$;

-- === 3. 互換ビュー（移行期間3か月、2026-12-21以降にDROP予定）===
CREATE OR REPLACE VIEW public.tcg_type_master AS SELECT * FROM public.type_master;
COMMENT ON VIEW public.tcg_type_master IS '互換ビュー: ADR-156 移行期間用（2026-12-21以降に DROP 予定）';

-- === 4. kind_id FK 追加（大分類への紐付け）===
ALTER TABLE public.type_master ADD COLUMN IF NOT EXISTS kind_id INTEGER REFERENCES public.product_kinds(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_type_master_kind_id ON public.type_master (kind_id);

-- ============================================================================
-- Rollback:
--   DROP INDEX IF EXISTS idx_type_master_kind_id;
--   ALTER TABLE public.type_master DROP COLUMN IF EXISTS kind_id;
--   DROP VIEW IF EXISTS public.tcg_type_master;
--   DROP TRIGGER IF EXISTS trg_type_master_updated_at ON public.type_master;
--   DROP FUNCTION IF EXISTS public.set_updated_at_type_master();
--   -- テーブルを元に戻す場合:
--   ALTER TABLE public.type_master RENAME TO tcg_type_master;
-- ============================================================================
