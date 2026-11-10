-- 状態の言葉の追加 rollback: CN0003 の search_kw を変更前の値（全文）に戻す。WHERE は変更後の md5 一致。件数が1でなければゼロ除算で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
BEGIN;
WITH up AS (
    UPDATE public.line_conditions SET
    search_kw = '通常品,[通常品],未開封,新品未開封,新品,シュリンク付き,シュリ付,シュリ付き,シュリンクあり,シュリ有り,シュリ有',
    updated_at = NOW()
     WHERE code = 'CN0003' AND md5(search_kw) = 'faec3d727a5b0773973089b01022287f'
    RETURNING code
)
SELECT CASE WHEN count(*) = 1 THEN 'REVERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM up;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0003' AND md5(search_kw) = 'b153520fe5e8291bca582d70ab42877b';
COMMIT;
SELECT 'ROLLBACK_DONE';
