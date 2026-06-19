-- Migration 20260618_120000: ADR-137 — fedex_etd_images テーブル作成
--
-- 目的:
--   FedEx Trade Documents Upload API（Upload Image）で登録した
--   レターヘッド/署名画像の imageIndex を永続化する。
--   テナントごとに1回登録・以降は再利用（Eva Q3/Q4: 無期限）。
--
-- !! 適用しない !!
--   このファイルは migration ファイルとして作成のみ。
--   deploy.yml への wiring（G2）・本番適用は Shingo GO（G1）後の別PR。
--
-- 設計:
--   - public スキーマ（tenant_carrier_credentials と同方針）
--   - tenant_id 列で RLS テナント分離（NULLIF ガード付き）
--   - UNIQUE(tenant_id, image_type, environment) — 同一テナント×種別×環境は upsert 上書き
--   - 有効期限カラムなし（Eva Q4: imageIndex は無期限）
--   - 出荷ごとの自前書類 docId は本テーブルに保存しない（Eva Q3: 使い捨て）
--     → fedex_etd.py の PERSISTENT_IMAGE_TYPES ガードで実施
--
-- 冪等: IF NOT EXISTS / DROP POLICY IF EXISTS で再実行 no-op
-- Rollback: DROP TABLE IF EXISTS public.fedex_etd_images; （緊急時のみ手動実行）

-- 1. テーブル作成
CREATE TABLE IF NOT EXISTS public.fedex_etd_images (
    id                 SERIAL PRIMARY KEY,
    tenant_id          INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    -- image_type: Trade Documents Upload API の Upload Image が対象とする画像種別のみ
    image_type         TEXT NOT NULL CHECK (image_type IN ('LETTERHEAD', 'SIGNATURE')),
    -- environment: sandbox または production（キャリア設定と同じ分離方針）
    environment        TEXT NOT NULL CHECK (environment IN ('sandbox', 'production')),
    -- fedex_image_index: Upload Image API の戻り値（imageIndex）。
    --   ※ docId（Upload Document の戻り値）ではない。混同禁止。
    fedex_image_index  TEXT NOT NULL,
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- テナント×種別×環境ごとに1レコードを保持（再アップロードは upsert 上書き）
    UNIQUE (tenant_id, image_type, environment)
);

COMMENT ON TABLE public.fedex_etd_images IS
  'FedEx ETD レターヘッド/署名画像専用。imageIndex を保持・再利用。出荷ごとの自前書類 docId は保存しない（ADR-137 J1）';

COMMENT ON COLUMN public.fedex_etd_images.fedex_image_index IS
  'Trade Documents Upload API / Upload Image 戻り値（imageIndex）。docId ではない。';

-- 2. RLS 有効化（tenant_carrier_credentials と同一パターン）
ALTER TABLE public.fedex_etd_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fedex_etd_images FORCE ROW LEVEL SECURITY;

-- 3. テナント分離ポリシー（冪等）
DROP POLICY IF EXISTS tenant_isolation_fedex_etd_images ON public.fedex_etd_images;

CREATE POLICY tenant_isolation_fedex_etd_images ON public.fedex_etd_images
    USING (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    );
-- NULLIF: current_setting が空文字のときに NULL → INTEGER キャストエラーを防ぐ
-- （migrations/20260609_090000_add_carrier_credentials_rls.sql と同パターン）
