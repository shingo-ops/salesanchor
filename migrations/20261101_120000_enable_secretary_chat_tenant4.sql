-- ADR-1056 段2: チャット秘書の会社の入口（第1段はテナント 4 だけ。冪等。既にある行は上書きしない）
SELECT set_config('app.is_operator', 'true', false);
DO $$
BEGIN
    IF to_regclass('public.tenant_features') IS NULL THEN
        RAISE NOTICE 'secretary_chat: tenant_features 表が無いので飛ばす';
        RETURN;
    END IF;
    INSERT INTO public.tenant_features (tenant_id, feature_key, enabled)
    VALUES (4, 'secretary_chat', true)
    ON CONFLICT (tenant_id, feature_key) DO NOTHING;
END $$;
