-- v102 規則直し 便1 dryrun: 入れて検査して必ず ROLLBACK。CN0004・CN0002 の search_kw と CN0003・CN0001 の exclude_kw の末尾に「,傷あり,傷有,キズあり,キズ有」を足す。件数が4でなければゼロ除算で失敗する。
\set ON_ERROR_STOP on
BEGIN;
WITH up AS (
    UPDATE public.line_conditions SET
    search_kw = CASE WHEN code IN ('CN0002','CN0004') THEN search_kw || ',傷あり,傷有,キズあり,キズ有' ELSE search_kw END,
    exclude_kw = CASE WHEN code IN ('CN0001','CN0003') THEN exclude_kw || ',傷あり,傷有,キズあり,キズ有' ELSE exclude_kw END,
    updated_at = NOW()
     WHERE (code = 'CN0001' AND md5(exclude_kw) = '47e88628b2211ff61dccdd15e9fb906e') OR (code = 'CN0002' AND md5(search_kw) = '47e88628b2211ff61dccdd15e9fb906e') OR (code = 'CN0003' AND md5(exclude_kw) = '47e88628b2211ff61dccdd15e9fb906e') OR (code = 'CN0004' AND md5(search_kw) = 'cd36d603d8a78e03af6e51ecadfac3ba')
    RETURNING code
)
SELECT CASE WHEN count(*) = 4 THEN 'UPDATED|4' ELSE (1 / (count(*) - count(*)))::text END FROM up;
SELECT CASE WHEN count(*) = 4 THEN 'CHECK_OK 4' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE (code = 'CN0001' AND md5(exclude_kw) = '76f0408b4f328a26ea961871770c0213') OR (code = 'CN0002' AND md5(search_kw) = '76f0408b4f328a26ea961871770c0213') OR (code = 'CN0003' AND md5(exclude_kw) = '76f0408b4f328a26ea961871770c0213') OR (code = 'CN0004' AND md5(search_kw) = '8166ec8e5ff7aeac5006589fdbae6f04');
ROLLBACK;
SELECT 'DRYRUN_OK';
