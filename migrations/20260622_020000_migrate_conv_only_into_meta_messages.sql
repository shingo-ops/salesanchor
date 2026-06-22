-- ============================================================================
-- Migration: 20260622_020000
-- conversation_logs のうち、実在 lead を持つ conv 専用行だけを meta_messages に移送する
--
-- 方針:
--   - tenant_[0-9]+ を全件走査
--   - lead が実在する行のみ移送
--   - 既存 meta_messages の一致行はスキップ
--   - lead_id は NULL 化しない
--   - 既存行は変更しない
--   - 冪等: message_id ベースで NOT EXISTS + ON CONFLICT DO NOTHING
--
-- 対象:
--   - tenant_004: conversation_logs id=6
--   - tenant_006: lead が消えた id=1-4 は除外
-- ============================================================================

DO $$
DECLARE
    schema_rec RECORD;
    inserted_count INTEGER;
BEGIN
    FOR schema_rec IN
        SELECT nspname
        FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        IF to_regclass(schema_rec.nspname || '.conversation_logs') IS NULL THEN
            CONTINUE;
        END IF;
        IF to_regclass(schema_rec.nspname || '.meta_messages') IS NULL THEN
            CONTINUE;
        END IF;

        EXECUTE format($q$
            INSERT INTO %I.meta_messages (
                tenant_id,
                lead_id,
                platform,
                sender_id,
                sender_name,
                message_id,
                message_text,
                direction,
                raw_payload,
                created_at,
                contact_id,
                company_id,
                deal_id,
                channel_identity,
                original_language,
                status,
                analysis,
                occurred_at,
                deleted_at,
                recorded_by_user_id,
                is_manual
            )
            SELECT
                cl.tenant_id,
                cl.lead_id,
                CASE
                    WHEN cl.channel_type = 'meta_messenger' THEN 'messenger'
                    WHEN cl.channel_type = 'instagram' THEN 'instagram'
                    WHEN cl.channel_type = 'discord' THEN 'discord'
                    WHEN cl.channel_type = 'phone' THEN 'phone'
                    ELSE cl.channel_type
                END AS platform,
                COALESCE(NULLIF(cl.channel_identity, ''), cl.sender, 'migrated:conv_log_' || cl.id::text) AS sender_id,
                cl.sender AS sender_name,
                COALESCE(cl.external_message_id, 'conv_log_' || cl.id::text) AS message_id,
                cl.content_text AS message_text,
                cl.direction,
                cl.raw_payload,
                cl.created_at,
                cl.contact_id,
                cl.company_id,
                cl.deal_id,
                cl.channel_identity,
                cl.original_language,
                cl.status,
                cl.analysis,
                cl.occurred_at,
                cl.deleted_at,
                cl.recorded_by_user_id,
                cl.is_manual
            FROM %I.conversation_logs cl
            WHERE EXISTS (
                SELECT 1
                FROM %I.leads l
                WHERE l.id = cl.lead_id
            )
              AND NOT EXISTS (
                SELECT 1
                FROM %I.meta_messages mm
                WHERE mm.message_id = COALESCE(cl.external_message_id, 'conv_log_' || cl.id::text)
              )
            ON CONFLICT DO NOTHING
        $q$, schema_rec.nspname, schema_rec.nspname, schema_rec.nspname, schema_rec.nspname);

        GET DIAGNOSTICS inserted_count = ROW_COUNT;
        RAISE NOTICE 'migration 20260622_020000: %.meta_messages inserted % rows', schema_rec.nspname, inserted_count;
    END LOOP;
END
$$;
