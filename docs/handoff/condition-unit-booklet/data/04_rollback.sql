-- ADR-1035 便1 戻し。本番での実行は Opus。6 行の unit_id を NULL に戻す（WHERE に今の値も書く）。続けて対象 job を再解析する。
\set ON_ERROR_STOP on
BEGIN;
WITH u AS (
    UPDATE public.line_conditions SET unit_id = NULL, updated_at = NOW()
     WHERE (id IN (22, 21, 44, 60, 61) AND unit_id = 11) OR (id = 20 AND unit_id = 9)
    RETURNING id
)
SELECT CASE WHEN count(*) = 6 THEN 'ROLLBACK unit_id|6' ELSE (1 / (count(*) - count(*)))::text END FROM u;
COMMIT;
SELECT 'ROLLBACK_DONE';
