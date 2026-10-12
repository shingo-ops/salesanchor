-- Opened box search_kw 追加 dryrun: 更新して検査して必ず ROLLBACK。
\set ON_ERROR_STOP on
BEGIN;
WITH u AS (
    UPDATE public.conditions
       SET search_kw = 'ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み,検品のため開封済み'
     WHERE id = 18
       AND search_kw = 'ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み'
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'UPDATED|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;
SELECT 'AFTER|' || search_kw FROM public.conditions WHERE id = 18;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.conditions
 WHERE id = 18 AND search_kw = 'ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み,検品のため開封済み';
ROLLBACK;
SELECT 'DRYRUN_OK';
