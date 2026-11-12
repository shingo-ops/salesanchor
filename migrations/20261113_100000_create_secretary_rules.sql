-- ADR-1077 便1: 秘書の決まり帳の表 2 つと、使用の記録の使いみち secretary_regression を足す（作るだけ。行は入れない）
-- 設計: docs/handoff/secretary-rulebook/design.md §4・§6 の①・§12 便1。手順書: docs/handoff/secretary-rulebook/card-bin1.md
-- RLS: 2 表とも ENABLE と FORCE。読む・書くとも「自社の会社文脈 OR 運営文脈」（型 C の書く側の式。読む側の USING (true) は使わない）
-- 冪等: 表と索引は IF NOT EXISTS。CHECK は表を作る文の中に書く。方針は DROP POLICY IF EXISTS の後に作る。使いみちの CHECK は定義に値が無いときだけ付け替える
-- ロールバック: migrations/20261113_100001_create_secretary_rules_down.sql（手動実行のみ）

BEGIN;

-- 会社の決まりと候補（この 1 表だけに持つ）
CREATE TABLE IF NOT EXISTS public.secretary_rules (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE RESTRICT,
    status TEXT NOT NULL,
    rule_text TEXT NOT NULL DEFAULT '',
    source_text TEXT NULL,
    source_kind TEXT NULL,
    source_reply TEXT NULL,
    created_by INTEGER NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    decided_by INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ NULL,
    CONSTRAINT ck_secretary_rules_status CHECK (status IN ('candidate', 'approved', 'rejected', 'removed')),
    CONSTRAINT ck_secretary_rules_rule_text_len CHECK (char_length(rule_text) <= 150),
    CONSTRAINT ck_secretary_rules_approved_text CHECK (status <> 'approved' OR char_length(btrim(rule_text)) >= 1),
    CONSTRAINT ck_secretary_rules_source_text_len CHECK (source_text IS NULL OR char_length(source_text) <= 1000),
    CONSTRAINT ck_secretary_rules_source_kind CHECK (source_kind IS NULL OR source_kind IN ('invoice', 'event', 'unknown', 'rule_proposal', 'rule_list')),
    CONSTRAINT ck_secretary_rules_source_reply_len CHECK (source_reply IS NULL OR char_length(source_reply) <= 200),
    CONSTRAINT ck_secretary_rules_decided CHECK ((status = 'candidate') = (decided_at IS NULL))
);
CREATE INDEX IF NOT EXISTS ix_secretary_rules_tenant_status
    ON public.secretary_rules (tenant_id, status, id);

-- 前と同じか確かめる試しの結果（1 回の試しごとに 1 行）
CREATE TABLE IF NOT EXISTS public.secretary_rule_checks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE RESTRICT,
    started_by INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    sdk TEXT NOT NULL,
    model TEXT NOT NULL,
    rules_count INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    ok INTEGER NOT NULL DEFAULT 0,
    ng INTEGER NOT NULL DEFAULT 0,
    unmeasured INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    progress_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ NULL,
    CONSTRAINT ck_secretary_rule_checks_sdk_len CHECK (char_length(sdk) BETWEEN 1 AND 50),
    CONSTRAINT ck_secretary_rule_checks_model_len CHECK (char_length(model) BETWEEN 1 AND 100),
    CONSTRAINT ck_secretary_rule_checks_rules_count CHECK (rules_count >= 0),
    CONSTRAINT ck_secretary_rule_checks_status CHECK (status IN ('running', 'done', 'failed')),
    CONSTRAINT ck_secretary_rule_checks_counts CHECK (ok >= 0 AND ng >= 0 AND unmeasured >= 0 AND total >= 0 AND ok + ng + unmeasured <= total),
    CONSTRAINT ck_secretary_rule_checks_finished CHECK ((status = 'running') = (finished_at IS NULL))
);
CREATE INDEX IF NOT EXISTS ix_secretary_rule_checks_tenant_started
    ON public.secretary_rule_checks (tenant_id, started_at DESC);

-- 列の説明（backend/AGENTS.md「書き方の決まり」: 新しい表は全部の列に COMMENT ON COLUMN）
COMMENT ON TABLE public.secretary_rules IS '秘書の決まり帳。会社ごとの決まりと候補をこの 1 表だけに持つ（ADR-1077）';
COMMENT ON COLUMN public.secretary_rules.id IS '番号';
COMMENT ON COLUMN public.secretary_rules.tenant_id IS '会社の番号（public.tenants.id）';
COMMENT ON COLUMN public.secretary_rules.status IS '状態: candidate=候補・approved=使う・rejected=捨てた・removed=外した';
COMMENT ON COLUMN public.secretary_rules.rule_text IS '決まりの文（150 字まで。approved のときは空白以外が 1 字以上）';
COMMENT ON COLUMN public.secretary_rules.source_text IS '元になった利用者の文 1 つ（1000 字まで）';
COMMENT ON COLUMN public.secretary_rules.source_kind IS '元になった秘書の答えの種類（invoice・event・unknown・rule_proposal・rule_list）';
COMMENT ON COLUMN public.secretary_rules.source_reply IS '元になった秘書の答えの文（200 字まで）';
COMMENT ON COLUMN public.secretary_rules.created_by IS '作った人（public.users.id）';
COMMENT ON COLUMN public.secretary_rules.decided_by IS '使う・捨てる・外すを決めた人（public.users.id）。人が消えたら空になる';
COMMENT ON COLUMN public.secretary_rules.created_at IS '作った時刻';
COMMENT ON COLUMN public.secretary_rules.decided_at IS '決めた時刻。候補のあいだは空';
COMMENT ON TABLE public.secretary_rule_checks IS '前と同じに読めるか確かめる試しの結果。1 回の試しごとに 1 行（ADR-1077）';
COMMENT ON COLUMN public.secretary_rule_checks.id IS '番号';
COMMENT ON COLUMN public.secretary_rule_checks.tenant_id IS '会社の番号（public.tenants.id）';
COMMENT ON COLUMN public.secretary_rule_checks.started_by IS '試しを始めた人（public.users.id）。人が消えたら空になる';
COMMENT ON COLUMN public.secretary_rule_checks.sdk IS '試しに使った AI の道具の名前（値の一覧は backend/app/services/llm_budget.py の USAGE_SDKS が正本）';
COMMENT ON COLUMN public.secretary_rule_checks.model IS '試しに使った AI のモデルの名前';
COMMENT ON COLUMN public.secretary_rule_checks.rules_count IS '試しのときに付けていた決まりの数';
COMMENT ON COLUMN public.secretary_rule_checks.status IS '状態: running=実行中・done=終わった・failed=途中で失敗';
COMMENT ON COLUMN public.secretary_rule_checks.ok IS '種類が合った件数';
COMMENT ON COLUMN public.secretary_rule_checks.ng IS '種類が合わなかった件数';
COMMENT ON COLUMN public.secretary_rule_checks.unmeasured IS '測れなかった件数（混み合い・時間切れでやり直しても取れなかった）';
COMMENT ON COLUMN public.secretary_rule_checks.total IS '試しの件数';
COMMENT ON COLUMN public.secretary_rule_checks.started_at IS '始めた時刻';
COMMENT ON COLUMN public.secretary_rule_checks.progress_at IS '最後に進んだ時刻（止まっていないかを見る）';
COMMENT ON COLUMN public.secretary_rule_checks.finished_at IS '終わった時刻。実行中のあいだは空';

ALTER TABLE public.secretary_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.secretary_rules FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS secretary_rules_tenant ON public.secretary_rules;
CREATE POLICY secretary_rules_tenant ON public.secretary_rules FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
           OR current_setting('app.is_operator', true) = 'true')
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                OR current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.secretary_rule_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.secretary_rule_checks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS secretary_rule_checks_tenant ON public.secretary_rule_checks;
CREATE POLICY secretary_rule_checks_tenant ON public.secretary_rule_checks FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
           OR current_setting('app.is_operator', true) = 'true')
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
                OR current_setting('app.is_operator', true) = 'true');

-- 使用の記録の使いみちに secretary_regression を足す（定義に値があれば何もしない。形は 20261103_120000_create_ai_job_assignments.sql の 1-7 と同じ）
DO $$
DECLARE
    purpose_def TEXT;
BEGIN
    SELECT pg_get_constraintdef(con.oid) INTO purpose_def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.llm_usage_events'::regclass
      AND con.conname = 'llm_usage_events_purpose_check';

    IF purpose_def IS NULL OR purpose_def NOT LIKE '%secretary_regression%' THEN
        ALTER TABLE public.llm_usage_events DROP CONSTRAINT IF EXISTS llm_usage_events_purpose_check;
        ALTER TABLE public.llm_usage_events
            ADD CONSTRAINT llm_usage_events_purpose_check
            CHECK (purpose IN ('line_extraction', 'line_extraction_shadow', 'inventory_parse_fallback', 'translation_inbound', 'translation_inbound_escalation', 'translation_outbound', 'secretary_intent', 'secretary_regression'));
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE ON public.secretary_rules, public.secretary_rule_checks TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.secretary_rules_id_seq, public.secretary_rule_checks_id_seq TO salesanchor_app;
    END IF;
END $$;

COMMIT;
