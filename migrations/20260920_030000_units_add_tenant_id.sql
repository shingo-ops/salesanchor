-- 単位マスタに tenant_id を追加（NULL=共用/LINE解析用、数値=テナント個別）
-- VIEW guard: 20260922_080000 が本番で先行デプロイ済みの場合 public.units は VIEW になっている。
-- VIEW に対して ALTER TABLE / CREATE INDEX は不可のため、実テーブルの場合のみ実行する。
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = 'units' AND c.relkind = 'r'
    ) THEN
        ALTER TABLE public.units ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES public.tenants(id);
        CREATE INDEX IF NOT EXISTS idx_units_tenant_id ON public.units (tenant_id);
        RAISE NOTICE '20260920_030000: public.units は BASE TABLE — tenant_id 追加完了';
    ELSE
        RAISE NOTICE '20260920_030000: public.units は BASE TABLE でない（VIEW の可能性）— スキップ';
    END IF;
END $$;
