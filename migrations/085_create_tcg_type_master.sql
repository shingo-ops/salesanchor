-- ============================================================================
-- Migration 085: public.tcg_type_master 新設 + tcg_series_master の tcg_type CHECK 撤廃
--
-- ADR-083: TCG シリーズの「種別」(ポケモンカード / ワンピース 等) を、固定 CHECK 制約から
--   マスタ表 + UI 管理へ移行し、種別自体を増減可能にする。
--
-- 冪等性:
--   - CREATE TABLE / CREATE INDEX IF NOT EXISTS
--   - 種別 seed は ON CONFLICT (code) DO NOTHING
--   - CHECK 制約 DROP は DROP CONSTRAINT IF EXISTS + to_regclass ガード
-- ============================================================================

-- === 1. 種別マスタ ===
-- ADR-156 Phase 2 互換ガード: tcg_type_master が VIEW (relkind='v') に変わっている場合は
-- type_master に対して操作する（CI 並列テスト時に旧 migration が実行される状況への対処）。
DO $$
DECLARE
    _target TEXT;
    _relkind CHAR(1);
BEGIN
    SELECT relkind INTO _relkind
      FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public' AND c.relname = 'tcg_type_master';

    IF _relkind = 'v' THEN
        -- tcg_type_master はビュー (互換ビュー) → type_master を操作
        _target := 'type_master';
    ELSE
        _target := 'tcg_type_master';
    END IF;

    EXECUTE format('
        CREATE TABLE IF NOT EXISTS public.%I (
            id          SERIAL PRIMARY KEY,
            code        VARCHAR(50)  NOT NULL UNIQUE,
            name_ja     VARCHAR(100) NOT NULL,
            name_en     VARCHAR(100),
            sort_order  INTEGER      NOT NULL DEFAULT 100,
            is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )', _target);

    EXECUTE format('
        CREATE INDEX IF NOT EXISTS idx_%s_sort ON public.%I (sort_order, id)',
        _target, _target);

    EXECUTE format('
        INSERT INTO public.%I (code, name_ja, name_en, sort_order) VALUES
            (''pokemon_booster_box'', ''ポケモンカード'',   ''Pokémon Card'',    10),
            (''one_piece'',           ''ワンピース'',       ''One Piece TCG'',   20),
            (''dragon_ball'',         ''ドラゴンボール'',   ''Dragon Ball TCG'', 30),
            (''union_arena'',         ''ユニオンアリーナ'', ''Union Arena'',     40),
            (''yugioh'',              ''遊戯王'',           ''Yu-Gi-Oh!'',       50),
            (''other'',               ''その他'',           ''Other'',           900)
        ON CONFLICT (code) DO NOTHING', _target);

    EXECUTE format('
        CREATE OR REPLACE FUNCTION public.set_updated_at_%s()
        RETURNS TRIGGER AS $upd$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $upd$ LANGUAGE plpgsql', _target);

    EXECUTE format('
        DROP TRIGGER IF EXISTS trigger_set_updated_at_%s ON public.%I',
        _target, _target);

    EXECUTE format('
        CREATE TRIGGER trigger_set_updated_at_%s
            BEFORE UPDATE ON public.%I
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_%s()',
        _target, _target, _target);

    EXECUTE format('
        COMMENT ON TABLE public.%I IS
            ''ADR-083: TCG 種別マスタ。UI から増減可能。tcg_series_master.tcg_type の値集合の正本。''',
        _target);
END $$;

-- === 2. tcg_series_master の固定 CHECK 制約を撤廃 ===
-- 種別を自由に増減可能にするため。tcg_series_master が存在する環境でのみ実行
-- (migration-test の最小ベースラインでは未作成のことがあるため to_regclass ガード)。
DO $$
BEGIN
    IF to_regclass('public.tcg_series_master') IS NOT NULL THEN
        ALTER TABLE public.tcg_series_master
            DROP CONSTRAINT IF EXISTS tcg_series_master_tcg_type_check;
        RAISE NOTICE 'tcg_series_master_tcg_type_check dropped (or already absent)';
    ELSE
        RAISE NOTICE 'public.tcg_series_master not present; skipping CHECK drop';
    END IF;
END $$;

-- ============================================================================
-- Rollback:
--   ALTER TABLE public.tcg_series_master ADD CONSTRAINT tcg_series_master_tcg_type_check
--     CHECK (tcg_type IN ('pokemon_booster_box','one_piece','dragon_ball','union_arena','yugioh','other'));
--   DROP TRIGGER IF EXISTS trigger_set_updated_at_tcg_type_master ON public.tcg_type_master;
--   DROP FUNCTION IF EXISTS public.set_updated_at_tcg_type_master();
--   DROP TABLE IF EXISTS public.tcg_type_master;
-- ============================================================================
