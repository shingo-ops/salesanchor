-- 権限の一覧に状態マスタ・商品カテゴリの 7 キーを足す本実行。件数ガードが通ったときだけ COMMIT。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';

INSERT INTO public.permissions (key, resource, action, description, category) VALUES
    ('conditions.view',           'conditions',         'view',   '状態マスタの閲覧',                       '状態マスタ'),
    ('conditions.create',         'conditions',         'create', '状態マスタの登録',                       '状態マスタ'),
    ('conditions.update',         'conditions',         'update', '状態マスタの編集',                       '状態マスタ'),
    ('conditions.delete',         'conditions',         'delete', '状態マスタの削除',                       '状態マスタ'),
    ('product_categories.view',   'product_categories', 'view',   '商品カテゴリの閲覧',                     '商品カテゴリ'),
    ('product_categories.edit',   'product_categories', 'edit',   '商品カテゴリの登録・編集・CSV取り込み',  '商品カテゴリ'),
    ('product_categories.delete', 'product_categories', 'delete', '商品カテゴリの削除',                     '商品カテゴリ')
ON CONFLICT (key) DO NOTHING;

-- 件数ガード: 違えば RAISE EXCEPTION（ON_ERROR_STOP で止まり、COMMIT に進まない）
DO $guard$
DECLARE
    n_total integer;
    n_new   integer;
BEGIN
    SELECT count(*) INTO n_total FROM public.permissions;
    SELECT count(*) INTO n_new FROM public.permissions WHERE category IN ('状態マスタ','商品カテゴリ');
    IF n_new <> 7 THEN RAISE EXCEPTION 'new keys must be 7 but was %', n_new; END IF;
    IF n_total <> 130 THEN RAISE EXCEPTION 'total must be 130 but was %', n_total; END IF;
END
$guard$;

SELECT 'COMMIT_NEXT';
COMMIT;
SELECT 'COMMIT_DONE';
