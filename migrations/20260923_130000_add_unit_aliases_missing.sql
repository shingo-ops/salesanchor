-- Migration: 不足していた unit_aliases を追加
-- 「冊」→ Piece (unit_id=12)
-- 「ﾏｽﾀｰｶｰﾄﾝ」→ Case (unit_id=9)
-- 「OX」→ Box (unit_id=10)（BOXのtypo）

INSERT INTO public.line_unit_aliases (unit_id, alias_text, lang)
VALUES
    (12, '冊',        'ja'),
    (9,  'ﾏｽﾀｰｶｰﾄﾝ', 'ja'),
    (10, 'OX',        'ja')
ON CONFLICT (unit_id, lang, alias_text) DO NOTHING;
