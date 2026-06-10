-- Migration: テナント別 PayPal 決済連携 認証情報テーブルを作成
--
-- 変更内容:
--   各テナントが自社の PayPal アプリの API 認証情報（Client ID / Secret）を画面から
--   入力・保存するためのテーブル（Model A：各テナントが自分の PayPal で受け取る）。
--   シークレットは Fernet で暗号化して保存する（tenant_carrier_credentials と同方針）。
--   将来 Model B（PayPal Multiparty / Connect with PayPal）へ拡張する際もこのテーブルを基点にできる。
--
-- 影響テーブル: public.tenant_paypal_config（新規作成）
-- 適用対象: public スキーマ（テナント横断）
-- 不可逆: テーブル削除は DROP TABLE で可（additive-only 原則に準拠）
--
-- 冪等チェック: IF NOT EXISTS で安全に再実行可能

CREATE TABLE IF NOT EXISTS tenant_paypal_config (
  id                       SERIAL PRIMARY KEY,
  tenant_id                INTEGER NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
  client_id_encrypted      TEXT    NOT NULL,  -- PayPal アプリの Client ID
  client_secret_encrypted  TEXT    NOT NULL,  -- PayPal アプリの Client Secret
  environment              TEXT    NOT NULL DEFAULT 'sandbox' CHECK (environment IN ('sandbox', 'live')),
  updated_by_user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_at               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at               TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
