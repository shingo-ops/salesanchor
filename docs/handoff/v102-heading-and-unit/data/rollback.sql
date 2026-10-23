-- ADR-1041 便1 設定 v102_kubun_allowed_units の戻し: 値を '{}'（空の表）に上書きする。表が空なら区分ごとの単位の表は働かない（行は残る）。
\set ON_ERROR_STOP on
BEGIN;
UPDATE public.tcg_distribution_settings SET value = '{}', updated_at = NOW() WHERE key = 'v102_kubun_allowed_units' RETURNING key;
COMMIT;
SELECT 'ROLLBACK_DONE';
