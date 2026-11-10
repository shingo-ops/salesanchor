-- 状態の言葉の追加 verify（読み取り）。KW_NEW|1（search_kw の md5 が期待どおり）・OTHERS_SAME|1（ほかの列が変更前のまま）・ONLY_CN0003|1（5語を持つ行は CN0003 だけ）・VERIFY_DONE が出ること。
-- 戻した後は、precheck の CAN_PROCEED|1 が再び出ることで確かめる。
SELECT 'KW_NEW|' || count(*) FROM public.line_conditions WHERE code = 'CN0003' AND md5(search_kw) = 'faec3d727a5b0773973089b01022287f';
SELECT 'OTHERS_SAME|' || count(*) FROM public.line_conditions WHERE code = 'CN0003' AND id = 14 AND canonical = 'Sealed box' AND app_kubun = '箱系' AND is_active = true AND priority = 4 AND created_at = '2026-09-19 16:35:26.371048+00:00'::timestamptz AND tenant_id IS NULL AND condition_def_id = 2 AND match_type = 'KEYWORD' AND effect = 'OUTPUT' AND unit_id = 10 AND md5(COALESCE(note,'')) = 'd41d8cd98f00b204e9800998ecf8427e' AND value_group = 'box' AND value_rank = 1 AND md5(COALESCE(exclude_kw,'')) = '76f0408b4f328a26ea961871770c0213';
SELECT 'ONLY_CN0003|' || count(*) FROM public.line_conditions WHERE (COALESCE(search_kw, '') || '|' || COALESCE(exclude_kw, '')) LIKE ANY (ARRAY['%シュリあり%','%シュリンク有%','%有〆%','%有り〆%']);
SELECT 'VERIFY_DONE';
