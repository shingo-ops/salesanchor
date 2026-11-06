-- ADR-1063 便2: ログイン許可の依頼に「会社の管理者（持ち主）に頼んだ時刻」の列を足す（追加のみ・冪等）
--
-- 設計: docs/handoff/tenant-owner-login-approval/design.md 便2
-- 目的: 社員が新しい機械で「会社の管理者に頼む」を押した時刻を残す。持ち主の一覧はこの列が入った依頼だけを出す（便3）。
-- 足すだけ・NULL 可・既定値なし。既にある行は書き換わらない。値はアプリ（便3）が入れる。
-- RLS は付けない（表 public.auth_login_requests は ADR-1055 段A でログイン前に hash で1行を引くため RLS なし。列を足しても変えない）。
-- ai_ro・ai_cloud の見せ方: timestamptz は素通しの型のため分類の行は要らない。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（索引も一緒に消える。便3 が出る前なら使う人はいない）:
--   ALTER TABLE public.auth_login_requests DROP COLUMN IF EXISTS admin_requested_at;

ALTER TABLE public.auth_login_requests
    ADD COLUMN IF NOT EXISTS admin_requested_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN public.auth_login_requests.admin_requested_at IS '社員が「会社の管理者に頼む」を押した時刻。NULL は頼んでいない。ADR-1063';

CREATE INDEX IF NOT EXISTS ix_auth_login_requests_admin_requested
    ON public.auth_login_requests (admin_requested_at)
    WHERE status = 'pending' AND admin_requested_at IS NOT NULL;
