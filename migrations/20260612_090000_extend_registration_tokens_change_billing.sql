-- ADR-127: registration_tokens.type CHECK 制約に change_billing を追加
-- public スキーマ（テナント横断）なのでテナントループ不要

ALTER TABLE public.registration_tokens
    DROP CONSTRAINT IF EXISTS registration_tokens_type_check;

ALTER TABLE public.registration_tokens
    ADD CONSTRAINT registration_tokens_type_check
        CHECK (type IN ('register', 'add_address', 'change_billing'));
