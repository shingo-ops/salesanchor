# recon: migration 2本の存在確認ガードの条件漏れ

## 1. 現状（変更前）
- migrations/20260920_020000_supplier_line_name_unique.sql:10-14 — information_schema.columns を `table_schema='public' AND column_name='line_name'` だけで見る。表名の条件がない。別表（public.viewer_accounts.line_name）でも真になる。
- migrations/20260920_020000_supplier_line_name_unique.sql:16-17 — `to_regclass('public.suppliers') IS NOT NULL AND col_exists` で CREATE UNIQUE INDEX。suppliers に line_name が無く viewer_accounts にだけある状態では、17行目が「列 line_name は存在しません」で落ちる。
- migrations/20260919_030000_master_ssot_fk_work_id.sql:21-25 — pg_class で relname='tcg_type_master' を見る。relkind の条件がない。VIEW でも真になる。
- migrations/20260919_030000_master_ssot_fk_work_id.sql:30-33 — 真なら ALTER TABLE ... REFERENCES public.tcg_type_master(id)。VIEW だと「参照先のリレーションはテーブルではありません」で落ちる。
- 毎デプロイ再実行: scripts/run_all_migrations.sh:697（030000）、:706（020000）。

## 2. 本番の現状（SELECT のみ。生出力: /Users/tanizawashingo/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/p5_dryrun_failures/fix/prod_before.txt）
- a) idx_suppliers_line_name_active_unique は public.suppliers に存在（line_name の部分 UNIQUE）。
- b) fk_products_work_id は products → type_master、convalidated=t、定義 `FOREIGN KEY (work_id) REFERENCES type_master(id)`。
- c) public.tcg_type_master の relkind は v（VIEW）。public で line_name 列を持つ表は suppliers と viewer_accounts。
- 要点: 本番は索引も FK も既にあるため、020000 は NOTICE でスキップ、030000 は `NOT EXISTS (pg_constraint ...)` が偽で何もしない。修正前後とも本番では何も変わらない。落ちるのは索引・制約が無い環境（CI の全件ドライラン2周目）だけ。

## 3. ガード調査（既存 migration の中身の書き換えを禁止・制限する仕組み）
- .github/workflows/migration-guard.yml — 新規ファイルは `--diff-filter=A`（81, 294行）。値の書き込み・破壊的変更・カラム churn（DROP COLUMN 等）は追加された行を見る（399-433行付近）。条件式の追加は対象外。
- scripts/migration-guard/ に value-write-allowlist.tsv 他。今回の追加行は値の書き込みでも破壊的変更でもない。
- ADR-1007 決定6（チェックサムで実行済みファイルの書き換えを止める）は「2〜5 を終えてから入る」と記載（docs/adr/ADR-1007-migration-structure-only-run-once.md:57-58）。現時点で書き換えを止める仕組みは確認していない。
- 前例: 196d75616（値書きの無効化）、PR #4419 = コミット 19b826d6e（20260919_015000 の中身を置換）。いずれも既存 migration の本文を書き換え、docs/handoff/<topic>/recon.md と design.md、台帳を付けている。同じ作法に合わせた。

## 4. 検証（使い捨て Postgres 16.15 / Homebrew。Docker は使えなかった）
- 生出力: .../fix/verify_local.txt（修正前=origin/main 版と修正後を同じ事例で実行）。
- A 修正前: viewer_accounts.line_name のみの状態で exit=3（ERROR）。修正後: exit=0・索引0。
- B 修正前: tcg_type_master が VIEW で exit=3（ERROR）。修正後: exit=0・制約0。
- A/B とも「本番相当」事例（索引あり／FK=type_master 参照・tcg_type_master は VIEW）は修正前後とも exit=0 で定義不変。BASE TABLE・制約なしでは FK が張られ、再実行で何もしない。
