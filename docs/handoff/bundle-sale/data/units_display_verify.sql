-- ADR-1027 単位の呼び名の verify（読み取り）。
SELECT id || '|' || canonical || '|' || COALESCE(name_ja, 'NULL') || '|' || COALESCE(name_en, 'NULL') FROM public.line_units WHERE id IN (9, 10, 11, 12, 13, 14, 15, 16, 17, 18) ORDER BY id;
SELECT 'VERIFY_DONE';
