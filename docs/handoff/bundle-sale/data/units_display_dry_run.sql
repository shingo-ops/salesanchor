-- ADR-1027 単位の呼び名 dry_run: 更新して検査し、必ず ROLLBACK。更新前に canonical が表どおりでなければ 0 行で、ゼロ除算で止まる。
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
ROLLBACK;
SELECT 'DRYRUN_OK';
