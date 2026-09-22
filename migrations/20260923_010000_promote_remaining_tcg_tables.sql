-- ============================================================================
-- Migration 20260923_010000: 残存 TCG マスタ 3 テーブルを public schema にプロモート
--
-- 対象テーブル:
--   tenant_004.tcg_manufacturers  → public.tcg_manufacturers
--   tenant_004.tcg_series         → public.tcg_series
--   tenant_004.tcg_unit_evidence_rules → public.tcg_unit_evidence_rules
--
-- 経緯:
--   ADR-1002 Phase C: パイプライン 17 テーブルを tenant_004 → public 移行
--   （2026-09-21 完了、PR #3xxx）。上記 3 テーブルは当時未プロモートとして残存。
--   TCG_SCHEMA = "public" をコードで採用（fix-tcg-schema-wiring ブランチ）に
--   合わせて public コピーを作成する。
--
-- 冪等性:
--   - CREATE TABLE IF NOT EXISTS
--   - INSERT ... ON CONFLICT (id) DO NOTHING
--   - CREATE INDEX IF NOT EXISTS
--
-- 注意:
--   tenant_004.* テーブルは DROP しない（別途 PO 確認後に独立 migration で実施）
--
-- 作成日: 2026-09-23
-- ============================================================================

-- ============================================================
-- 1. public.tcg_manufacturers
-- ============================================================
CREATE TABLE IF NOT EXISTS public.tcg_manufacturers (
    id           UUID        NOT NULL DEFAULT gen_random_uuid(),
    code         VARCHAR(20) NOT NULL,
    display_name TEXT        NOT NULL,
    alt_name     TEXT,
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT tcg_manufacturers_pkey PRIMARY KEY (id),
    CONSTRAINT tcg_manufacturers_code_key UNIQUE (code)
);

COMMENT ON TABLE public.tcg_manufacturers IS 'TCG メーカーマスタ（全テナント共有・公式管理）';

-- データプロモート: tenant_004 → public（冪等・CI環境ではスキップ）
DO $$ BEGIN
IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tenant_004' AND table_name = 'tcg_manufacturers') THEN
    INSERT INTO public.tcg_manufacturers (id, code, display_name, alt_name, is_active, created_at) SELECT id, code, display_name, alt_name, is_active, created_at FROM tenant_004.tcg_manufacturers ON CONFLICT (id) DO NOTHING;
    RAISE NOTICE 'migration 20260923_010000: tcg_manufacturers データを tenant_004 からコピー';
ELSE
    RAISE NOTICE 'migration 20260923_010000: tenant_004.tcg_manufacturers 不在 — スキップ（CI環境）';
END IF;
END $$;

-- 索引
CREATE INDEX IF NOT EXISTS idx_public_tcg_manufacturers_active
    ON public.tcg_manufacturers (is_active);
CREATE INDEX IF NOT EXISTS idx_public_tcg_manufacturers_code
    ON public.tcg_manufacturers (code);

DO $$ BEGIN
    RAISE NOTICE 'migration 20260923_010000: public.tcg_manufacturers プロモート完了';
END $$;

-- ============================================================
-- 2. public.tcg_series
-- ============================================================
CREATE TABLE IF NOT EXISTS public.tcg_series (
    id           UUID        NOT NULL DEFAULT gen_random_uuid(),
    code         VARCHAR(20) NOT NULL,
    display_name TEXT        NOT NULL,
    alt_name     TEXT,
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT tcg_series_pkey PRIMARY KEY (id),
    CONSTRAINT tcg_series_code_key UNIQUE (code)
);

COMMENT ON TABLE public.tcg_series IS 'TCG シリーズ（IP）マスタ（全テナント共有・公式管理）';

-- データプロモート: tenant_004 → public（冪等・CI環境ではスキップ）
DO $$ BEGIN
IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tenant_004' AND table_name = 'tcg_series') THEN
    INSERT INTO public.tcg_series (id, code, display_name, alt_name, is_active, created_at) SELECT id, code, display_name, alt_name, is_active, created_at FROM tenant_004.tcg_series ON CONFLICT (id) DO NOTHING;
    RAISE NOTICE 'migration 20260923_010000: tcg_series データを tenant_004 からコピー';
ELSE
    RAISE NOTICE 'migration 20260923_010000: tenant_004.tcg_series 不在 — スキップ（CI環境）';
END IF;
END $$;

-- 索引
CREATE INDEX IF NOT EXISTS idx_public_tcg_series_active
    ON public.tcg_series (is_active);
CREATE INDEX IF NOT EXISTS idx_public_tcg_series_code
    ON public.tcg_series (code);

DO $$ BEGIN
    RAISE NOTICE 'migration 20260923_010000: public.tcg_series プロモート完了';
END $$;

-- ============================================================
-- 3. public.tcg_unit_evidence_rules
-- ============================================================
CREATE TABLE IF NOT EXISTS public.tcg_unit_evidence_rules (
    id                              TEXT        NOT NULL,
    evidence_type                   TEXT        NOT NULL,
    priority                        INTEGER     NOT NULL,
    enabled                         BOOLEAN     NOT NULL DEFAULT TRUE,
    requires_unique_pid             BOOLEAN     NOT NULL DEFAULT FALSE,
    requires_unique_unit_candidate  BOOLEAN     NOT NULL DEFAULT FALSE,
    exclude_product_matched_terms   BOOLEAN     NOT NULL DEFAULT FALSE,
    structure_pattern               TEXT        NOT NULL DEFAULT '',
    note                            TEXT        NOT NULL DEFAULT '',
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT tcg_unit_evidence_rules_pkey PRIMARY KEY (id)
);

COMMENT ON TABLE public.tcg_unit_evidence_rules IS 'TCG 単位証拠ルールマスタ（全テナント共有・公式管理）';

-- データプロモート: tenant_004 → public（冪等・CI環境ではスキップ）
DO $$ BEGIN
IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tenant_004' AND table_name = 'tcg_unit_evidence_rules') THEN
    INSERT INTO public.tcg_unit_evidence_rules (id, evidence_type, priority, enabled, requires_unique_pid, requires_unique_unit_candidate, exclude_product_matched_terms, structure_pattern, note, created_at) SELECT id, evidence_type, priority, enabled, requires_unique_pid, requires_unique_unit_candidate, exclude_product_matched_terms, structure_pattern, note, created_at FROM tenant_004.tcg_unit_evidence_rules ON CONFLICT (id) DO NOTHING;
    RAISE NOTICE 'migration 20260923_010000: tcg_unit_evidence_rules データを tenant_004 からコピー';
ELSE
    RAISE NOTICE 'migration 20260923_010000: tenant_004.tcg_unit_evidence_rules 不在 — スキップ（CI環境）';
END IF;
END $$;

-- 索引
CREATE INDEX IF NOT EXISTS idx_public_tcg_unit_evidence_rules_enabled
    ON public.tcg_unit_evidence_rules (enabled);
CREATE INDEX IF NOT EXISTS idx_public_tcg_unit_evidence_rules_priority
    ON public.tcg_unit_evidence_rules (priority);

DO $$ BEGIN
    RAISE NOTICE 'migration 20260923_010000: public.tcg_unit_evidence_rules プロモート完了';
END $$;

-- ============================================================================
-- Rollback 手順（緊急時のみ手動実行、tenant_004.* は温存されているため安全）:
--
-- DROP TABLE IF EXISTS public.tcg_unit_evidence_rules;
-- DROP TABLE IF EXISTS public.tcg_series;
-- DROP TABLE IF EXISTS public.tcg_manufacturers;
-- ============================================================================
