-- 戻しの本実行。7 行を消し、件数ガードが通ったときだけ COMMIT。各社の role_permissions は ON DELETE CASCADE で一緒に消える。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';

-- 消した件数と残りの件数を確かめる。違えば RAISE EXCEPTION（ON_ERROR_STOP で止まり、COMMIT に進まない）
DO $guard$
DECLARE
    n_deleted integer;
    n_total   integer;
    n_left    integer;
BEGIN
    DELETE FROM public.permissions
     WHERE category IN ('状態マスタ','商品カテゴリ')
       AND resource IN ('conditions','product_categories');
    GET DIAGNOSTICS n_deleted = ROW_COUNT;
    SELECT count(*) INTO n_total FROM public.permissions;
    SELECT count(*) INTO n_left FROM public.permissions WHERE resource IN ('conditions','product_categories');
    IF n_deleted <> 7 THEN RAISE EXCEPTION 'deleted rows must be 7 but was %', n_deleted; END IF;
    IF n_left <> 0 THEN RAISE EXCEPTION 'remaining rows must be 0 but was %', n_left; END IF;
    IF n_total <> 123 THEN RAISE EXCEPTION 'total must be 123 but was %', n_total; END IF;
END
$guard$;

SELECT 'COMMIT_NEXT';
COMMIT;
SELECT 'COMMIT_DONE';
