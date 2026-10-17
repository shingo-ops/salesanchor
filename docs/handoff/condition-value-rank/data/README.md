# 状態マスタの価値順: 値の投入（11 行・1 回だけのデータ変更）

ADR-1007（migration に値を書かない。値は記録した SQL を 1 回だけ実行する）。ADR-1023。
構造（列 `value_group`・`value_rank`）は migration `migrations/20261017_120000_line_conditions_value_rank.sql` が足す。ここは値だけ。
本番では PR のマージ・deploy の後に、Opus の指示で実行する（実装担当は実行しない）。

## 値
| 群 | code | canonical | value_rank |
|---|---|---|---|
| box | CN0003 | Sealed box | 1 |
| box | CN0004 | Damaged sealed box | 2 |
| box | CN0005 | No shrink box | 3 |
| box | CN0006 | Opened box | 4 |
| box | CN20261008072213 | Searched box | 5 |
| case | CN0001 | Case | 1 |
| case | CN0002 | Damaged case | 2 |
| case | CN0009 | Opened case | 3 |
| pack | CN0007 | Unsearched pack | 1 |
| pack | CN0010 | Searched pack | 2 |
| pack | CN0013 | AR confirmed pack | 3 |

対象外（NULL のまま）: Empty box・FLAG_SINGLE・Error・Bulk・空箱 Case。
注意: カートン（case）の順は PO の明示の y が無い。実行前に PO へ再確認し、異議があればこの SQL の値だけ直す（コードは変わらない）。

## 手順（上から順に。失敗したらそこで止まる）
1. `value_rank_precheck.sql`（読み取り）: `COLUMNS|2`・`VIEW_HAS_COLUMN|2`・`TARGET_ROWS|11`・`ALREADY_SET|0`・`PRECHECK_DONE`。
2. `value_rank_dryrun.sql`: 更新して検査し、必ず ROLLBACK。`AFTER|` が 11 行・`DRYRUN_OK`。
3. `value_rank_commit.sql`: dryrun 成功の後だけ。11 行がちょうど更新されなければ失敗（COMMIT に進まない）。`COMMIT_DONE`。
4. `value_rank_verify.sql`（読み取り）: `ROW|` が 11 行・`ROWS|11`・`VERIFY_DONE`。
5. 対象の job を再解析し、前後で現行行の数・状態・単位を数える（K6）。

## 戻し方
`value_rank_rollback.sql`（11 行を NULL に戻す。件数が 11 でなければ失敗）。`ROLLBACK_DONE`。値が空なら判定は今と同じ。

## 記録欄（Opus が実施後に記入）
| 項目 | 内容 |
|---|---|
| precheck | |
| dryrun | |
| 実施日時・commit | |
| verify | |
| 再解析と前後比較 | |
