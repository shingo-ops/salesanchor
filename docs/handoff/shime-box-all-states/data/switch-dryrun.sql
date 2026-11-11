-- ADR-1073 便4 設定 v102_shime_box_all_states 投入 dryrun: 入れて検査して必ず ROLLBACK。key は主キー。件数が1でなければゼロ除算で失敗する。
-- 既に行があれば INSERT が主キーで失敗して止まる（上書きしない）。
\set ON_ERROR_STOP on
BEGIN;
WITH up AS (
    INSERT INTO public.tcg_distribution_settings (key, value, note) VALUES
        ('v102_shime_box_all_states', '{"keep_words": ["まだあります"]}', '状態を書かない箱の〆の規則12h（ADR-1073）: JSON（keep_words＝在庫が残ると書く語の配列）。行を消すと働かない。コードの検査に通らない値は使われない')
    RETURNING key
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM up;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings
 WHERE key = 'v102_shime_box_all_states'
   AND value = '{"keep_words": ["まだあります"]}';
ROLLBACK;
SELECT 'DRYRUN_OK';
