-- unit_aliases に不足エイリアス追加
-- public.unit_aliases は public.line_unit_aliases の VIEW のため実テーブルに INSERT する
-- unit_id=9: Case（カートン系）, unit_id=10: Box（BOX系）, unit_id=12: Piece（枚/冊系）
INSERT INTO public.line_unit_aliases (alias_text, unit_id, lang) VALUES ('冊', 12, 'ja') ON CONFLICT ON CONSTRAINT uq_unit_aliases_unit_lang DO NOTHING;
INSERT INTO public.line_unit_aliases (alias_text, unit_id, lang) VALUES ('OX', 10, 'ja') ON CONFLICT ON CONSTRAINT uq_unit_aliases_unit_lang DO NOTHING;
INSERT INTO public.line_unit_aliases (alias_text, unit_id, lang) VALUES ('ﾏｽﾀｰｶｰﾄﾝ', 9, 'ja') ON CONFLICT ON CONSTRAINT uq_unit_aliases_unit_lang DO NOTHING;
