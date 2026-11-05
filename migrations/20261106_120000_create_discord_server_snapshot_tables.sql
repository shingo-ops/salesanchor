-- discord-server-management 便2: 自社用サーバーの今の姿の記録と、反映の記録の表を作る（作るだけ・冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md §4-1・§4-6・§8 改訂3
-- discord_server_snapshots: 自社用サーバーのロールとチャンネルの構成（Opus が最初の設計図を作るためだけに使う）。
--   サーバーの番号は持たない（登録の表 tenant_discord_config の 1 か所だけ）。人の名前・書き込みは入れない。
-- discord_server_apply_runs: 反映の記録（便3 で使う。この便では作るだけ）。
-- 列名に hash・token・secret を使わない（ai_ro の拒否リスト migrations/20261017_130100_create_ai_ro_views.sql:24）。
-- RLS は付けない: 登録の表 tenant_discord_config と同じく、プログラムが tenant_id で絞る。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック: 表は残してプログラムが使わない（表を消すのは別便・PO GO）。

BEGIN;

CREATE TABLE IF NOT EXISTS public.discord_server_snapshots (
    id        BIGSERIAL    PRIMARY KEY,
    tenant_id INTEGER      NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    purpose   VARCHAR(16)  NOT NULL,
    body      JSONB        NOT NULL,
    taken_by  INTEGER,
    taken_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_discord_server_snapshots_purpose CHECK (purpose = 'own')
);

CREATE INDEX IF NOT EXISTS ix_discord_server_snapshots_tenant_taken
    ON public.discord_server_snapshots (tenant_id, taken_at DESC);

COMMENT ON TABLE public.discord_server_snapshots IS '自社用 Discord サーバーの今の姿（ロールとチャンネルの構成）。読み取りボタン 1 回で 1 行。サーバーの番号・人の名前・書き込みは持たない';
COMMENT ON COLUMN public.discord_server_snapshots.tenant_id IS '会社 tenants.id';
COMMENT ON COLUMN public.discord_server_snapshots.purpose IS '用途。own＝自社用だけ';
COMMENT ON COLUMN public.discord_server_snapshots.body IS '{"version":1,"roles":[...],"channels":[...]}。@everyone は "@everyone" と書く';
COMMENT ON COLUMN public.discord_server_snapshots.taken_by IS '読み取った人 users.id（外部キーなし）';
COMMENT ON COLUMN public.discord_server_snapshots.taken_at IS '読み取った時刻';

CREATE TABLE IF NOT EXISTS public.discord_server_apply_runs (
    id          BIGSERIAL    PRIMARY KEY,
    tenant_id   INTEGER      NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    purpose     VARCHAR(16)  NOT NULL,
    plan_digest VARCHAR(64)  NOT NULL,
    started_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    applied_by  INTEGER,
    result      JSONB,
    CONSTRAINT ck_discord_server_apply_runs_purpose CHECK (purpose = 'own')
);

CREATE INDEX IF NOT EXISTS ix_discord_server_apply_runs_tenant_started
    ON public.discord_server_apply_runs (tenant_id, started_at DESC);

COMMENT ON TABLE public.discord_server_apply_runs IS '自社用 Discord サーバーへの反映の記録（反映ボタン 1 回で 1 行）';
COMMENT ON COLUMN public.discord_server_apply_runs.tenant_id IS '会社 tenants.id';
COMMENT ON COLUMN public.discord_server_apply_runs.purpose IS '用途。own＝自社用だけ';
COMMENT ON COLUMN public.discord_server_apply_runs.plan_digest IS '確認の結果の要約値（確認のあとに変わっていないかを見る）';
COMMENT ON COLUMN public.discord_server_apply_runs.started_at IS '反映を始めた時刻';
COMMENT ON COLUMN public.discord_server_apply_runs.finished_at IS '反映が終わった時刻';
COMMENT ON COLUMN public.discord_server_apply_runs.applied_by IS '反映した人 users.id（外部キーなし）';
COMMENT ON COLUMN public.discord_server_apply_runs.result IS '行ごとの結果（成功・できない・失敗と理由）';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE
            ON public.discord_server_snapshots, public.discord_server_apply_runs TO salesanchor_app;
        GRANT USAGE, SELECT
            ON SEQUENCE public.discord_server_snapshots_id_seq, public.discord_server_apply_runs_id_seq TO salesanchor_app;
    END IF;
END $$;

COMMIT;
