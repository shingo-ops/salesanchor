-- 登録後の確認（読み取りのみ）。期待: 4 行
-- 読む側（backend/app/services/gemini_raw_copy_v102_product_first.py:111-115）と同じ SELECT
SELECT pattern FROM public.knowledge_rules
WHERE category = 'followup_plural_word' AND pattern_type = 'substring' AND is_active = TRUE
ORDER BY priority, id;

-- 件数（期待: 4）
SELECT count(*) AS n
FROM public.knowledge_rules
WHERE category = 'followup_plural_word' AND pattern_type = 'substring' AND is_active = TRUE;

-- 他カテゴリが増減していないこと（登録前: block_delimiter 18 / message_exclude 9 / message_exclude_no_digit 2 / status_keyword 4）
SELECT category, count(*) AS n
FROM public.knowledge_rules
GROUP BY category
ORDER BY category;
