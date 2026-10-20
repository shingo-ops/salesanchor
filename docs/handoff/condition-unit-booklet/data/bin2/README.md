# ADR-1035 便2 記録 SQL（本番未適用）

区分「ブックレット系」をデータで入れる（状態 2 行・区分 1 行・商品 440415 の区分付け替え）。本番に流すのは Opus（担当は流さない）。
前提: コード（PR）のマージ・デプロイと、migration `20261020_100000_line_conditions_value_group_add_booklet.sql` の適用が済んでいること。

| 順 | 作業 | 期待 |
|---|---|---|
| 1 | `01_precheck.sql` | PRECHECK_OK が 6 行（canonical_unused・next_codes_unused・check_allows_booklet・unit 17=Booklet・category_absent・product_440415_category_2）。ROW 行・CONSTRAINT 行・next_codes・target_jobs は情報として出る |
| 2 | `02_apply.sql` を `-v end=ROLLBACK` で DRY-RUN | INSERTED conditions 2・INSERTED category 1・UPDATED products 1・CHECK_OK 2 行。最後に ROLLBACK |
| 3 | `02_apply.sql` を `-v end=COMMIT` | 手順 2 と同じ件数、COMMIT |
| 4 | `03_verify.sql` | VERIFY_OK が 4 行。ROW 行を 01 の ROW 行と突き合わせ、既存の行が同じであることを確かめる |
| 5 | `05_target_jobs.sql` で対象 job を数え、再解析 | 設計 K3-2・K5 を測る（再解析はこの SQL では行わない） |

戻し: `04_rollback.sql` → 対象 job を再解析。

- code は固定: CN0023（With booklet）・CN0024（Without booklet）。line_conditions.code には画面が自動で作る CN+14 桁の日時の値もあるため、最大値からの採番はしない（2026-10-20 dryrun で桁あふれ）。01 の next_codes_unused で未使用を確かめる。
- 商品の WHERE は id と今の区分 2 の両方。更新件数が 1 でなければ `1 / 0` で失敗し、COMMIT に進まない。
- 05 の対象は商品 440415 の現行行を持つ job だけ。
