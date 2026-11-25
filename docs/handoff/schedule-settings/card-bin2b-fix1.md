# 実装カード schedule-settings 便2b 直し1 — 「チームの表が無い部屋は飛ばす」の試験を表の写しなしで書く

> この文書は何か：PR #5763 の CI「test-schema-dup gate」の赤を直す作業指示書です。

- 元のカード: `docs/handoff/schedule-settings/card-bin2b.md`。設計: `docs/handoff/schedule-settings/design-bin2b.md` §5（`teams` が無い部屋は飛ばす、を確かめる）。設計の範囲は変えない
- 担当: 実装 Sonnet（クラウド）は push まで。PR・審査・マージは Opus
- 枝: `release/schedule-settings-bin2b`。`bash scripts/new-worktree.sh release/schedule-settings-bin2b` で場所を作り、`git switch -C release/schedule-settings-bin2b origin/release/schedule-settings-bin2b`。clone のまま commit しない
- 触るファイル（これ以外は触らない）: `backend/tests/test_calendar_team_share.py`

## 事実（CI の原文）

- CI「test-schema-dup gate」（`scripts/check_test_schema_dup.py`）の出力: `backend/tests/test_calendar_team_share.py (0 -> 2)`。exit 1
- 原因: `backend/tests/test_calendar_team_share.py` の `test_migration_skips_rooms_without_teams_table` が、空の部屋 `tenant_98200` に `CREATE TABLE ... calendar_events` と `CREATE TABLE ... calendar_categories` を書いている。試験に表の定義を新しく足すことは、この点検で禁止されている（例外の印は無い）

## 変更1 試験の書き直し

`test_migration_skips_rooms_without_teams_table` を次の形に置き換える。ファイルの中のどこにも `CREATE TABLE` の文字を書かない（文字列の組み立てで点検をすり抜ける書き方もしない）。

1. `_env()` が用意した試験の部屋 `_SCHEMA` をそのまま使う。新しい部屋は作らない
2. `admin` の接続を 1 本開き、取引（transaction）を始める
3. その取引の中で、順に:
   - `DROP TABLE {_SCHEMA}.calendar_event_teams`・`DROP TABLE {_SCHEMA}.calendar_category_teams`
   - `ALTER TABLE {_SCHEMA}.teams RENAME TO teams_hidden_for_skip_test`
   - `_apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)`
   - 同じ接続で `to_regclass` を読み、2 つの表がどちらも NULL（作られていない）ことを確かめる
4. 最後に必ず取引を取り消す（`rollback`）。`try/finally` で、確かめが外れても取り消す
5. 取り消したあと、別の接続で `{_SCHEMA}.teams`・`calendar_event_teams`・`calendar_category_teams` がどれも在ることを確かめる（ほかの試験を壊していない証拠）

試験の名前は変えない。

## 確かめ

- `python3 scripts/check_test_schema_dup.py` を `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=HEAD` を付けて流し、`test_calendar_team_share.py` が `BASE=0 HEAD=0` で exit 0 になること。出力は生のままファイルに残す
- PostgreSQL 16 を手元に立てられれば `cd backend && python -m pytest tests/test_calendar_team_share.py -q` を流して生の出力を残す。立てられなければ「CI で確かめる」と書く
- `git grep -n "CREATE TABLE" backend/tests/test_calendar_team_share.py` が 0 件
- 提出前: `bash scripts/dev/check-before-submit.sh`
- commit（`--no-verify` は使わない）→ `git log -1 --oneline` → `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin2b -1 --oneline`

## 停止する条件（BLOCKED: で返す）

- 上の形で書けない（取引の中で表の名前を変えられない、など）
- 触るファイル以外を変える必要が出た
- この試験以外の試験が落ちた

## 報告

- 冒頭に「本報告はカード schedule-settings 便2b 直し1 の実行結果である」。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: 点検と試験の生の出力のファイルの場所と末尾・push した commit

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える
- 本文や Bash の文字に SQL の消す語を直接書くと見張りに止められる。ファイルの変更は Edit/Write で行う

END OF CARD
