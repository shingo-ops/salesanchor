-- 便1: conversation_logs.lead_id → leads.id のFK追加（全テナント・冪等）
-- 設計: docs/specs/transaction-flow/design.md §4-4
-- ON DELETE RESTRICT / ON UPDATE RESTRICT（取引データ永久保存の方針・§11 ソフトデリート予約）
-- 冪等: 既に fk_conversation_logs_lead が在るテナントはスキップ
-- 前提: 全テナントで孤児0・NULL0（2026-07-15実測）。孤児が在るテナントではFK追加が失敗し停止する（安全側）
DO $$
DECLARE
    s TEXT;
BEGIN
    FOR s IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'fk_conversation_logs_lead'
              AND connamespace = s::regnamespace
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.conversation_logs '
                'ADD CONSTRAINT fk_conversation_logs_lead '
                'FOREIGN KEY (lead_id) REFERENCES %I.leads(id) '
                'ON DELETE RESTRICT ON UPDATE RESTRICT',
                s, s
            );
            RAISE NOTICE 'FK added to %.conversation_logs', s;
        ELSE
            RAISE NOTICE 'FK already exists on %.conversation_logs, skipped', s;
        END IF;
    END LOOP;
END $$;
