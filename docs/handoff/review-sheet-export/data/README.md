# tcg_distribution_targets.review_sheet_name の設定（PR①・1回だけのデータ変更）

設計: [../design.md](../design.md) §4。ADR-1007（migration に値を書かない。値は記録した SQL を1回だけ実行する）。

列 `review_sheet_name` は migration `20261012_210000_add_tcg_distribution_targets_review_sheet_name.sql` が作る（構造のみ）。配信先「配信テスト」（spreadsheet_id `1unwFM3MZikSmQjZ744uxhvzG2ENhuhcDsvse1dfSrm4`）の1行だけに '要確認' を入れる。ほかの行は NULL のまま（NULL なら要確認タブには出さない）。

## 手順（上から順に。失敗したらそこで止まる。PR① の本番反映の後、PR② のマージの前）
1. `rs_precheck.sql`（読み取り）: `COLUMN|1`、`TARGET_ROWS|1`、`TARGET_NULL|1`、`OTHER_NOT_NULL|0`、`ALL_ROWS|3`、`PRECHECK_DONE`。
2. `rs_dryrun.sql`: 1行を更新して検査し、必ず ROLLBACK。`UPDATED|1`・`CHECK_OK 1`・`SET_ROWS_OK 1`・`DRYRUN_OK`。
3. `rs_commit.sql`: dryrun 成功の後だけ。`UPDATED|1`・`CHECK_OK 1`・`SET_ROWS_OK 1`・`COMMIT_DONE`。
4. `rs_verify.sql`（読み取り）: 配信テストだけ「要確認」、ほかの2行は NULL、`SET_ROWS|1`、`ALL_ROWS|3`、`VERIFY_DONE`。

## 戻し方
`rs_rollback.sql`（配信テストの1行を NULL に戻す。戻すときだけ使う）。`ROLLBACK_DONE` が出ること。

## 記録欄（設計者が実施後に記入）
| 項目 | 内容 |
|---|---|
| 実施日時 | |
| precheck | |
| dryrun | |
| commit | |
| verify | |
