-- Migration: public.fedex_etd_images テーブル作成 + RLS
--
-- 変更内容:
--   FedEx ETD（Paperless Trade）で使用するレターヘッド/署名画像の
--   imageIndex を保存するテーブルを新設する。
--
--   設計（ADR-137 J1）:
--     - LETTERHEAD / SIGNATURE のみ永続化対象（Eva Q3 poka-yoke: 出荷ごとの書類は保存しない）
--     - imageIndex は無期限再利用（Eva Q4: リフレッシュ機構不要）
--     - UNIQUE(tenant_id, image_type, environment) で再アップロード時は ON CONFLICT upsert
--     - 有効期限カラムなし（無期限のため不要）
--     - RLS: tenant_carrier_credentials と同一パターン（ADR-125 D1）
--
--   参照ADR: docs/adr/ADR-137-fedex-etd-paperless-trade.md J1
--   RLS パターン参考: migrations/20260609_090000_add_carrier_credentials_rls.sql
--
-- 影響テーブル: public.fedex_etd_images（新設）
-- 適用対象: public スキーマ
-- 冪等チェック: CREATE TABLE IF NOT EXISTS + DROP POLICY IF EXISTS + CREATE POLICY で安全に再実行可能
-- 危険変更: なし（新規テーブル追加のみ）
-- 本番適用: ADR-137 G1 Shingo GO 後に run_all_migrations.sh 経由で実行

-- テーブル作成（冪等）
CREATE TABLE IF NOT EXISTS public.fedex_etd_images (
    id                 SERIAL PRIMARY KEY,
    tenant_id          INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    image_type         TEXT NOT NULL CHECK (image_type IN ('LETTERHEAD','SIGNATURE')),
    environment        TEXT NOT NULL CHECK (environment IN ('sandbox','production')),
    fedex_image_index  TEXT NOT NULL,
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (tenant_id, image_type, environment)
);

-- RLS を有効化
ALTER TABLE public.fedex_etd_images ENABLE ROW LEVEL SECURITY;

-- テーブル所有者にも RLS を適用（SUPERUSER は引き続きバイパス可）
ALTER TABLE public.fedex_etd_images FORCE ROW LEVEL SECURITY;

-- 既存ポリシーを削除してから再作成（冪等）
DROP POLICY IF EXISTS tenant_isolation_fedex_etd_images ON public.fedex_etd_images;

-- SELECT / INSERT / UPDATE / DELETE 全操作に適用
-- NULLIF: current_setting が空文字列を返す場合（app.tenant_id 未設定）に NULL へ変換し
--         INTEGER キャストエラーを防ぐ（空文字のまま ::INTEGER にかけると "invalid input syntax"）
CREATE POLICY tenant_isolation_fedex_etd_images ON public.fedex_etd_images
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
