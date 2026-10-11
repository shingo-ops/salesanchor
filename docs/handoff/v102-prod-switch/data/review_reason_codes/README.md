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

## 追加: quantity_not_in_text（PR #4077）
初期29行の verify 成功の後にだけ、qty_precheck（ROWS|29・HAS_QTY|0）→ qty_dryrun（CHECK_OK 1・DRYRUN_OK）→ qty_commit（CHECK_OK 1・COMMIT_DONE）→ qty_verify（quantity_not_in_text|system|extraction・ROWS|30）。戻し方 qty_rollback.sql。

| 項目 | 内容 |
|---|---|
| 実施日時 | |
| precheck | |
| dryrun | |
| commit | |
| verify | |

## 追加: quantity_unresolved（便PQ）
quantity_not_in_text の追加（qty_*）の verify 成功の後にだけ、qu_precheck（ROWS|30・HAS_QU|0）→ qu_dryrun（CHECK_OK 1・DRYRUN_OK）→ qu_commit（CHECK_OK 1・COMMIT_DONE）→ qu_verify（quantity_unresolved|system|analysis・ROWS|31）。戻し方 qu_rollback.sql（この1コードだけ戻す）。

| 項目 | 内容 |
|---|---|
| 実施日時 | 2026-10-10 21:50〜21:55 JST（Opus、PO 委任「必要な権限は全て使用して良い」・permit-danger psql write） |
| precheck | TABLE|review_reason_codes・ROWS|30・HAS_QU|0・APP_INSERT_PRIV|true・PRECHECK_DONE |
| dryrun | INSERT 0 1・CHECK_OK 1・ROLLBACK・DRYRUN_OK |
| commit | INSERT 0 1・CHECK_OK 1・COMMIT・COMMIT_DONE |
| verify | quantity_unresolved|system|analysis・ROWS|31・VERIFY_DONE |

## 追加: 理由コード4つ（便G）
price_source_mismatch / quantity_source_mismatch / value_out_of_range / item_mapping_mismatch（すべて system・analysis）。quantity_unresolved の追加（qu_*）の verify 成功（ROWS|31）の後にだけ、gt_precheck（ROWS|31・HAS_NEW|0・PRECHECK_DONE）→ gt_dryrun（INSERTED|4・CHECK_OK 4・ROWS_OK 35・DRYRUN_OK）→ gt_commit（INSERTED|4・CHECK_OK 4・ROWS_OK 35・COMMIT_DONE）→ gt_verify（4行・ROWS|35・VERIFY_DONE）。戻し方 gt_rollback.sql（この4コードだけ戻す）。値は seed_20261011_gemini_trust.sql が正本。DO ブロックは使わず、件数が違えばゼロ除算で失敗する型（kw_commit.sql と同じ）。

| 項目 | 内容 |
|---|---|
| 実施日時 | 2026-10-10T23:05Z（本 PR マージ前・Opus 実行、許可チケット psql write） |
| precheck | TABLE review_reason_codes・ROWS 31・HAS_NEW 0・PRECHECK_DONE |
| dryrun | INSERTED 4・CHECK_OK 4・ROWS_OK 35・ROLLBACK・DRYRUN_OK |
| commit | INSERTED 4・CHECK_OK 4・ROWS_OK 35・COMMIT・COMMIT_DONE |
| verify | 4行（item_mapping_mismatch・price_source_mismatch・quantity_source_mismatch・value_out_of_range、いずれも system・analysis）・ROWS 35・VERIFY_DONE |
