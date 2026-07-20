-- deals廃止 段階②(D3): orders.deal_id の NOT NULL を解除（company_id 直参照へ移行）
-- 設計: docs/specs/db-ssot/deal-removal/design.md §4.6
-- 冪等: 既に nullable ならそのまま成功する
DO $$
DECLARE
    s TEXT;
BEGIN
    FOR s IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        EXECUTE format(
            'ALTER TABLE %I.orders ALTER COLUMN deal_id DROP NOT NULL',
            s
        );
        RAISE NOTICE 'orders.deal_id nullable on %', s;
    END LOOP;
END $$;
