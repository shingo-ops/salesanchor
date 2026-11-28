# 実装カード schedule-settings 便3a 直し2 — 古い試験の期待と基準の数を新しい動きに合わせる

> この文書は何か：PR #5771 の CI「pytest-run-internal」で落ちた 2 件の直しの指示書です。

- 設計: `docs/handoff/schedule-settings/design-bin3a.md`（A6「使っていないチームは team_ids に出さない」は承認済み。範囲は変えない）
- 枝: `release/schedule-settings-bin3`。`bash scripts/new-worktree.sh release/schedule-settings-bin3` で場所を作り、`git switch -C release/schedule-settings-bin3 origin/release/schedule-settings-bin3`（d232cac9f の次に Opus のこのカードの commit がある）。clone のまま commit しない。`git rev-list --count HEAD..origin/main` が 0 でなければ `BLOCKED: main が先に進んだ` で返す
- 触るファイル（これだけ）: `backend/tests/test_calendar_team_share.py`・`backend/tests/error_detail_baseline.json`

## 事実（Opus が CI の記録で確かめた）

CI の結果: 2 failed, 10181 passed, 79 skipped。

1. `tests/test_calendar_team_share.py::test_b1_visibility_for_five_people_in_list_and_search`
   - `:309` の期待が `"試験B": [t["t3"]]`。今は `"試験B": []` が返る
   - 試験B は使っていないチーム t3 の予定（`:279-281` で作ってから t3 を止める）。便3a の A6 で、使っていないチームは予定一覧の `team_ids` に出さなくなった。試験の期待が古い動き
   - 設計がこの試験の書き直しを入れ忘れていた（Opus の設計漏れ）
2. `tests/test_error_detail_guard.py::test_detail_guard_no_stale_baseline`
   - 「減った: app/routers/calendar.py 基準 13 → 今 12（backend/tests/error_detail_baseline.json のこの行を 12 に下げる。0 なら行を消す）」
   - `backend/tests/error_detail_baseline.json:13` が `"app/routers/calendar.py": 13`

## 変更

### 変更1 `backend/tests/test_calendar_team_share.py:309` の 1 行だけ

変更前:
```python
        assert by_title == {"試験A": [t["t1"]], "試験B": [t["t3"]], "試験P": [], "試験S": []}
```

変更後:
```python
        # 使っていないチーム t3 は team_ids に出さない（schedule-settings 便3a A6）。紐づけの行は残る（:285）
        assert by_title == {"試験A": [t["t1"]], "試験B": [], "試験P": [], "試験S": []}
```

`:285` の `_team_ids_of`（表を直接読む）は変えない。見え方の期待（`:287-298`）も変えない。

### 変更2 `backend/tests/error_detail_baseline.json:13` の数だけ

変更前: `  "app/routers/calendar.py": 13,`
変更後: `  "app/routers/calendar.py": 12,`

ほかの行は触らない。

## 確かめ

- `cd backend && python -m pytest tests/test_error_detail_guard.py -q` の生の出力（手元に依存が無ければ、`pip install -r requirements.txt` を試し、だめなら「CI で確かめる」と書く）
- `tests/test_calendar_team_share.py` は本物の PostgreSQL が要る。手元で流せなければ「CI で確かめる」と書く
- `git diff --stat` が 2 ファイル・各 1〜2 行であること
- 提出前: `bash scripts/dev/check-before-submit.sh`
- commit（`--no-verify` は使わない）→ `git log -1 --oneline` → `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin3 -1 --oneline`

## 停止する条件（BLOCKED: で返す）

- 上の 2 か所以外を変える必要が出た
- 実物の行が上の「変更前」と違う
- main が先に進んでいた

## 報告

- 冒頭に「本報告はカード schedule-settings 便3a 直し2 の実行結果である」。1 行目は DONE: <sha>／BLOCKED: 理由 のどちらか
- 試験の生の出力の末尾・`git diff --stat`・push した commit

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

END OF CARD
