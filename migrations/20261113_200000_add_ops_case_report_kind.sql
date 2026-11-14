-- ADR-1012 段階4 便2a: 報告を種類（kind）ごとに 1 通にする準備と、報告が届いた出来事の kind・actor を足す。
-- 古い一意（incident_id だけ）は残す（今のコードの ON CONFLICT (incident_id) が使うため。消すのは便2b）。冪等。

-- 1. 報告の種類の列（既存の行は investigation になる）
ALTER TABLE ops_case.reports ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'investigation';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'ops_case.reports'::regclass AND conname = 'reports_kind_check') THEN
        ALTER TABLE ops_case.reports
            ADD CONSTRAINT reports_kind_check CHECK (kind IN ('investigation', 'verification', 'effect'));
    END IF;
END $$;

-- 2. 種類ごとに 1 通の一意
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'ops_case.reports'::regclass AND conname = 'reports_incident_id_kind_key') THEN
        ALTER TABLE ops_case.reports
            ADD CONSTRAINT reports_incident_id_kind_key UNIQUE (incident_id, kind);
    END IF;
END $$;

-- 3. 出来事の kind に case_report を足す（名前は変えない。伏せた窓の分類の理由がこの名前を指すため）
DO $$
DECLARE
    def TEXT;
BEGIN
    SELECT pg_get_constraintdef(con.oid) INTO def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.ops_incident_events'::regclass
      AND con.conname = 'ops_incident_events_kind_check';

    IF def IS NULL OR def NOT LIKE '%case_report%' THEN
        ALTER TABLE public.ops_incident_events DROP CONSTRAINT IF EXISTS ops_incident_events_kind_check;
        ALTER TABLE public.ops_incident_events
            ADD CONSTRAINT ops_incident_events_kind_check
            CHECK (kind IN ('notified', 'resolved', 'annotated', 'first_aid', 'ai', 'halt', 'case_report')) NOT VALID;
    END IF;
END $$;
ALTER TABLE public.ops_incident_events VALIDATE CONSTRAINT ops_incident_events_kind_check;

-- 4. 出来事の actor に case_agent を足す
DO $$
DECLARE
    def TEXT;
BEGIN
    SELECT pg_get_constraintdef(con.oid) INTO def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.ops_incident_events'::regclass
      AND con.conname = 'ops_incident_events_actor_check';

    IF def IS NULL OR def NOT LIKE '%case_agent%' THEN
        ALTER TABLE public.ops_incident_events DROP CONSTRAINT IF EXISTS ops_incident_events_actor_check;
        ALTER TABLE public.ops_incident_events
            ADD CONSTRAINT ops_incident_events_actor_check
            CHECK (actor IN ('alertmanager', 'ops_token', 'super_admin', 'case_agent')) NOT VALID;
    END IF;
END $$;
ALTER TABLE public.ops_incident_events VALIDATE CONSTRAINT ops_incident_events_actor_check;

COMMENT ON COLUMN ops_case.reports.kind IS '報告の種類。investigation=調べた結果・verification=直ったかの確かめ・effect=効果の確かめ。種類ごとに 1 通';
