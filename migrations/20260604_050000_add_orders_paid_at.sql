-- ADR-021 受注ステータスフロー改修 / Migration 20260604_050000:
-- 全既存テナントスキーマの orders テーブルに paid_at TIMESTAMPTZ を追加する。
--
-- 経緯:
--   受注一覧のステータスフローを実態に合わせて表示・操作するため
--   （ひとしさん指示 2026-06-04 夜・区切り4）。
--   フェーズ判定:
--     支払い待ち   = invoice_id 有（請求書発行済）かつ paid_at IS NULL
--     仕入れ中     = paid_at 有（支払済フラグ）かつ仕入未確定
--     発送待ち     = order_purchase_details.purchase_status='confirmed'
--     完了         = order_shipping_details.label_issued_at + tracking_number 有
--     トラブル/キャンセル = orders.status
--   このうち「支払済フラグ」が DB 上に存在しなかったため、本 migration で
--   orders.paid_at（支払日時。NULL=未払い）を追加する。
--   将来は発注書送付 / 発送ラベル発行と連動予定（現状は手動フラグ）。
--
-- 追加列:
--   - paid_at TIMESTAMPTZ NULL  -- 支払済日時（NULL=未払い）
--
-- 設計:
--   - 全既存テナントスキーマ（^tenant_\d+$）をループして ALTER TABLE ... ADD COLUMN
--     IF NOT EXISTS する DO ブロック（migration 20260604_030000 の踏襲）。
--   - orders テーブル未存在のスキーマは CONTINUE 相当でスキップ
--     （migration-test の単体 baseline 等で no-op 緑になる）。
--   - NULL 許可・DEFAULT なし（既存行への影響なし）。
--
-- 冪等性:
--   - ADD COLUMN IF NOT EXISTS で再実行 no-op。
--
-- 新規テナント用の CREATE TABLE 側（backend/app/services/tenant.py）にも
-- paid_at 列を追加済み。
--
-- additive-only (backend/CLAUDE.md): 列追加のみ。削除・型変更なし。
--
-- 作成日: 2026-06-04

DO $$
DECLARE
    schema_rec RECORD;
    applied_count INTEGER := 0;
    skipped_no_table INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        IF EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'orders'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.orders ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ',
                schema_rec.nspname
            );
            applied_count := applied_count + 1;
            RAISE NOTICE 'migration 20260604_050000: %.orders に paid_at を追加', schema_rec.nspname;
        ELSE
            skipped_no_table := skipped_no_table + 1;
        END IF;
    END LOOP;

    RAISE NOTICE
        'migration 20260604_050000: 完了。適用 % テーブル、未存在スキップ % スキーマ',
        applied_count, skipped_no_table;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行）:
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$'
--     LOOP
--         IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = r.nspname AND tablename = 'orders') THEN
--             EXECUTE format('ALTER TABLE %I.orders DROP COLUMN IF EXISTS paid_at', r.nspname);
--         END IF;
--     END LOOP;
-- END $$;
-- =====================================================================
