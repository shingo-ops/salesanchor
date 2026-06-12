-- Migration 103: leads.initiative + leads.channel_type 追加、leads.source 廃止
--              （ファネルダッシュボード PR1）
--
-- 目的:
--   リードの流入軸を「きっかけ（initiative）」と「チャネル（channel_type）」の2軸に整理する。
--   既存 leads.source はフリーテキストで表記ゆれあり（recon#1）。
--
-- 設計判断:
--   - ADR-138 §D1-3: クリーンスレート方針（PO宣言 2026-06-12）
--   - 既存行はすべて channel_type='unknown', initiative=NULL に初期化（移行対応表の個別変換なし）
--   - ただし instagram:/messenger: 形式の source 値は外部ID（Meta PSID）を含むため、
--     lead_channels への変換保全（方法A）を先に実行してから source を DROP する。
--     根拠: 重複リード判定（UNIQUE(platform, external_id)）の鍵を失うと将来の webhook 重複チェックが壊れる。
--   - tenant_006 の 23件テストデータ: 消去OK（PO確認済み 2026-06-12）
--
-- 冪等性:
--   ADD COLUMN IF NOT EXISTS / INSERT ... ON CONFLICT DO NOTHING / DROP COLUMN IF EXISTS
-- 適用対象: 全テナント
-- 作成日: 2026-06-12
-- 関連: docs/handoff/funnel-dashboard-stage1/design.md §2.3
--       docs/adr/ADR-138-funnel-dashboard-stage1.md §D1-3
--       migrations/20260607_120000_create_lead_channels.sql（lead_channels テーブル）

DO $$
DECLARE
    schema_rec RECORD;
    has_source BOOLEAN;
BEGIN
    FOR schema_rec IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        RAISE NOTICE 'Migration 103: processing schema %', schema_rec.schema_name;

        -- ── 1. source カラムの存在確認 ────────────────────────────────────
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_rec.schema_name
              AND table_name   = 'leads'
              AND column_name  = 'source'
        ) INTO has_source;

        -- ── 2. lead_channels への変換保全（方法A）────────────────────────
        --   instagram:<PSID> / messenger:<PSID> 形式のみ対象。
        --   lead_channels テーブルが存在する場合のみ実行（migration 20260607_120000 依存）。
        IF has_source THEN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = schema_rec.schema_name
                  AND table_name   = 'lead_channels'
            ) THEN
                EXECUTE format($sql$
                    INSERT INTO %I.lead_channels (lead_id, platform, external_id, display_name)
                    SELECT
                        id,
                        CASE
                            WHEN source LIKE 'instagram:%%' THEN 'instagram'
                            ELSE 'messenger'
                        END,
                        split_part(source, ':', 2),
                        customer_name
                    FROM %I.leads
                    WHERE source ~ '^(instagram|messenger):[0-9]+'
                    ON CONFLICT (platform, external_id) DO NOTHING
                $sql$,
                    schema_rec.schema_name,
                    schema_rec.schema_name
                );
                RAISE NOTICE '  lead_channels 変換保全: 完了';
            ELSE
                RAISE WARNING '  lead_channels テーブルが存在しません（schema: %）。変換保全をスキップ。', schema_rec.schema_name;
            END IF;
        END IF;

        -- ── 3. initiative カラム追加 ──────────────────────────────────────
        EXECUTE format(
            'ALTER TABLE %I.leads
             ADD COLUMN IF NOT EXISTS initiative VARCHAR(10)
                 CHECK (initiative IS NULL OR initiative IN (''outbound'', ''inbound''))',
            schema_rec.schema_name
        );

        -- ── 4. channel_type カラム追加 ────────────────────────────────────
        EXECUTE format(
            'ALTER TABLE %I.leads
             ADD COLUMN IF NOT EXISTS channel_type VARCHAR(30)',
            schema_rec.schema_name
        );

        -- ── 5. 既存行の初期化（すべて unknown/NULL）──────────────────────
        EXECUTE format(
            'UPDATE %I.leads
             SET channel_type = ''unknown''
             WHERE channel_type IS NULL',
            schema_rec.schema_name
        );
        -- initiative はすべて NULL のまま（きっかけ不明）

        -- ── 6. leads.source 廃止 ──────────────────────────────────────────
        EXECUTE format(
            'ALTER TABLE %I.leads
             DROP COLUMN IF EXISTS source',
            schema_rec.schema_name
        );

        -- ── 7. インデックス ───────────────────────────────────────────────
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_leads_initiative
             ON %I.leads (initiative)
             WHERE initiative IS NOT NULL',
            schema_rec.schema_name
        );

        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_leads_channel_type
             ON %I.leads (channel_type)',
            schema_rec.schema_name
        );

    END LOOP;
    RAISE NOTICE 'Migration 103: complete';
END
$$;
