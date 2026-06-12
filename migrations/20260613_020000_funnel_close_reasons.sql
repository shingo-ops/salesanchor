-- Migration 102: 成約・失注理由マスタ（ファネルダッシュボード PR1）
--
-- 目的:
--   テナント別の成約/失注理由マスタ（close_reasons）と
--   商談との中間表（deal_close_reasons）を作成する。
--   deals.close_reason_memo を追加し、deals.lost_reason_code / deals.lost_reason を廃止する。
--
-- 設計判断:
--   - ADR-138 §D1-2: クリーンスレート方針（PO宣言 2026-06-12）
--   - lost_reason_code (enum 7値): 全テナント実データ 0件確認済み → 移行なし・カラムごと廃止
--   - lost_reason (VARCHAR 255): 全テナント実データ 0件確認済み → close_reason_memo に置換
--   - デフォルト理由は全テナントに自動投入
--
-- 冪等性:
--   CREATE TABLE IF NOT EXISTS / DROP COLUMN IF EXISTS / INSERT ... ON CONFLICT DO NOTHING
-- 適用対象: 全テナント
-- 作成日: 2026-06-12
-- 関連: docs/handoff/funnel-dashboard-stage1/design.md §2.2
--       docs/adr/ADR-138-funnel-dashboard-stage1.md §D1-2

DO $$
DECLARE
    schema_rec RECORD;
    constraint_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        RAISE NOTICE 'Migration 102: processing schema %', schema_rec.schema_name;

        -- ── 1. close_reasons マスタテーブル ──────────────────────────────────
        EXECUTE format($sql$
            CREATE TABLE IF NOT EXISTS %I.close_reasons (
                id         SERIAL PRIMARY KEY,
                type       VARCHAR(10) NOT NULL CHECK (type IN ('won', 'lost')),
                label      TEXT        NOT NULL,
                sort_order INTEGER     NOT NULL DEFAULT 0,
                is_active  BOOLEAN     NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (type, label)
            )
        $sql$, schema_rec.schema_name);

        -- ── 2. deal_close_reasons 中間表（主因1 + 副因複数）────────────────
        EXECUTE format($sql$
            CREATE TABLE IF NOT EXISTS %I.deal_close_reasons (
                id         SERIAL PRIMARY KEY,
                deal_id    INTEGER NOT NULL
                               REFERENCES %I.deals(id) ON DELETE CASCADE,
                reason_id  INTEGER NOT NULL
                               REFERENCES %I.close_reasons(id),
                is_primary BOOLEAN NOT NULL DEFAULT false,
                UNIQUE (deal_id, reason_id)
            )
        $sql$,
            schema_rec.schema_name,
            schema_rec.schema_name,
            schema_rec.schema_name
        );

        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_deal_close_reasons_deal
             ON %I.deal_close_reasons (deal_id)',
            schema_rec.schema_name
        );

        -- ── 3. deals.close_reason_memo 追加 ──────────────────────────────────
        EXECUTE format(
            'ALTER TABLE %I.deals
             ADD COLUMN IF NOT EXISTS close_reason_memo TEXT',
            schema_rec.schema_name
        );

        -- ── 4. deals.lost_reason_code 廃止（実データ 0件確認済み） ───────────
        EXECUTE format(
            'ALTER TABLE %I.deals
             DROP COLUMN IF EXISTS lost_reason_code',
            schema_rec.schema_name
        );

        -- ── 5. deals.lost_reason 廃止（実データ 0件確認済み・close_reason_memo に置換） ──
        EXECUTE format(
            'ALTER TABLE %I.deals
             DROP COLUMN IF EXISTS lost_reason',
            schema_rec.schema_name
        );

        -- ── 6. デフォルト理由を投入 ──────────────────────────────────────────
        -- 成約理由
        EXECUTE format($sql$
            INSERT INTO %I.close_reasons (type, label, sort_order) VALUES
                ('won', '在庫・品揃え',  1),
                ('won', '価格',          2),
                ('won', '安心感',        3),
                ('won', 'スピード',      4),
                ('won', '取引条件',      5),
                ('won', '人・関係',      6),
                ('won', 'その他',       99)
            ON CONFLICT (type, label) DO NOTHING
        $sql$, schema_rec.schema_name);

        -- 失注理由
        EXECUTE format($sql$
            INSERT INTO %I.close_reasons (type, label, sort_order) VALUES
                ('lost', '価格が合わなかった',             1),
                ('lost', '在庫・品揃えで応えられなかった', 2),
                ('lost', '不安を解消できなかった',         3),
                ('lost', '対応が遅れた',                   4),
                ('lost', '取引条件が合わなかった',         5),
                ('lost', '連絡が途絶えた',                 6),
                ('lost', 'お客様側の事情',                 7),
                ('lost', 'その他',                        99)
            ON CONFLICT (type, label) DO NOTHING
        $sql$, schema_rec.schema_name);

    END LOOP;
    RAISE NOTICE 'Migration 102: complete';
END
$$;
