-- attachment-storage 便2 / Migration: lead_attachments テーブル作成
--
-- 背景:
--   Discord など外部プラットフォームの添付ファイルは、提供元が恒久保持しない。
--   Discord CDN URL は約24時間で署名が失効し、元投稿が削除されると実体も消える。
--   顧客とのやり取りを CRM の履歴として残すため、添付を自社サーバーへ保存する。
--   本テーブルは「どの画像が誰のものか」を記録する台帳である。
--
-- 設計:
--   docs/specs/attachment-storage/to-be.md（PR #3192 でマージ済み）に基づく。
--   実体は Docker ボリューム attachments_data（PR #3195 で追加）に置く。
--   探す・数える・並べる処理はすべて本テーブルが担う。
--
-- 冪等性:
--   - CREATE TABLE IF NOT EXISTS
--   - CREATE INDEX IF NOT EXISTS
--   - CREATE TRIGGER は pg_trigger 存在確認
--   - CREATE POLICY は pg_policies 存在確認
--   - DO block で pg_namespace 走査して全 tenant_NNN schema に適用
--
-- 参照: migrations/026_create_customer_contact_channels.sql（同型の実装）
--
-- 変更履歴:
--   2026-09-02: 初版作成（attachment-storage 便2）

DO $$
DECLARE
    schema_rec RECORD;
    created_count INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- leads テーブルが存在するスキーマのみ対象
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'leads'
        ) THEN
            CONTINUE;
        END IF;

        -- trg_set_updated_at() 関数が未定義のスキーマに備えて保険で作成（冪等）
        EXECUTE format($q$
            CREATE OR REPLACE FUNCTION %I.trg_set_updated_at()
            RETURNS TRIGGER AS $fn$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $fn$ LANGUAGE plpgsql
        $q$, schema_rec.nspname);

        -- テーブル作成（冪等: IF NOT EXISTS）
        EXECUTE format($q$
            CREATE TABLE IF NOT EXISTS %I.lead_attachments (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                lead_id INTEGER NOT NULL REFERENCES %I.leads(id) ON DELETE CASCADE,
                message_id VARCHAR(64) NOT NULL,
                platform VARCHAR(32) NOT NULL,
                file_path TEXT NOT NULL,
                file_size BIGINT NOT NULL,
                content_type VARCHAR(128),
                original_filename TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        $q$, schema_rec.nspname, schema_rec.nspname);

        -- インデックス（冪等）
        -- KGI4: リード削除時に対象を高速に特定する
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_la_lead_id ON %I.lead_attachments (lead_id)',
            schema_rec.nspname
        );
        -- KGI5/KGI6: 容量集計と古い順削除
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_la_tenant_created ON %I.lead_attachments (tenant_id, created_at)',
            schema_rec.nspname
        );
        -- 同一添付の二重保存を防ぐ
        EXECUTE format(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_la_message_id ON %I.lead_attachments (message_id)',
            schema_rec.nspname
        );

        -- updated_at トリガ
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'trg_la_updated_at'
              AND tgrelid = format('%I.lead_attachments', schema_rec.nspname)::regclass
        ) THEN
            EXECUTE format(
                'CREATE TRIGGER trg_la_updated_at BEFORE UPDATE ON %I.lead_attachments '
                'FOR EACH ROW EXECUTE FUNCTION %I.trg_set_updated_at()',
                schema_rec.nspname, schema_rec.nspname
            );
        END IF;

        -- RLS 有効化（冪等）
        EXECUTE format(
            'ALTER TABLE %I.lead_attachments ENABLE ROW LEVEL SECURITY',
            schema_rec.nspname
        );

        -- RLS ポリシー: leads を経由してテナント分離
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE policyname = 'tenant_isolation_lead_attachments'
              AND schemaname = schema_rec.nspname
        ) THEN
            EXECUTE format($q$
                CREATE POLICY tenant_isolation_lead_attachments ON %I.lead_attachments
                    USING (EXISTS (
                        SELECT 1 FROM %I.leads l
                        WHERE l.id = lead_attachments.lead_id
                          AND l.tenant_id = public.current_tenant_id()
                    ))
            $q$, schema_rec.nspname, schema_rec.nspname);
        END IF;

        EXECUTE format(
            $q$COMMENT ON TABLE %I.lead_attachments IS
              'attachment-storage: 顧客から受信した添付ファイルの保管台帳（実体は attachments_data ボリューム）'$q$,
            schema_rec.nspname
        );

        created_count := created_count + 1;
        RAISE NOTICE 'migration lead_attachments: %: 作成完了', schema_rec.nspname;
    END LOOP;
    RAISE NOTICE 'migration lead_attachments: 全 % テナントに適用', created_count;
END $$;
