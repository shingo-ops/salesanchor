-- Migration: テナント Google Drive OAuth 連携設定テーブルを作成
--
-- 変更内容:
--   管理者が Google OAuth で接続した際の認証情報をテナント単位で保持するテーブル。
--   アクセストークン・リフレッシュトークンは Fernet で暗号化して保存する。
--   テナント共通の接続（管理者が1回接続 → 全スタッフ操作で同一アカウントの
--   ドライブに保存）を実現する。保存先フォルダ ID は任意（未指定ならマイドライブ直下）。
--   設計は public.tenant_google_calendar_config（migration 076）に倣う。
--
-- 影響テーブル: public.tenant_google_drive_config（新規作成）
-- 適用対象: public スキーマ（テナント横断）
-- 不可逆: テーブル削除は DROP TABLE で可（additive-only 原則に準拠）
--
-- 冪等チェック: IF NOT EXISTS で安全に再実行可能

CREATE TABLE IF NOT EXISTS tenant_google_drive_config (
  id                       SERIAL PRIMARY KEY,
  tenant_id                INTEGER NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
  access_token_encrypted   TEXT    NOT NULL,
  refresh_token_encrypted  TEXT    NOT NULL,
  token_expiry             TIMESTAMP WITH TIME ZONE,
  account_email            TEXT,
  folder_id                TEXT,
  connected_by_user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
  connected_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at               TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
