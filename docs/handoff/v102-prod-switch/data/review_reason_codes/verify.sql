-- 便A verify（読み取り）: code|source|fix_stage を code 順に出す。
SELECT code || '|' || source || '|' || fix_stage FROM public.review_reason_codes ORDER BY code;
SELECT 'VERIFY_DONE';
