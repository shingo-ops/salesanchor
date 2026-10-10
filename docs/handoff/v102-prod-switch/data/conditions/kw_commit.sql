-- Opened box search_kw 追加 commit: dryrun 成功の印がある時だけ実行する。
-- id=18 かつ search_kw が現在値と完全一致する時だけ更新。更新件数が1でなければ失敗（COMMIT に進まない）。
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
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.conditions
 WHERE id = 18 AND search_kw = 'ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み,検品のため開封済み';
COMMIT;
SELECT 'COMMIT_DONE';
