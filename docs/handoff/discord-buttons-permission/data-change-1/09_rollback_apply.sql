-- 戻しの本実行。5 行を消し、件数ガードが通ったときだけ COMMIT。コードの付け替え（card-impl-2）を戻した後にだけ使う。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';

-- 5 行を消す。各社の role_permissions の行は ON DELETE CASCADE（backend/app/services/tenant.py:514）で一緒に消える。
-- 消した件数と残りの件数を確かめる。違えば RAISE EXCEPTION（ON_ERROR_STOP で止まり、先に進まない）
DO $guard$
DECLARE
    n_deleted integer;
    n_total   integer;
    n_left    integer;
BEGIN
    DELETE FROM public.permissions
     WHERE key IN ('leads.discord_invite', 'leads.discord_resync', 'leads.discord_remove_channel',
                   'leads.discord_kick', 'leads.discord_ban');
    GET DIAGNOSTICS n_deleted = ROW_COUNT;
    SELECT count(*) INTO n_total FROM public.permissions;
    SELECT count(*) INTO n_left FROM public.permissions WHERE key LIKE 'leads.discord\_%';
    IF n_deleted <> 5 THEN RAISE EXCEPTION 'deleted rows must be 5 but was %', n_deleted; END IF;
    IF n_left <> 0 THEN RAISE EXCEPTION 'remaining rows must be 0 but was %', n_left; END IF;
    IF n_total <> 130 THEN RAISE EXCEPTION 'total must be 130 but was %', n_total; END IF;
END
$guard$;

SELECT 'COMMIT_NEXT';
COMMIT;
SELECT 'COMMIT_DONE';
