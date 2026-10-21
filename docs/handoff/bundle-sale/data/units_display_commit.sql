-- ADR-1027 単位の呼び名 commit: dry_run 成功の印がある時だけ実行する。canonical が表どおりの 6 行だけを更新し、件数が合わなければゼロ除算で COMMIT に進まない。
\set ON_ERROR_STOP on
BEGIN;
WITH upd AS (
    UPDATE public.line_units u SET name_ja = v.name_ja, name_en = v.name_en
    FROM (VALUES
        (9, 'Case', 'カートン', 'Case'),
        (10, 'Box', 'BOX', 'Box'),
        (11, 'Pack', 'パック', 'Pack'),
        (12, 'Piece', '枚', 'Piece'),
        (13, 'Set', 'セット', 'Set'),
        (16, '個', '個', 'Item')
    ) AS v(id, canonical, name_ja, name_en)
    WHERE u.id = v.id AND u.canonical = v.canonical
    RETURNING u.id
)
SELECT CASE WHEN count(*) = 6 THEN 'UPDATED|6' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
SELECT CASE WHEN count(*) = 6 THEN 'CHECK_OK 6' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_units
 WHERE (id, canonical, name_ja, name_en) IN (
        (9, 'Case', 'カートン', 'Case'),
       (10, 'Box', 'BOX', 'Box'),
       (11, 'Pack', 'パック', 'Pack'),
       (12, 'Piece', '枚', 'Piece'),
       (13, 'Set', 'セット', 'Set'),
       (16, '個', '個', 'Item'));
COMMIT;
SELECT 'COMMIT_DONE';
