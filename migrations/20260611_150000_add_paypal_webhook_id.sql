-- Migration: tenant_paypal_config に webhook_id 列を追加（Increment 2.5）
--
-- 目的 (ADR-101 §6 PayPal 入金自動確認 / webhook):
--   テナント毎に PayPal webhook を自動登録し、その webhook_id を保存する。
--   受信 webhook の署名検証（verify-webhook-signature API）に webhook_id が必須。
--
-- 影響テーブル: public.tenant_paypal_config（public スキーマの単一テーブル・1テナント1行）
-- 冪等・安全: ADD COLUMN IF NOT EXISTS（nullable 追加のみ・既存データ不変・破壊操作なし）
-- ※ migration-test は変更 SQL を単体 baseline で実行するため、テーブル存在を to_regclass で
--   ガードする（tenant_paypal_config は先行 migration 20260610_071110 で作成される）。

DO $$
BEGIN
    IF to_regclass('public.tenant_paypal_config') IS NOT NULL THEN
        ALTER TABLE tenant_paypal_config
            ADD COLUMN IF NOT EXISTS webhook_id TEXT;
        EXECUTE 'COMMENT ON COLUMN tenant_paypal_config.webhook_id IS '
                '''ADR-101: テナントの PayPal アプリに自動登録した webhook の id（署名検証に使用）''';
    END IF;
END
$$;
