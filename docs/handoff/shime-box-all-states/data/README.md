# 状態の語を 5 つ足す（便2・1 回だけのデータ変更）

ADR-1007（値は記録した SQL を 1 回だけ実行する）。ADR-1073。設計: docs/handoff/shime-box-all-states/design.md §3 の便2。根拠: docs/handoff/shime-box-all-states/recon.md §4。

## 値

- 足す先: 状態の表 `public.line_conditions`（別名 `public.conditions`。解析は別名の方から読む・同じ行）の code `CN0003`（Sealed box）の `search_kw`。
- 足す語（末尾に足す）: `シュリあり`・`シュリンク有り`・`シュリンク有`・`有〆`・`有り〆`。
- 足す前の `search_kw` の md5: `b153520fe5e8291bca582d70ab42877b`（`rollback.sql` に全文）。足した後: `faec3d727a5b0773973089b01022287f`。Opus が 2026-11-10 に手元で計算し、2 つとも一致を確かめた。
- 語だけでは、状態の値・〆の相手・在庫は変わらない（2026-11-09 の本番の写しでのやり直し 134 投稿で、変わったのは状態の理由 176 件だけ）。

## 手順（上から順に。1 つでも期待と違えばそこで止まる）

1. `precheck.sql`（読み取り）: `ROWS|1`・`CAN_PROCEED|1`・`PRECHECK_DONE`。本番の今の値が前提と違えば 0 除算で失敗する。
2. `dryrun.sql`: 足して検査し、必ず ROLLBACK。`UPDATED|1`・`CHECK_OK 1`・`DRYRUN_OK`。
3. `commit.sql`: 2 の成功の後だけ。`UPDATED|1`・`CHECK_OK 1`・`COMMIT_DONE`。
4. `verify.sql`（読み取り）: `KW_NEW|1`・`OTHERS_SAME|1`・`ONLY_CN0003|1`・`VERIFY_DONE`。

実行は本番の書き込みの鍵が要る。AI の自動判定では止まるため、PO が `!` で流す。

## 戻し方

`rollback.sql`（足す前の全文に戻す。件数が 1 でなければ失敗）。`ROLLBACK_DONE`。戻した後は `precheck.sql` の `CAN_PROCEED|1` が再び出ることで確かめる。

## 記録欄（Opus が実施後に記入）

| 項目 | 内容 |
|---|---|
| precheck | 2026-11-10 20:37:52 JST・rc=0・`ROWS\|1`・`CAN_PROCEED\|1`・`PRECHECK_DONE` |
| dryrun | 2026-11-10 20:37:54 JST・rc=0・`UPDATED\|1`・`CHECK_OK 1`・`ROLLBACK`・`DRYRUN_OK` |
| 実施日時・commit | 2026-11-10 20:37:55 JST・rc=0・`UPDATED\|1`・`CHECK_OK 1`・`COMMIT`・`COMMIT_DONE`。実行は PO の `!`（manual-only の鍵・SQL は origin/main 1ac5ce51e の本ファイル群を git show で読んだもの） |
| verify | 2026-11-10 20:37:56 JST・rc=0・`KW_NEW\|1`・`OTHERS_SAME\|1`・`ONLY_CN0003\|1`・`VERIFY_DONE`。生の出力は PO の Mac の `~/CC報告ファイル-keep/shime-bin2/` |

---

# 便4: 規則12h の設定を入れる（切り替え・1 回だけのデータ変更）

ADR-1007・ADR-1073。設計: docs/handoff/shime-box-all-states/design.md §3-4（PO 2026-11-11「1」）。

## 値

- 入れる先: `public.tcg_distribution_settings`（key が主キー）の key `v102_shime_box_all_states`。
- 値: `{"keep_words": ["まだあります"]}`（便3・便3.5 のやり直しで差し込んだ値と一字一句同じ）。
- 解析は投稿を読むたびにこの表を読む（`backend/app/services/gemini_raw_copy_v102_product_first.py` の `_load_shime_box_all_states`）。入れた後に届いた投稿から働く。

## 手順（上から順に。1 つでも期待と違えばそこで止まる）

1. `switch-precheck.sql`（読み取り）: `TABLE|tcg_distribution_settings`・`CAN_PROCEED|1`・`BOX|5`・`PRECHECK_DONE`。
2. `switch-dryrun.sql`: 入れて検査し、必ず ROLLBACK。`INSERTED|1`・`CHECK_OK 1`・`DRYRUN_OK`。
3. `switch-commit.sql`: 2 の成功の後だけ。`INSERTED|1`・`CHECK_OK 1`・`COMMIT_DONE`。
4. `switch-verify.sql`（読み取り）: `MATCH|1`・`ROWS|1`・`VERIFY_DONE`。

実行は本番の書き込みの鍵が要る。AI の自動判定では止まるため、PO が `!` で流す。

## 戻し方

`switch-rollback.sql`（行を 1 行消す。件数が 1 でなければ失敗）。`DELETED|1`・`ROLLBACK_DONE`。戻した後は `switch-verify.sql` の `MATCH|0`・`ROWS|0`。それまでに規則12h で閉じた在庫は戻らない恐れがある（未確認・design.md §6）。

## 記録欄（Opus が実施後に記入）

| 項目 | 内容 |
|---|---|
| precheck | 2026-11-11 13:12:23 JST・rc=0・`TABLE\|tcg_distribution_settings`・`CAN_PROCEED\|1`・`BOX\|5`・`PRECHECK_DONE` |
| dryrun | 2026-11-11 13:12:24 JST・rc=0・`INSERTED\|1`・`CHECK_OK 1`・`ROLLBACK`・`DRYRUN_OK` |
| 実施日時・commit | 2026-11-11 13:12:24 JST・rc=0・`INSERTED\|1`・`CHECK_OK 1`・`COMMIT`・`COMMIT_DONE`。実行は PO の `!`（manual-only の鍵・SQL は origin/main の本ファイル群を git show で読んだもの。流した写しと本ファイルが同じことを cmp で確認） |
| verify | 2026-11-11 13:12:25 JST・rc=0・`MATCH\|1`・`ROWS\|1`・`VERIFY_DONE`。生の出力は PO の Mac の `~/CC報告ファイル-keep/shime-bin4/`。この時刻から新しく届く投稿の解析に規則12h が働く |
