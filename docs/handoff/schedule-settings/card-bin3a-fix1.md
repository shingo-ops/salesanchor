# 実装カード schedule-settings 便3a 直し1 — 試験の検索文字が「表の写し」に数えられる

> この文書は何か：PR #5771 の CI「test-schema-dup gate」が赤になった件の直しの指示書です。

- 設計: `docs/handoff/schedule-settings/design-bin3a.md`（範囲は変えない）
- 枝: `release/schedule-settings-bin3`。`bash scripts/new-worktree.sh release/schedule-settings-bin3` で場所を作り、`git switch -C release/schedule-settings-bin3 origin/release/schedule-settings-bin3`。clone のまま commit しない。`git rev-list --count HEAD..origin/main` が 0 でなければ `BLOCKED: main が先に進んだ` で返す
- 触るファイル（これだけ）: `backend/tests/test_owner_color_key_map.py`

## 事実（Opus が確かめた）

- CI の `python3 scripts/check_test_schema_dup.py` の出力: 「テストに本番テーブル定義の新規コピーが増えています: backend/tests/test_owner_color_key_map.py (0 -> 1)」
- 原因: `backend/tests/test_owner_color_key_map.py:52` の文字 `"CREATE TABLE IF NOT EXISTS {schema}.calendar_owner_settings ("` を、検査（`scripts/check_test_schema_dup.py:28` の `CREATE\s+TABLE`）が表の写しと数える
- `backend/app/services/tenant.py` の中で `{schema}.calendar_owner_settings (` は 1 か所だけ（`:1650`）

## 変更

`backend/tests/test_owner_color_key_map.py:52` だけを次のとおりにする。

変更前:
```python
    start = text.index("CREATE TABLE IF NOT EXISTS {schema}.calendar_owner_settings (")
```

変更後:
```python
    start = text.index("{schema}.calendar_owner_settings (")
```

ほかの行は触らない。

## 確かめ

- `python3 scripts/check_test_schema_dup.py` を、CI と同じく `BASE_SHA=314eeef1ec1992f4349bfe7e9dc504ddaa6b48db HEAD_SHA=$(git rev-parse HEAD)` を付けて流し、生の出力を残す（終了コード 0。`test_owner_color_key_map.py: BASE=0 HEAD=0`）
- `cd backend && python -m pytest tests/test_owner_color_key_map.py -q` の生の出力
- 提出前: `bash scripts/dev/check-before-submit.sh`
- commit（`--no-verify` は使わない）→ `git log -1 --oneline` → `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin3 -1 --oneline`

## 停止する条件（BLOCKED: で返す）

- 上の 1 行を直しても検査が 0 で終わらない
- 試験が落ちる
- main が先に進んでいた

## 報告

- 冒頭に「本報告はカード schedule-settings 便3a 直し1 の実行結果である」。1 行目は DONE／BLOCKED: 理由 のどちらか
- 検査と試験の生の出力の末尾・push した commit

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

END OF CARD
