-- Migration: tenant_carrier_credentials に account_number_encrypted を追加
--
-- 変更内容:
--   FedEx Rates API / Ship API は accountNumber（FedEx 配送契約アカウント番号）が必須。
--   ADR-123 D3 / ADR-124 D2 に従い、既存テーブルに Fernet 暗号化カラムを追加する。
--
--   NULL 許容（既存レコードの後方互換を保持）:
--     - 接続テスト機能（carrier_credentials.py:test_connection）は account_number 不要
--     - Rates API 呼び出し時に NULL であれば live_error を返す（暗黙フォールバック禁止・ADR-124 D5）
--
-- 影響テーブル: public.tenant_carrier_credentials（カラム追加）
-- 適用対象: public スキーマ
-- 冪等チェック: ADD COLUMN IF NOT EXISTS で安全に再実行可能

ALTER TABLE tenant_carrier_credentials
    ADD COLUMN IF NOT EXISTS account_number_encrypted TEXT;

COMMENT ON COLUMN tenant_carrier_credentials.account_number_encrypted
    IS 'FedEx / UPS 配送アカウント番号（Fernet 暗号化）。Rates / Ship API に必須。NULL = 未設定。';
