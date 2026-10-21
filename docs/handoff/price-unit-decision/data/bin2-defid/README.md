# 価格で単位を決める 便2 記録 SQL「札と組の一覧」（本番未適用）

ADR-1036・設計 `docs/handoff/price-unit-decision/design.md` の B2 と「記録 SQL（札と組の一覧）」。ADR-1007 の形（precheck・dryrun・commit・verify・rollback）。コードは変えない。本番に流すのは PO（`!`）または Opus で、担当は流さない。

## やること
- 状態マスタ `public.line_conditions` の 8 行に、種類の札 `condition_def_id` を入れる（札は `public.condition_definitions.code` から引く。id は直書きしない）。

  | code | 状態 | 群 | 入れる札 |
  |---|---|---|---|
  | CN0001 | Case | case | SEALED |
  | CN0003 | Sealed box | box | SEALED |
  | CN0004 | Damaged sealed box | box | DAMAGED |
  | CN0005 | No shrink box | box | NO_SHRINK |
  | CN0006 | Opened box | box | OPENED |
  | CN0009 | Opened case | case | OPENED |
  | CN0007 | Unsearched pack | pack | UNSEARCHED |
  | CN0010 | Searched pack | pack | SEARCHED |

- 触らない: CN0002（札 DAMAGED のまま）・CN20261008072213（札 SEARCHED のまま）・CN0013（札なしのまま）。
- 種類と単位の組の一覧 `public.unit_condition_links` に 2 行足す: CASE×SEALED・BOX×SEARCHED（`quantity_units.code` と `condition_definitions.code` から引く）。11 行 → 13 行。PO 合意 2026-10-21（カートン CN0001 は未開封、サーチ済みの箱 CN20261008072213 は今のままサーチ済み）。

## 流す順序

| 順 | 作業 | 期待 |
|---|---|---|
| 1 | `precheck.sql` | `PRECHECK_OK` が 10 行（defs 6・quantity_units CASE,BOX 1x2・targets 8・codes 8x1・keep 2・cn0013 null・labeled_in_groups 2・tenant_rows 0・links_new_absent・links 11）と `PRECHECK_DONE`。ROW 行が 27 行（commit 後の verify と突き合わせる基準） |
| 2 | `dryrun.sql` | `UPDATED labels\|8`・`INSERTED links\|2`・取引の中で verify の検査 `VERIFY_OK` 6 行、最後に ROLLBACK と `DRYRUN_OK`。何も残らない |
| 3 | `commit.sql` | `UPDATED labels\|8`・`CHECK_OK labels 8`・`INSERTED links\|2`・`CHECK_OK links 13`・`CHECK_OK keep 2`・`COMMIT_DONE` |
| 4 | `verify.sql` | `VERIFY_OK` が 6 行（pairs 15/15・group_unit 3・dup_groups 0・cn0013 null・links_new 2・links 13）と `VERIFY_DONE`。ROW 行を precheck の ROW 行と突き合わせ、変わったのが 8 行の `condition_def_id` だけであることを確かめる |

コードより先に流す（設計「反映の順」）。今は札を読むコードが無いので判定は変わらない。変わるのは管理画面「状態マスタ」の名前の表示だけ。

## 失敗したとき
- どの検査も、件数が合わなければ `(1 / (count(*) - count(*)))` のゼロ除算で失敗する（`\set ON_ERROR_STOP on`）。commit・dryrun・rollback は取引の中なので、失敗しても何も残らない。
- 失敗した検査の直前に出る `DIFF ...|` 行が、違った行の code・名前（verify は 群・種類・code）を出す。

## 戻し方
`rollback.sql`。**コード（札を読む便2）を revert した後に**流す。コードが札を読んでいる間に札を消すと、便BB の Box・Case も何もしなくなる（設計「戻し方」）。8 行の札を NULL に戻し、組の一覧の 2 行を消す。CN0002・CN20261008072213 の札は触らない。

## 読み取り専用の道（reader 鍵・ADR-1024）で流す
- `precheck.sql` と `verify.sql` は、各 SELECT が 1 文で自己完結している。reader 鍵の道は 1 回 1 文なので、`public.` を `ai_ro.public__` に読み替え、`\set` 行と `--` 行を除き、`;` で区切って 1 文ずつ送れば流せる。読むのは `line_conditions`・`line_units`・`condition_definitions`・`quantity_units`・`unit_condition_links` の 5 つ（どれも `ai_ro.public__*` にある）。
- `dryrun.sql`・`commit.sql`・`rollback.sql` は書き込みを含むので reader 鍵では流せない。
- 作成時の読み取り確認（2026-10-21）: precheck は reader 鍵で全文が通り、`PRECHECK_OK` 10 行・`PRECHECK_DONE`。commit 前の verify は期待どおり、札が空の 8 組が `DIFF pair` に出る（CN0002・CN20261008072213 の 2 組は一致）。
