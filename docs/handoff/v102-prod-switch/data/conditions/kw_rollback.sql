-- Opened box search_kw 追加の戻し: 使うのは戻すときだけ。現在値（追加前）に戻す。
-- 追加後の値と完全一致する時だけ戻す。更新件数が1でなければ失敗。
\set ON_ERROR_STOP on
BEGIN;
WITH u AS (
    UPDATE public.conditions
       SET search_kw = 'ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み'
     WHERE id = 18
       AND search_kw = 'ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み,検品のため開封済み'
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLED_BACK|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;
COMMIT;
SELECT 'ROLLBACK_DONE';
