-- Migration 20260612_200000: ADR-129 — tenant_carrier_credentials の UNIQUE 制約を環境別に変更
--
-- 変更内容:
--   旧制約: UNIQUE (tenant_id, carrier)          ← テナントあたり 1 キャリア 1 レコードのみ
--   新制約: UNIQUE (tenant_id, carrier, environment) ← 本番/Sandbox を別行で保持
--
-- 移行安全性:
--   既存行はすべて environment = 'production'（ADR-125 UX: 顧客UIから production 固定）
--   のため、新制約への変更後もデータの重複は発生しない。
--
-- 不可逆操作: 本番デプロイ前に必ず適用すること（ADR-025 確認済み）
-- 冪等チェック: DROP CONSTRAINT IF EXISTS で再実行 no-op

-- 1. environment が NULL の既存行を production に正規化（念のため）
UPDATE public.tenant_carrier_credentials
  SET environment = 'production'
  WHERE environment IS NULL OR environment = '';

-- 2. 旧制約を削除
ALTER TABLE public.tenant_carrier_credentials
  DROP CONSTRAINT IF EXISTS tenant_carrier_credentials_tenant_id_carrier_key;

-- 3. 新制約を追加
ALTER TABLE public.tenant_carrier_credentials
  ADD CONSTRAINT tenant_carrier_credentials_tenant_id_carrier_env_key
  UNIQUE (tenant_id, carrier, environment);
