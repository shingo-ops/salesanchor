-- Discord の 5 つの権限を足し、今と同じ役割に付ける本実行。件数ガードが通ったときだけ COMMIT。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';

-- 1) 権限の一覧に Discord の 5 行を足す（区分は既存の「リード」。役割の画面は description をそのまま出す）
INSERT INTO public.permissions (key, resource, action, description, category) VALUES
    ('leads.discord_invite',         'leads', 'discord_invite',         'Discord 専用チャンネルへの招待',   'リード'),
    ('leads.discord_resync',         'leads', 'discord_resync',         'Discord ロールの再同期',           'リード'),
    ('leads.discord_remove_channel', 'leads', 'discord_remove_channel', 'Discord 専用チャンネルから外す',   'リード'),
    ('leads.discord_kick',           'leads', 'discord_kick',           'Discord サーバーからの退出（Kick）', 'リード'),
    ('leads.discord_ban',            'leads', 'discord_ban',            'Discord からの永久追放（BAN）',     'リード')
ON CONFLICT (key) DO NOTHING;

-- 2) 今と同じ人が同じボタンを使えるように写す
--    leads.update を持つ役割 → 招待・再同期
--    leads.delete を持つ役割 → 外す・Kick・BAN
SELECT set_config('app.tenant_id', '1', true);
INSERT INTO tenant_001.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_001.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.update'
  JOIN public.permissions np ON np.key IN ('leads.discord_invite', 'leads.discord_resync')
ON CONFLICT (role_id, permission_id) DO NOTHING;
INSERT INTO tenant_001.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_001.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.delete'
  JOIN public.permissions np ON np.key IN ('leads.discord_remove_channel', 'leads.discord_kick', 'leads.discord_ban')
ON CONFLICT (role_id, permission_id) DO NOTHING;

SELECT set_config('app.tenant_id', '3', true);
INSERT INTO tenant_003.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_003.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.update'
  JOIN public.permissions np ON np.key IN ('leads.discord_invite', 'leads.discord_resync')
ON CONFLICT (role_id, permission_id) DO NOTHING;
INSERT INTO tenant_003.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_003.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.delete'
  JOIN public.permissions np ON np.key IN ('leads.discord_remove_channel', 'leads.discord_kick', 'leads.discord_ban')
ON CONFLICT (role_id, permission_id) DO NOTHING;

SELECT set_config('app.tenant_id', '4', true);
INSERT INTO tenant_004.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_004.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.update'
  JOIN public.permissions np ON np.key IN ('leads.discord_invite', 'leads.discord_resync')
ON CONFLICT (role_id, permission_id) DO NOTHING;
INSERT INTO tenant_004.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_004.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.delete'
  JOIN public.permissions np ON np.key IN ('leads.discord_remove_channel', 'leads.discord_kick', 'leads.discord_ban')
ON CONFLICT (role_id, permission_id) DO NOTHING;

SELECT set_config('app.tenant_id', '5', true);
INSERT INTO tenant_005.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_005.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.update'
  JOIN public.permissions np ON np.key IN ('leads.discord_invite', 'leads.discord_resync')
ON CONFLICT (role_id, permission_id) DO NOTHING;
INSERT INTO tenant_005.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_005.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.delete'
  JOIN public.permissions np ON np.key IN ('leads.discord_remove_channel', 'leads.discord_kick', 'leads.discord_ban')
ON CONFLICT (role_id, permission_id) DO NOTHING;

SELECT set_config('app.tenant_id', '6', true);
INSERT INTO tenant_006.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_006.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.update'
  JOIN public.permissions np ON np.key IN ('leads.discord_invite', 'leads.discord_resync')
ON CONFLICT (role_id, permission_id) DO NOTHING;
INSERT INTO tenant_006.role_permissions (role_id, permission_id)
SELECT rp.role_id, np.id
  FROM tenant_006.role_permissions rp
  JOIN public.permissions op ON op.id = rp.permission_id AND op.key = 'leads.delete'
  JOIN public.permissions np ON np.key IN ('leads.discord_remove_channel', 'leads.discord_kick', 'leads.discord_ban')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 3) 件数ガード: 違えば RAISE EXCEPTION（ON_ERROR_STOP で止まり、先へ進まない）
--    期待値は recon.md §7-2 の実測（更新 001:5・他 4、削除 001:4・他 3）から計算した値。
DO $guard$
DECLARE
    n_total integer;
    n_new   integer;
    n integer;
    s text;
    expected integer;
    mismatch integer;
BEGIN
    SELECT count(*) INTO n_total FROM public.permissions;
    SELECT count(*) INTO n_new FROM public.permissions WHERE key LIKE 'leads.discord\_%';
    IF n_new <> 5 THEN RAISE EXCEPTION 'new keys must be 5 but was %', n_new; END IF;
    IF n_total <> 135 THEN RAISE EXCEPTION 'total must be 135 but was %', n_total; END IF;
    FOREACH s IN ARRAY ARRAY['tenant_001','tenant_003','tenant_004','tenant_005','tenant_006'] LOOP
        expected := CASE s WHEN 'tenant_001' THEN 22 ELSE 17 END;
        EXECUTE format('SELECT count(*) FROM %I.role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id WHERE p.key LIKE %L', s, 'leads.discord\_%') INTO n;
        IF n <> expected THEN RAISE EXCEPTION '% grants must be % but was %', s, expected, n; END IF;
        -- 写しの一致: 招待・再同期は leads.update の役割と、外す・Kick・BAN は leads.delete の役割と、ちょうど同じ
        EXECUTE format($q$
            SELECT count(*) FROM (
                SELECT r.id, k.key,
                       EXISTS (SELECT 1 FROM %1$I.role_permissions a JOIN public.permissions pa ON pa.id = a.permission_id
                                WHERE a.role_id = r.id AND pa.key = k.base) AS has_base,
                       EXISTS (SELECT 1 FROM %1$I.role_permissions b JOIN public.permissions pb ON pb.id = b.permission_id
                                WHERE b.role_id = r.id AND pb.key = k.key) AS has_new
                  FROM %1$I.roles r
                 CROSS JOIN (VALUES ('leads.discord_invite','leads.update'), ('leads.discord_resync','leads.update'),
                                    ('leads.discord_remove_channel','leads.delete'), ('leads.discord_kick','leads.delete'),
                                    ('leads.discord_ban','leads.delete')) AS k(key, base)
            ) x WHERE has_base <> has_new
        $q$, s) INTO mismatch;
        IF mismatch <> 0 THEN RAISE EXCEPTION '% mirror mismatch %', s, mismatch; END IF;
    END LOOP;
END
$guard$;

SELECT key, resource, action, category, description FROM public.permissions
 WHERE key LIKE 'leads.discord\_%' ORDER BY key;
SELECT 'COMMIT_NEXT';
COMMIT;
SELECT 'COMMIT_DONE';
