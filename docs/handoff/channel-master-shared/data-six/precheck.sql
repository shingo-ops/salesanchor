-- 共用6行の投入 precheck（読み取りだけ）。設計 design.md §3。前提が違えばゼロ除算で止まる。
-- 1) 新しい表は空（共用も会社の行も 0）
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters)=0 THEN 1 ELSE 0 END) AS public_channel_masters_must_be_empty;
-- 2) 5社の古い名簿は、どれも同じ6つだけ（会社が足した行 0＝移す行 0）
SELECT 1 / (CASE WHEN (SELECT count(*) FROM (
  SELECT platform FROM tenant_001.channel_masters UNION ALL SELECT platform FROM tenant_003.channel_masters UNION ALL
  SELECT platform FROM tenant_004.channel_masters UNION ALL SELECT platform FROM tenant_005.channel_masters UNION ALL
  SELECT platform FROM tenant_006.channel_masters) x
  WHERE platform NOT IN ('messenger','instagram','discord','phone','in_person','whatsapp'))=0 THEN 1 ELSE 0 END) AS tenant_extra_rows_must_be_zero;
-- 3) 会社の名簿を持つのは 001・003・004・005・006 の5つだけ（他の会社の古い表が無い）
SELECT 1 / (CASE WHEN (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE c.relname='channel_masters' AND n.nspname LIKE 'tenant\_%')=5 THEN 1 ELSE 0 END) AS tenant_tables_must_be_5;
