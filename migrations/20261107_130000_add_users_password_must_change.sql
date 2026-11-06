-- ADR-1068 2回目: users に仮パスワードの印 password_must_change を足す（足すだけ・冪等）
--
-- 設計: docs/handoff/staff-self-registration/design.md §4-1
-- 目的: Discord で受け付けた人に仮のパスワードを渡し、自分で変えるまで他の画面を使わせない印。
-- 足すだけ。既定 false なので既にある行は変わらない。値はアプリが入れる。
-- RLS は付けない（public.users は今も RLS なし）。
-- ai_ro・ai_cloud の見せ方: 真偽値は素通しの型のため分類の行は要らない。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック:
--   ALTER TABLE public.users DROP COLUMN IF EXISTS password_must_change;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS password_must_change BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN public.users.password_must_change IS '仮のパスワードを渡された人が自分で変えるまで true にしておく印。ADR-1068';
