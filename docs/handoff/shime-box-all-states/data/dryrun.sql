-- 状態の言葉の追加 dryrun: 入れて検査して必ず ROLLBACK。CN0003（Sealed box）の search_kw の末尾に「,シュリあり,シュリンク有り,シュリンク有,有〆,有り〆」を足す。件数が1でなければゼロ除算で失敗する。
\set ON_ERROR_STOP on
BEGIN;
WITH up AS (
    UPDATE public.line_conditions SET
    search_kw = search_kw || ',シュリあり,シュリンク有り,シュリンク有,有〆,有り〆',
    updated_at = NOW()
     WHERE code = 'CN0003' AND md5(search_kw) = 'b153520fe5e8291bca582d70ab42877b'
    RETURNING code
)
SELECT CASE WHEN count(*) = 1 THEN 'UPDATED|1' ELSE (1 / (count(*) - count(*)))::text END FROM up;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0003' AND md5(search_kw) = 'faec3d727a5b0773973089b01022287f';
ROLLBACK;
SELECT 'DRYRUN_OK';
