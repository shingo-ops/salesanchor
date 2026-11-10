-- 状態の言葉の追加 precheck（読み取り）。CAN_PROCEED|1 と PRECHECK_DONE が出ること。1つでも前提と違えば 0 除算で失敗する。
-- 確かめること: (1) CN0003 が1行だけ (2) search_kw・exclude_kw の md5 が本番の今の値と一致 (3) 足す5語がどの行の search_kw・exclude_kw にも無い。
\set ON_ERROR_STOP on
SELECT 'ROWS|' || count(*) FROM public.line_conditions WHERE code = 'CN0003';
SELECT 'CAN_PROCEED|' || CASE WHEN
    (SELECT count(*) FROM public.line_conditions WHERE code = 'CN0003') = 1
    AND (SELECT count(*) FROM public.line_conditions WHERE code = 'CN0003' AND md5(search_kw) = 'b153520fe5e8291bca582d70ab42877b' AND md5(COALESCE(exclude_kw, '')) = '76f0408b4f328a26ea961871770c0213') = 1
    AND (SELECT count(*) FROM public.line_conditions
          WHERE (COALESCE(search_kw, '') || '|' || COALESCE(exclude_kw, '')) LIKE ANY (ARRAY['%シュリあり%','%シュリンク有%','%有〆%','%有り〆%'])) = 0
  THEN 1 ELSE 1 / (SELECT count(*) - count(*) FROM public.line_conditions) END;
SELECT 'PRECHECK_DONE';
