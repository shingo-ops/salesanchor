-- ADR-SA-03: 顧客登録トークン基盤
-- public スキーマ（テナント横断のトークン管理）
-- 担当者がリードに個別登録リンクを発行し、顧客が自分で住所・連絡先を登録する仕組み。
-- テナントはトークン（HMAC-SHA256 署名）が決める——フォーム入力ではなく構造で分離。

CREATE TABLE IF NOT EXISTS public.registration_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    lead_id INTEGER NOT NULL,
    token_hash VARCHAR(64) UNIQUE NOT NULL,  -- HMAC-SHA256 の hex
    type VARCHAR(20) NOT NULL CHECK (type IN ('register', 'add_address')),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,    -- NULL = 未使用
    created_by INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reg_tokens_hash ON public.registration_tokens (token_hash);
CREATE INDEX IF NOT EXISTS idx_reg_tokens_lead ON public.registration_tokens (lead_id);
