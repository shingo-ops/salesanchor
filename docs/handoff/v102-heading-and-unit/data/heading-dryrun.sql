-- ADR-1041 見出し 設定 v102_condition_heading 投入 dryrun: 入れて検査して必ず ROLLBACK。key は主キー（reader 鍵で確認済み）。件数が1でなければゼロ除算で失敗する。
\set ON_ERROR_STOP on
BEGIN;
WITH up AS (
    INSERT INTO public.tcg_distribution_settings (key, value, note) VALUES
        ('v102_condition_heading', '{"max_lines": 3, "sentence_end": ["。", "ます", "ません", "ございます", "おります", "です", "下さい", "ください"], "trailing_chars": "!！。"}', '状態の見出しの規則（ADR-1041 What 5）: 文の終わりの語・記号と塊の最大行数。{} は取り消し（働かない）。コードの検査に通らない値は使われない')
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
    RETURNING key
)
SELECT CASE WHEN count(*) = 1 THEN 'UPSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM up;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings
 WHERE key = 'v102_condition_heading'
   AND value = '{"max_lines": 3, "sentence_end": ["。", "ます", "ません", "ございます", "おります", "です", "下さい", "ください"], "trailing_chars": "!！。"}';
ROLLBACK;
SELECT 'DRYRUN_OK';
