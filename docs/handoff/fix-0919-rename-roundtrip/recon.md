# recon: migration 20260919_015000 の往復 RENAME

この文書は何か（1行）: 全件実行のたびに line_units / line_unit_aliases / line_conditions / line_condition_aliases が数秒消える原因と、事前検証の実測を記録したもの。

実測時の origin/main: 61702ca0cb253c824a880b078aaf0a32647f0970（2026-10-17）。
実装カード: /Users/tanizawashingo/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/linecond_missing/CARD.md
調査の原本: 同フォルダの recon.md と FACTS.md。
既存 ADR の検索: docs/adr/ で migration の値書き・無効化を引いた。ADR-1007（決定2）、ADR-155、ADR-1005。前例は PR #3544、#4051、#4018、196d75616（NEUTRALIZED 方式）。

## 1. 事実
- scripts/run_all_migrations.sh:691 が 20260919_015000_fix_view_to_table_rename.sql、:776 が 20260922_080000_rename_line_analysis_tables.sql を登録している。
- 0919 は旧名 (units 等) が VIEW のとき DROP VIEW ... CASCADE のあと line_* を元名へ RENAME する（migrations/20260919_015000_fix_view_to_table_rename.sql の旧 :32-60）。
- 0922 は旧名が BASE TABLE のとき line_* へ RENAME し、旧名 VIEW を作り直す（migrations/20260922_080000_rename_line_analysis_tables.sql:20-108）。
- 本番は 0922 以降の形のため、毎回の全件実行で 0919 の条件が成立し、0922 までの間 line_* が不在になる。
- 前例の無効化の形: git show 196d75616 -- migrations/20260905_020000_tcg_fix_product_names_t004.sql（コメント + `DO $$ BEGIN RAISE NOTICE '...'; END $$;`）。

## 2. 事前検証（使い捨て Postgres 16 の docker コンテナ。本番には接続していない）
手段: .github/workflows/migration-test.yml の job migration-full-dryrun の下準備（ベーススキーマ・Sprint1・suppliers.tenant_id）と scripts/migration-dryrun-report.py（登録 SQL を登録順に流す）。空 DB には別名表 2 つ（unit_aliases / condition_aliases）を作る migration が無いため、最小定義と数行を検証用に足した。
生ログ: /Users/tanizawashingo/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/linecond_missing/verify/

|検証|内容|0919 由来の RENAME NOTICE|最後の表の種類|
|---|---|---|---|
|A 1周目|現行、空DB|0（"is not a VIEW" 4）|line_* 4つ BASE TABLE・旧名 4つ VIEW|
|A 2周目|現行|4（Renamed line_* → 元名）|同上|
|C|A の終了状態に修正版を1回|0（neutralized 1）|同上|
|B 1周目|修正版、空DB|0（neutralized 1）|同上|
|B 2周目|修正版|0（neutralized 1）|同上|

- 失敗ファイル数: A 1周目 24 / A 2周目 23 / B 1周目 24 / B 2周目 23 / C 22。A と B は同じ周同士で失敗ファイルの集合が一致。失敗は 0919・0922 以外で、原因は空 DB に前提の表が無いこと（例: public.analysis_results が無い）。
- 行数: line_unit_aliases 2、line_condition_aliases 1、line_units 0、line_conditions 0 が A・B・C で同じ。
