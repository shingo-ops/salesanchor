-- A4: 接続テスト結果の保存・表示
-- public.tenant_carrier_credentials に最終接続テスト結果を追加
-- additive-only / nullable / idempotent

ALTER TABLE public.tenant_carrier_credentials
  ADD COLUMN IF NOT EXISTS last_tested_at TIMESTAMP WITH TIME ZONE NULL,
  ADD COLUMN IF NOT EXISTS last_test_ok BOOLEAN NULL,
  ADD COLUMN IF NOT EXISTS last_test_message TEXT NULL;
