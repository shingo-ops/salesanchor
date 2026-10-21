-- ADR-1027 単位の呼び名の戻し: 使うのは戻すときだけ。6 行の呼び名を NULL に戻す（NULL のときは canonical を使う）。
\set ON_ERROR_STOP on
BEGIN;
UPDATE public.line_units SET name_ja = NULL, name_en = NULL WHERE id IN (9, 10, 11, 12, 13, 16);
COMMIT;
SELECT 'ROLLBACK_DONE';
