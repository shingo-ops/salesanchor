-- テナント単位フィーチャーフラグ (tenant_features) テーブル新設
-- 目的: テナントごとに機能のON/OFFを制御する開発用スイッチ
-- 設計: public スキーマに配置。RLS で自テナント行のみ参照可。
-- 冪等: CREATE TABLE IF NOT EXISTS + DROP POLICY IF EXISTS を使用。

CREATE TABLE IF NOT EXISTS public.tenant_features (
    tenant_id INTEGER NOT NULL,
    feature_key TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, feature_key)
);

-- RLS 有効化（冪等）
ALTER TABLE public.tenant_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_features FORCE ROW LEVEL SECURITY;

-- テナント自身の行のみ参照可
-- キャスト: NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
--   - missing_ok=true: 変数未設定なら NULL を返す（フェイルクローズ）
--   - NULLIF: clear_tenant_context が SET app.tenant_id='' した場合も NULL 扱い → 全行 deny
-- 参照: migrations/20260623_100000_rls_message_translations.sql
DROP POLICY IF EXISTS tenant_features_tenant_isolation ON public.tenant_features;
CREATE POLICY tenant_features_tenant_isolation
    ON public.tenant_features
    FOR ALL
    USING (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    );

-- 運営 (app.is_operator=true) は全件参照可
-- 参照: migrations/20260626_130000_force_rls_public_products.sql
DROP POLICY IF EXISTS tenant_features_operator ON public.tenant_features;
CREATE POLICY tenant_features_operator
    ON public.tenant_features
    FOR ALL
    USING (
        current_setting('app.is_operator', true) = 'true'
    );
