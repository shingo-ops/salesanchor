-- Migration: public.tenant_carrier_credentials に RLS ポリシーを追加
--
-- 変更内容:
--   tenant_carrier_credentials は 2026-06-08 に作成されたが RLS が未設定だった。
--   アプリ層の WHERE tenant_id = :tid に加え、DB レイヤでもテナント分離を強制する。
--
--   設計:
--     - NULLIF を使い空文字列 → INTEGER キャストエラーを防止（test_rls_invariants.py 準拠）
--     - FORCE ROW LEVEL SECURITY でテーブル所有者（superuser を除く）にも適用
--     - superuser は FORCE でもバイパスされるため CI で salesanchor_app（NOBYPASSRLS）を使用
--
--   ADR-124: docs/adr/ADR-125-fedex-rates-stage1.md D1
--   パターン参考: migrations/040_create_tenant_meta_config.sql:54-67
--                 migrations/20260605_010000_rls_translation_glossary.sql
--
-- 影響テーブル: public.tenant_carrier_credentials（RLS有効化）
-- 適用対象: public スキーマ
-- 冪等チェック: DROP POLICY IF EXISTS + CREATE POLICY で安全に再実行可能

-- RLS を有効化
ALTER TABLE tenant_carrier_credentials ENABLE ROW LEVEL SECURITY;

-- テーブル所有者にも RLS を適用（SUPERUSER は引き続きバイパス可）
ALTER TABLE tenant_carrier_credentials FORCE ROW LEVEL SECURITY;

-- 既存ポリシーを削除してから再作成（冪等）
DROP POLICY IF EXISTS tenant_isolation_carrier_credentials ON tenant_carrier_credentials;

-- SELECT / INSERT / UPDATE / DELETE 全操作に適用
-- NULLIF: current_setting が空文字列を返す場合（app.tenant_id 未設定）に NULL へ変換し
--         INTEGER キャストエラーを防ぐ（空文字のまま ::INTEGER にかけると "invalid input syntax"）
CREATE POLICY tenant_isolation_carrier_credentials ON tenant_carrier_credentials
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
