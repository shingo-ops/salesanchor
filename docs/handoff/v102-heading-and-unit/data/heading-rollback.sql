-- ADR-1041 見出し 設定 v102_condition_heading の戻し: 値を '{}'（取り消し）に上書きする。{} なら状態の見出しは働かない（行は残る）。
\set ON_ERROR_STOP on
BEGIN;
UPDATE public.tcg_distribution_settings SET value = '{}', updated_at = NOW() WHERE key = 'v102_condition_heading' RETURNING key;
COMMIT;
SELECT 'ROLLBACK_DONE';
