-- Migration: テナント別 配送キャリア(FedEx/DHL/UPS) 認証情報テーブルを作成
--
-- 変更内容:
--   各テナントが自社の配送キャリア API 認証情報を画面から入力・保存するためのテーブル。
--   FedEx/UPS は Client ID/Secret、DHL は API Key/Secret を保持（カラムは汎用名）。
--   シークレットは Fernet で暗号化して保存する（tenant_google_drive_config と同方針）。
--
-- 影響テーブル: public.tenant_carrier_credentials（新規作成）
-- 適用対象: public スキーマ（テナント横断）
-- 不可逆: テーブル削除は DROP TABLE で可（additive-only 原則に準拠）
--
-- 冪等チェック: IF NOT EXISTS で安全に再実行可能

CREATE TABLE IF NOT EXISTS tenant_carrier_credentials (
  id                       SERIAL PRIMARY KEY,
  tenant_id                INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  carrier                  TEXT    NOT NULL CHECK (carrier IN ('fedex', 'dhl', 'ups')),
  client_id_encrypted      TEXT    NOT NULL,  -- FedEx/UPS: Client ID / DHL: API Key
  client_secret_encrypted  TEXT    NOT NULL,  -- FedEx/UPS: Client Secret / DHL: API Secret
  environment              TEXT    NOT NULL DEFAULT 'sandbox',  -- sandbox / production
  updated_by_user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_at               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (tenant_id, carrier)
);
