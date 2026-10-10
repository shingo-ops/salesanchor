-- COMMIT: 複数を指す言葉 4 語を登録（PO 決定 2026-10-10 y）。dryrun.sql で 4 行を確認してから実行
BEGIN;

INSERT INTO public.knowledge_rules
    (category, pattern_type, pattern, priority, language, is_active, description)
SELECT 'followup_plural_word', 'substring', v.word, 100, 'ja', TRUE,
       '複数を指す言葉（PO 2026-10-10 y）。v102 で直前・過去の投稿から商品を1つに決めない'
FROM (VALUES ('両方'), ('全部'), ('全て'), ('どちらも')) AS v(word)
WHERE NOT EXISTS (
    SELECT 1 FROM public.knowledge_rules k
    WHERE k.category = 'followup_plural_word' AND k.pattern = v.word
);

COMMIT;
