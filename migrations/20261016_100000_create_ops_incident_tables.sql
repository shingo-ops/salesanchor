-- ADR-1012 段階2 便A: 障害記録の表（public）。読み書きとも運用者の旗が立った接続だけ。記録は消せない。
-- 値の書き込みはしない（ADR-155）。書き込むのは便B の保守 API だけ。冪等。

-- 1. 1 件の障害 = 1 行（Alertmanager の fingerprint と startsAt で 1 件）
CREATE TABLE IF NOT EXISTS public.ops_incidents (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint           TEXT        NOT NULL,
    starts_at             TIMESTAMPTZ NOT NULL,
    alertname             TEXT        NOT NULL,
    severity              TEXT,
    labels                JSONB       NOT NULL DEFAULT '{}'::jsonb,
    annotations           JSONB       NOT NULL DEFAULT '{}'::jsonb,
    status                TEXT        NOT NULL,
    first_notified_at     TIMESTAMPTZ NOT NULL,
    last_notified_at      TIMESTAMPTZ NOT NULL,
    notify_count          INTEGER     NOT NULL DEFAULT 1,
    resolved_at           TIMESTAMPTZ,
    recurrence_of         UUID        REFERENCES public.ops_incidents(id),
    detection_path        TEXT        NOT NULL DEFAULT 'alert',
    human_noticed_at      TIMESTAMPTZ,
    needs_action          BOOLEAN,
    first_aid_started_at  TIMESTAMPTZ,
    first_aid_done_at     TIMESTAMPTZ,
    first_aid_result      TEXT,
    ai_started_at         TIMESTAMPTZ,
    root_cause            TEXT,
    fix_pr                INTEGER,
    review_note           TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ops_incidents_fingerprint_starts_at_key UNIQUE (fingerprint, starts_at),
    CONSTRAINT ops_incidents_status_check CHECK (status IN ('firing', 'resolved')),
    CONSTRAINT ops_incidents_detection_path_check CHECK (detection_path IN ('alert', 'human', 'ai')),
    CONSTRAINT ops_incidents_first_aid_result_check
        CHECK (first_aid_result IN ('recovered', 'not_recovered', 'escalated')),
    CONSTRAINT ops_incidents_notify_count_check CHECK (notify_count >= 1),
    CONSTRAINT ops_incidents_labels_size_check CHECK (octet_length(labels::text) <= 4096),
    CONSTRAINT ops_incidents_annotations_size_check CHECK (octet_length(annotations::text) <= 4096)
);

CREATE INDEX IF NOT EXISTS ix_ops_incidents_fingerprint_starts_at
    ON public.ops_incidents (fingerprint, starts_at DESC);
CREATE INDEX IF NOT EXISTS ix_ops_incidents_first_notified_at
    ON public.ops_incidents (first_notified_at);

-- 2. 出来事の記録（追記だけ）
CREATE TABLE IF NOT EXISTS public.ops_incident_events (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id  UUID        NOT NULL REFERENCES public.ops_incidents(id),
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind         TEXT        NOT NULL,
    actor        TEXT        NOT NULL,
    detail       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT ops_incident_events_kind_check
        CHECK (kind IN ('notified', 'resolved', 'annotated', 'first_aid', 'ai', 'halt')),
    CONSTRAINT ops_incident_events_actor_check
        CHECK (actor IN ('alertmanager', 'ops_token', 'super_admin')),
    CONSTRAINT ops_incident_events_detail_size_check CHECK (octet_length(detail::text) <= 8192)
);

CREATE INDEX IF NOT EXISTS ix_ops_incident_events_incident_id_occurred_at
    ON public.ops_incident_events (incident_id, occurred_at);

-- 3. 全停止スイッチ（1 行だけ。行が無いときは「止めていない」として扱う。最初の行は便B の API が作る）
CREATE TABLE IF NOT EXISTS public.ops_control (
    id          SMALLINT    PRIMARY KEY,
    halt_all    BOOLEAN     NOT NULL DEFAULT false,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    changed_by  TEXT        NOT NULL,
    reason      TEXT,
    CONSTRAINT ops_control_single_row_check CHECK (id = 1)
);

COMMENT ON TABLE public.ops_incidents IS 'ADR-1012 段階2: 障害 1 件 = 1 行。書き込みは保守 API だけ';
COMMENT ON TABLE public.ops_incident_events IS 'ADR-1012 段階2: 障害の出来事の記録。追記だけ';
COMMENT ON TABLE public.ops_control IS 'ADR-1012 段階2: 全停止スイッチ。id=1 の 1 行だけ。行が無いときは止めていない';

-- 4. RLS（運用者の旗が立った接続だけ。DELETE のポリシーは作らない）
ALTER TABLE public.ops_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ops_incidents FORCE ROW LEVEL SECURITY;
ALTER TABLE public.ops_incident_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ops_incident_events FORCE ROW LEVEL SECURITY;
ALTER TABLE public.ops_control ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ops_control FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ops_incidents_operator_select ON public.ops_incidents;
CREATE POLICY ops_incidents_operator_select ON public.ops_incidents
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_incidents_operator_insert ON public.ops_incidents;
CREATE POLICY ops_incidents_operator_insert ON public.ops_incidents
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_incidents_operator_update ON public.ops_incidents;
CREATE POLICY ops_incidents_operator_update ON public.ops_incidents
    FOR UPDATE
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS ops_incident_events_operator_select ON public.ops_incident_events;
CREATE POLICY ops_incident_events_operator_select ON public.ops_incident_events
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_incident_events_operator_insert ON public.ops_incident_events;
CREATE POLICY ops_incident_events_operator_insert ON public.ops_incident_events
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS ops_control_operator_select ON public.ops_control;
CREATE POLICY ops_control_operator_select ON public.ops_control
    FOR SELECT USING (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_control_operator_insert ON public.ops_control;
CREATE POLICY ops_control_operator_insert ON public.ops_control
    FOR INSERT WITH CHECK (current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS ops_control_operator_update ON public.ops_control;
CREATE POLICY ops_control_operator_update ON public.ops_control
    FOR UPDATE
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

-- 5. アプリのロールの権限（既定の権限で付いた DELETE などを外す）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE ON public.ops_incidents, public.ops_control TO salesanchor_app;
        GRANT SELECT, INSERT ON public.ops_incident_events TO salesanchor_app;
        REVOKE DELETE, TRUNCATE ON public.ops_incidents, public.ops_control FROM salesanchor_app;
        REVOKE UPDATE, DELETE, TRUNCATE ON public.ops_incident_events FROM salesanchor_app;
    END IF;
END $$;
