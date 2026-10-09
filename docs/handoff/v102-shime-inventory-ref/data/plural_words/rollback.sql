-- ROLLBACK: commit.sql で入れた 4 行だけを消す（category・pattern・description の 3 条件で絞る）
-- 期待: DELETE 4。4 以外なら ROLLBACK して止める
BEGIN;

DELETE FROM public.knowledge_rules
WHERE category = 'followup_plural_word'
  AND pattern IN ('両方', '全部', '全て', 'どちらも')
  AND description = '複数を指す言葉（PO 2026-10-10 y）。v102 で直前・過去の投稿から商品を1つに決めない';

-- 残りが 0 行であること
SELECT count(*) AS remaining
FROM public.knowledge_rules
WHERE category = 'followup_plural_word';

-- 件数が合えば COMMIT; 合わなければ ROLLBACK;
COMMIT;
