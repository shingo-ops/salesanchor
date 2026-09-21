-- ============================================================================
-- Migration 20260921_020000: tcg_type_master → type_master リネーム（冪等）
--
-- ADR-156: 商品分類ツリー Phase 1
--   tcg_type_master を中分類マスタ type_master として汎用化する。
--   移行期間中（2026-12-21 まで）は互換ビュー public.tcg_type_master を残す。
--
-- ADR-155 準拠: seed なし（値の投入は CSV アプリ経由）
-- 冪等性:
--   Case 1: tcg_type_master あり & type_master なし → RENAME
--   Case 2: 両方なし → CREATE type_master
--   Case 3: type_master あり → スキップ
-- ============================================================================

-- === 1. テーブルリネーム or 新規作成（冪等ガード付き）===
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tcg_type_master')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'type_master')
    THEN
        ALTER TABLE public.tcg_type_master RENAME TO type_master;
    END IF;
END $$;

-- type_master が存在しなければ新規作成（CI テスト環境用: tcg_type_master も存在しない場合）
CREATE TABLE IF NOT EXISTS public.type_master (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(50)  NOT NULL UNIQUE,
    name_ja       VARCHAR(100),
    name_en       VARCHAR(100),
    sort_order    INTEGER      NOT NULL DEFAULT 100,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- === 2. 互換ビュー（移行期間3か月、2026-12-21以降にDROP予定）===
-- tcg_type_master がテーブルとして残っていない場合のみビューを作成
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tcg_type_master')
    THEN
        CREATE OR REPLACE VIEW public.tcg_type_master AS SELECT * FROM public.type_master;
    END IF;
END $$;

COMMENT ON VIEW public.tcg_type_master IS '互換ビュー: ADR-156 移行期間用（2026-12-21以降に DROP 予定）';

-- === 3. トリガ関数（新規作成 or リネーム後どちらでも適用）===
CREATE OR REPLACE FUNCTION public.set_updated_at_type_master() RETURNS TRIGGER AS $upd$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $upd$ LANGUAGE plpgsql;

-- 旧トリガ削除（tcg_type_master からリネームされた場合のみ存在する）
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_set_updated_at_tcg_type_master') THEN
        DROP TRIGGER trigger_set_updated_at_tcg_type_master ON public.type_master;
    END IF;
END $$;

DROP TRIGGER IF EXISTS trg_type_master_updated_at ON public.type_master;
CREATE TRIGGER trg_type_master_updated_at BEFORE UPDATE ON public.type_master FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_type_master();

-- === 4. kind_id FK 追加（大分類への紐付け）===
ALTER TABLE public.type_master ADD COLUMN IF NOT EXISTS kind_id INTEGER REFERENCES public.product_kinds(id) ON DELETE SET NULL;

-- インデックス（1行で書く — migration-guard チェック8対策）
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
