# review_reason_codes 初期行（便A・1回だけのデータ変更）

設計: [../../design.md](../../design.md) §12。ADR-1007（migration に値を書かない。値は記録した SQL を1回だけ実行する）。

表 `public.review_reason_codes` は migration `20261009_200000_create_review_reason_codes.sql` が作る（構造のみ）。この表に29行を入れる。

## 手順（上から順に。失敗したらそこで止まる）
1. `precheck.sql`（読み取り）: `TABLE|public.review_reason_codes`、`ROWS|0`、`APP_SELECT|t`、`PRECHECK_DONE` が出ること。
2. `dryrun.sql`: 29行を入れて件数を検査し、必ず ROLLBACK。`CHECK_OK 1` と `DRYRUN_OK` が出ること。
3. `commit.sql`: dryrun 成功の後だけ。`CHECK_OK 1` と `COMMIT_DONE`。
4. `verify.sql`（読み取り）: `code|source|fix_stage` が `seed_20261009.sql` と一致（29行）、`VERIFY_DONE`。

件数の期待: 29行（source: gemini 1・system 28 ／ fix_stage: extraction 13・analysis 16）。

## 戻し方
`rollback.sql`（29コードを指定して削除。戻すときだけ使う）。`ROLLBACK_DONE` が出ること。

## 新しい理由コードを足すとき
コード側の定数 ＋ ja.json / en.json の `reviewReason.<code>` ＋ この SQL の型で1行を足すデータ変更、の3つが揃わないと CI（`backend/tests/test_review_reason_codes_consistency.py`）が通らない。

## 記録欄（設計者が実施後に記入）
| 項目 | 内容 |
|---|---|
| 実施日時 | |
| precheck | |
| dryrun | |
| commit | |
| verify | |
