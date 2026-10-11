-- 登録前の状態確認（読み取りのみ）。期待: 1 も 2 も 0 行
-- 1. category が followup_plural_word の行
SELECT id, category, pattern_type, pattern, priority, language, is_active
FROM public.knowledge_rules
WHERE category = 'followup_plural_word'
ORDER BY id;

-- 2. pattern が 4 語のどれかに一致する行（category 問わず）
SELECT id, category, pattern_type, pattern, priority, language, is_active
FROM public.knowledge_rules
WHERE pattern IN ('両方', '全部', '全て', 'どちらも')
ORDER BY id;

-- 3. category ごとの priority の範囲
SELECT category, count(*) AS n, min(priority) AS min_priority, max(priority) AS max_priority
FROM public.knowledge_rules
GROUP BY category
ORDER BY category;
