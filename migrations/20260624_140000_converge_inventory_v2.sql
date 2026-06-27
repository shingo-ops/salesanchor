-- 20260624_140000_converge_inventory_v2.sql
-- 目的: public.inventory(B在庫/WEGO在庫/仕入元在庫) を v2形へ収束させる（冪等）。
-- 背景: 20260602_180000 (run_all L221) が condition 含みの uq_inventory_offer_key を
--       「後から」再作成するため、HELD(L176/L178)の封印解除では収束しない（白紙DBでは
--       L178でcondition削除→L221でcondition参照INDEX作成が失敗し set -e で停止する）。
--       全在庫migration完了後の末尾で、IF EXISTS により確実かつ無害に除去する。
-- 本番: 既に v2 のため両文とも no-op（uq_inventory_offer_key も condition も存在しない）。
-- 参照: ADR-143 / recon-D1-inventory-drift-formalize.md / design-D1-...-v2.md

-- 1) condition を含む旧UNIQUEインデックスを除去（作成元: 20260602_180000）
DROP INDEX IF EXISTS uq_inventory_offer_key;

-- 2) 旧 condition 列を除去（v2の一意性は uq_inventory_offer_v2 が担保）
ALTER TABLE public.inventory DROP COLUMN IF EXISTS condition;
