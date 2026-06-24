-- バックフィル: meta_messages.original_language を message_translations から補完
--
-- 目的: 20260622_010000 でカラム追加済みだが、過去の Meta inbound 行はすべて NULL。
--       message_translations.original_language（ensure_inbound_translations で書き込み済み）
--       を message_id キーで突合して補完する。
--
-- 制約:
--   - additive-only（UPDATE のみ。DELETE/DROP なし）
--   - 冪等（original_language IS NULL の行のみ対象）
--   - テナント全件ループ（プレースホルダ方式ではなく pg_namespace 走査形式）
--   - Discord DM は message_translations に行がないため影響なし（IS NULL のまま）

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname
        FROM pg_catalog.pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        -- テーブル存在確認（migration-test など一部テナントが未セットアップの場合はスキップ）
        IF to_regclass(schema_rec.nspname || '.meta_messages') IS NULL THEN
            RAISE NOTICE 'backfill 20260624_120000: %.meta_messages not found — skip', schema_rec.nspname;
            CONTINUE;
        END IF;
        IF to_regclass(schema_rec.nspname || '.message_translations') IS NULL THEN
            RAISE NOTICE 'backfill 20260624_120000: %.message_translations not found — skip', schema_rec.nspname;
            CONTINUE;
        END IF;

        -- meta_messages.original_language が NULL の inbound 行を
        -- message_translations の original_language で補完する。
        -- ON CONFLICT なし: IS NULL フィルタで冪等を保証。
        EXECUTE format(
            'UPDATE %I.meta_messages mm
             SET    original_language = mt.original_language
             FROM   %I.message_translations mt
             WHERE  mt.message_id         = mm.message_id
               AND  mm.original_language  IS NULL
               AND  mm.direction          = ''inbound''
               AND  mt.original_language  IS NOT NULL',
            schema_rec.nspname,
            schema_rec.nspname
        );
        RAISE NOTICE 'backfill 20260624_120000: %.meta_messages original_language 補完完了', schema_rec.nspname;
    END LOOP;
END;
$$;
