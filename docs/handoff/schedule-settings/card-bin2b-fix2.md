# 実装カード schedule-settings 便2b 直し2 — 失敗の文の数の見張りと、理由コードの数の試験

> この文書は何か：PR #5763（先頭 973862523）の CI 赤 2 件を直す作業指示書です。

- 元のカード: `docs/handoff/schedule-settings/card-bin2b.md`。設計: `docs/handoff/schedule-settings/design-bin2b.md` §4（直すで `team_ids` だけ送ったときも、持ち主でなければ 403・見せ方を変えるのと同じ文）。設計の範囲・振る舞いは変えない
- 担当: 実装 Sonnet（クラウド）は push まで。PR・審査・マージは Opus
- 枝: `release/schedule-settings-bin2b`。`bash scripts/new-worktree.sh release/schedule-settings-bin2b` で場所を作り、`git switch -C release/schedule-settings-bin2b origin/release/schedule-settings-bin2b`。clone のまま commit しない
- 触るファイル（これ以外は触らない）: `backend/app/routers/calendar.py`・`frontend/src/lib/apiErrorReason.test.ts`

## 事実（CI の原文・973862523）

- `pytest-run-internal`: `FAILED tests/test_error_detail_guard.py::test_detail_guard_no_increase - AssertionError: 増えた: app/routers/calendar.py 基準 13 → 今 14`。`1 failed, 10148 passed`
  - 原因: `backend/app/routers/calendar.py` の予定を直す受け口で、`elif "team_ids" in payload and event_owner != user.id:` の下に、文を直書きした `HTTPException`（`detail="見せ方を変えられるのは予定の持ち主だけです"`）を 1 つ新しく足した。同じ文の 403 はすぐ上の `if "calendar_type" in payload:` の中に元からある
- `Frontend unit tests（内部）`: `src/lib/apiErrorReason.test.ts > backend sync > every table code is used in backend/app` が `expected 28 to be 27`
  - 原因: この PR が `frontend/src/lib/apiErrorReason.ts` の表に `invalid_team_ids` を足して 28 件になったが、試験の件数 `toBe(27)`（`frontend/src/lib/apiErrorReason.test.ts:76`）を直していない

## 変更1 `backend/app/routers/calendar.py` の 403 を 1 つにまとめる（文の数を 13 に戻す）

今の形（予定を直す受け口）:

```python
    if "calendar_type" in payload:
        if payload["calendar_type"] not in cal_svc.SHARE_VALUES:
            raise HTTPException(... 422 ... detail="calendar_type は 'shared'・'personal'・'team' のどれかを指定してください")
        if event_owner != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="見せ方を変えられるのは予定の持ち主だけです")
        if payload["calendar_type"] == "personal":
            payload["user_id"] = user.id
    elif "team_ids" in payload and event_owner != user.id:
        # team_ids だけを送った直しも、見せ方を変えるのと同じ（持ち主だけ）
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="見せ方を変えられるのは予定の持ち主だけです")
```

直したあとの形（判定の順番・状態コード・文は同じ。`HTTPException` の数だけ 1 つ減る）:

```python
    if "calendar_type" in payload and payload["calendar_type"] not in cal_svc.SHARE_VALUES:
        raise HTTPException(... 422 ... 今と同じ detail ...)
    # 見せ方（calendar_type）とチーム（team_ids）を変えられるのは持ち主だけ。team_ids だけを送った直しも同じ
    if ("calendar_type" in payload or "team_ids" in payload) and event_owner != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="見せ方を変えられるのは予定の持ち主だけです")
    if payload.get("calendar_type") == "personal":
        payload["user_id"] = user.id
```

- 422 の文・403 の文は 1 文字も変えない（画面と試験が文を見ている）
- `error-detail-exempt` の印は使わない。`backend/tests/error_detail_baseline.json` は変えない
- この 3 つの判定より前・後のコードは変えない

## 変更2 `frontend/src/lib/apiErrorReason.test.ts:76`

- `expect(Object.keys(API_ERROR_REASON_KEYS).length).toBe(27);` の `27` を `28` にする。ほかは変えない

## 確かめ（出力は生のまま /tmp の下のファイルに残す）

- `cd backend && python3 -m pytest tests/test_error_detail_guard.py -q`（DB を使わない）が通ること
- `cd backend && python3 -m pytest tests/test_api_error_reason_sync.py -q` が通ること
- PostgreSQL 16 を立てられれば `tests/test_calendar_team_share.py tests/test_calendar_owner_api.py` を流す。立てられなければ「CI で確かめる」と書く（psql でファイルを流す・権限を足す操作はしない）
- `cd frontend && npx vitest run src/lib/apiErrorReason.test.ts`（node_modules が無ければ `npm ci` の後）が通ること。入れられなければ「CI で確かめる」と書く
- 提出前: `bash scripts/dev/check-before-submit.sh`
- commit（`--no-verify` は使わない）→ `git log -1 --oneline` → `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin2b -1 --oneline`

## 停止する条件（BLOCKED: で返す）

- 上の形で書けない・判定の順番を変えないとまとめられない
- 触るファイル以外を変える必要が出た
- 上の試験が落ちた

## 報告

- 冒頭に「本報告はカード schedule-settings 便2b 直し2 の実行結果である」。1 行目は DONE: <sha>／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: 各確かめの生の出力のファイルの場所と末尾 3 行・push した commit

## 委任の定型

- sleep は使わない。CI は待たない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える
- 本文や Bash の文字に SQL の消す語を直接書くと見張りに止められる。ファイルの変更は Edit/Write で行う

END OF CARD
