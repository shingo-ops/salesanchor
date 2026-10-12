-- ADR-1008 P1: companies.sales_rep_id の参照先を tenant staff(id) から public.users(id) に付け替える。
-- 目的: 担当者の正本を public.users(id) の1か所にする（構造のみ。値の付け替えは別途 D2）。
-- 冪等: 既存の staff 向け外部キーを外し、fk_companies_sales_rep_user が無ければ作る。2回流しても同じ結果。

DO $$
DECLARE
    schema_rec RECORD;
    fk_name text;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname
    LOOP
        IF to_regclass(schema_rec.nspname || '.companies') IS NULL THEN
            CONTINUE;
        END IF;

        -- sales_rep_id の staff(id) 向け外部キー（fk_companies_sales_rep / companies_sales_rep_id_fkey）を全て外す
        FOR fk_name IN
            SELECT conname FROM pg_constraint
            WHERE conrelid = (schema_rec.nspname || '.companies')::regclass
              AND contype = 'f'
              AND pg_get_constraintdef(oid) LIKE 'FOREIGN KEY (sales_rep_id) REFERENCES%'
              AND pg_get_constraintdef(oid) LIKE '%staff(id)%'
        LOOP
            EXECUTE format('ALTER TABLE %I.companies DROP CONSTRAINT %I', schema_rec.nspname, fk_name);
        END LOOP;

        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = (schema_rec.nspname || '.companies')::regclass
              AND contype = 'f'
              AND conname = 'fk_companies_sales_rep_user'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.companies ADD CONSTRAINT fk_companies_sales_rep_user '
                'FOREIGN KEY (sales_rep_id) REFERENCES public.users(id) ON DELETE SET NULL',
                schema_rec.nspname
            );
        END IF;
    END LOOP;
END $$;
