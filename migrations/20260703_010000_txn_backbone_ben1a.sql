-- 便1a: 背骨の必須化 — 遡及lead逆造成 backfill ＋ 条件付き SET NOT NULL
-- 冪等・全テナントループ。NULLが残るスキーマは NOTICE でスキップ（tenant_006 はDEMO削除後に再実行で適用）
DO $$
DECLARE s RECORD; n_orphan INT; n_left INT;
BEGIN
  FOR s IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$' ORDER BY nspname LOOP
    -- (1) 孤立 company → 遡及 lead を1件ずつ作成して紐づけ（決定的・名寄せ推測なし）
    EXECUTE format($f$
      WITH orphans AS (SELECT id, tenant_id, name FROM %I.companies WHERE lead_id IS NULL),
      created AS (
        INSERT INTO %I.leads (tenant_id, customer_name, company_name, status, notes)
        SELECT tenant_id, name, name, 'lead', '[便1a] 遡及作成: 既存companyの出自lead（属性は不明のためNULL）'
        FROM orphans RETURNING id, customer_name)
      UPDATE %I.companies c SET lead_id = cr.id
      FROM created cr, orphans o
      WHERE c.id = o.id AND cr.customer_name = o.name AND c.lead_id IS NULL$f$, s.nspname, s.nspname, s.nspname);
    -- 同名会社が複数ある場合の残余を個別処理（1社=1lead を保証）
    LOOP
      EXECUTE format('SELECT count(*) FROM %I.companies WHERE lead_id IS NULL', s.nspname) INTO n_orphan;
      EXIT WHEN n_orphan = 0;
      EXECUTE format($f$
        WITH o AS (SELECT id, tenant_id, name FROM %I.companies WHERE lead_id IS NULL ORDER BY id LIMIT 1),
        cr AS (INSERT INTO %I.leads (tenant_id, customer_name, company_name, status, notes)
               SELECT tenant_id, name, name, 'lead', '[便1a] 遡及作成' FROM o RETURNING id)
        UPDATE %I.companies SET lead_id = (SELECT id FROM cr) WHERE id = (SELECT id FROM o)$f$,
        s.nspname, s.nspname, s.nspname);
    END LOOP;
    -- (2) companies.lead_id: 全行充足したので NOT NULL（冪等）
    EXECUTE format('ALTER TABLE %I.companies ALTER COLUMN lead_id SET NOT NULL', s.nspname);
    -- (3) deals.lead_id / orders.deal_id: 違反0のスキーマのみ適用、残ればNOTICE
    EXECUTE format('SELECT count(*) FROM %I.deals WHERE lead_id IS NULL', s.nspname) INTO n_left;
    IF n_left = 0 THEN
      EXECUTE format('ALTER TABLE %I.deals ALTER COLUMN lead_id SET NOT NULL', s.nspname);
    ELSE RAISE NOTICE '[ben1a] % : deals.lead_id NULL % 件のためスキップ（DEMO削除後に再実行）', s.nspname, n_left;
    END IF;
    EXECUTE format('SELECT count(*) FROM %I.orders WHERE deal_id IS NULL', s.nspname) INTO n_left;
    IF n_left = 0 THEN
      EXECUTE format('ALTER TABLE %I.orders ALTER COLUMN deal_id SET NOT NULL', s.nspname);
    ELSE RAISE NOTICE '[ben1a] % : orders.deal_id NULL % 件のためスキップ（DEMO削除後に再実行）', s.nspname, n_left;
    END IF;
  END LOOP;
END $$;
