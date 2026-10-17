-- ADR-1025 便1: 解析の誤り報告の表 3 つ（public）。読み書きとも運用者の旗が立った接続だけ。
-- events は追記だけ（UPDATE・DELETE 不可）。構造のみ・データは入れない・冪等。
-- extraction_item_id / extraction_job_id に FK を付けないのは、再解析で行が作り直されても報告を残すため
-- （前例: item_corrections「no FK constraints by design」20260921_110000_pipeline_tables_public.sql）。

-- 1. 報告番号の連番（ER-000001 形式の元）
CREATE SEQUENCE IF NOT EXISTS public.analysis_error_report_code_seq START 1;

-- 2. 報告 1 件 = 1 行
CREATE TABLE IF NOT EXISTS public.analysis_error_reports (
    report_code         VARCHAR(16)  NOT NULL UNIQUE
                        DEFAULT ('ER-' || LPAD(nextval('public.analysis_error_report_code_seq')::TEXT, 6, '0')),
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_item_id  UUID         NOT NULL,
    extraction_job_id   UUID         NOT NULL,
    reported_by         TEXT         NOT NULL,
    reported_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    status              TEXT         NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'working', 'resolved', 'unresolved', 'cancelled')),
    discord_message_id  TEXT
);

CREATE INDEX IF NOT EXISTS ix_analysis_error_reports_extraction_item_id
    ON public.analysis_error_reports (extraction_item_id);

-- 3. 報告の項目（1 報告に最大 7 項目）
CREATE TABLE IF NOT EXISTS public.analysis_error_report_fields (
    id                        BIGSERIAL PRIMARY KEY,
    report_id                 UUID      NOT NULL REFERENCES public.analysis_error_reports(id),
    field_name                TEXT      NOT NULL
                              CHECK (field_name IN ('product_id', 'quantity', 'price', 'unit', 'condition', 'status', 'note')),
    system_value              JSONB,
    expected_value            JSONB,
    expected_missing_product  BOOLEAN   NOT NULL DEFAULT false,
    UNIQUE (report_id, field_name)
);

-- 4. 出来事の記録（追記だけ）
CREATE TABLE IF NOT EXISTS public.analysis_error_report_events (
    id         BIGSERIAL    PRIMARY KEY,
    report_id  UUID         NOT NULL REFERENCES public.analysis_error_reports(id),
    at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    actor      TEXT         NOT NULL,
    kind       TEXT         NOT NULL
               CHECK (kind IN ('created', 'notified', 'notify_failed', 'session_opened', 'cause', 'action', 'reanalyzed', 'verified')),
    payload    JSONB        NOT NULL DEFAULT '{}'::jsonb
               CHECK (octet_length(payload::text) <= 8192)
);

CREATE INDEX IF NOT EXISTS ix_analysis_error_report_events_report_id_at
    ON public.analysis_error_report_events (report_id, at);

COMMENT ON TABLE public.analysis_error_reports IS 'ADR-1025: 解析の誤り報告 1 件 = 1 行';
COMMENT ON TABLE public.analysis_error_report_fields IS 'ADR-1025: 誤り報告の項目（システムの値と期待値）';
COMMENT ON TABLE public.analysis_error_report_events IS 'ADR-1025: 誤り報告の出来事の記録。追記だけ';

-- 5. RLS（運用者の旗が立った接続だけ。events の UPDATE・DELETE のポリシーは作らない）
ALTER TABLE public.analysis_error_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_error_reports FORCE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_error_report_fields ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_error_report_fields FORCE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_error_report_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_error_report_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS analysis_error_reports_operator_select ON public.analysis_error_reports;
CREATE POLICY analysis_error_reports_operator_select ON public.analysis_error_reports
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS analysis_error_reports_operator_insert ON public.analysis_error_reports;
CREATE POLICY analysis_error_reports_operator_insert ON public.analysis_error_reports
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS analysis_error_reports_operator_update ON public.analysis_error_reports;
CREATE POLICY analysis_error_reports_operator_update ON public.analysis_error_reports
    FOR UPDATE
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS analysis_error_report_fields_operator_select ON public.analysis_error_report_fields;
CREATE POLICY analysis_error_report_fields_operator_select ON public.analysis_error_report_fields
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS analysis_error_report_fields_operator_insert ON public.analysis_error_report_fields;
CREATE POLICY analysis_error_report_fields_operator_insert ON public.analysis_error_report_fields
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS analysis_error_report_events_operator_select ON public.analysis_error_report_events;
CREATE POLICY analysis_error_report_events_operator_select ON public.analysis_error_report_events
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS analysis_error_report_events_operator_insert ON public.analysis_error_report_events;
CREATE POLICY analysis_error_report_events_operator_insert ON public.analysis_error_report_events
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');

-- 6. アプリのロールの権限（既定の権限で付いた DELETE などを外す）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE ON public.analysis_error_reports TO salesanchor_app;
        GRANT SELECT, INSERT ON public.analysis_error_report_fields TO salesanchor_app;
        GRANT SELECT, INSERT ON public.analysis_error_report_events TO salesanchor_app;
        REVOKE DELETE, TRUNCATE ON public.analysis_error_reports FROM salesanchor_app;
        REVOKE UPDATE, DELETE, TRUNCATE ON public.analysis_error_report_fields FROM salesanchor_app;
        REVOKE UPDATE, DELETE, TRUNCATE ON public.analysis_error_report_events FROM salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE
            public.analysis_error_report_code_seq,
            public.analysis_error_report_fields_id_seq,
            public.analysis_error_report_events_id_seq
            TO salesanchor_app;
    END IF;
END $$;
