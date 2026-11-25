# 実装カード 便2a 直し2（CI の赤 4 件）

- 元のカード: docs/handoff/schedule-settings/card-bin2a.md（委任の定型・報告の形・停止条件はそのまま効く）
- ブランチ: release/schedule-settings-bin2a（PR #5759。head ddb29a7ef の上に積む）
- 発行: Opus（設計統括）2026-11-25。PO の委任（「1,このセッションでは…PRマージ、デプロイまで完走させてくれ。」）の範囲内の直し

## なぜ

head ddb29a7ef の CI で 4 件が赤。Opus が CI の記録と実物で原因を確かめた。

- pytest 3 件（全体 10129 通過・3 失敗）:
  - `tests/test_realtime_topics.py::test_every_write_route_is_in_exactly_one_table`: 「どちらの表にも無い書き込みルート: [('PATCH', '/api/v1/calendar/categories/{key}'), ('POST', '/api/v1/calendar/categories')]」
  - `tests/test_api_error_reason_sync.py::test_not_found_table_rows_are_read`: 「assert 67 == 66」
  - `tests/test_error_detail_guard.py::test_detail_guard_no_increase`: 「増えた: app/routers/calendar.py 基準 13 → 今 15」
- guard-authoring/evaluation: state error。`scripts/run-guard-evaluation.js:24-25` の `git merge-base --is-ancestor base head` が通らない。枝が main より 16 件遅れているため（main の今の先頭が枝に入っていない）。

## 触るファイル（この 4 つと main の取り込みだけ）

1. `backend/app/routers/calendar.py`
2. `backend/app/realtime/topics.py`
3. `backend/tests/test_api_error_reason_sync.py`
4. `backend/tests/test_calendar_categories.py`

## 直し

### 直し0 main を取り込む（先に行う）

- `git fetch origin main` → `git merge --no-ff --no-edit origin/main`。このカードに限り merge を許す。
- Opus が手元で `git merge-tree --write-tree --name-only` を流し、ぶつかりは 0 件だった。ぶつかりが出たら直さずに BLOCKED:（ぶつかったファイル名を書く）。
- main 側の変更には `backend/app/services/calendar_service.py` と `backend/tests/test_calendar_sync_tenant_reset_pg.py` が入る。取り込んだ後に下の「確かめ」の試験で両方を流す。

### 直し1 管理者だけの確かめを共通の部品に寄せる（文の直書きを消す）

- 事実: `backend/app/routers/calendar.py:246-247` と `:260-261` が「この操作は管理者のみ実行できます」を直書きしている。同じ確かめと同じ文が共通の部品 `backend/app/auth/dependencies.py:581-595` の `require_tenant_admin` にある。同じファイルの `PATCH /calendar/sync-mode`（`calendar.py:782` 付近）は既にこの部品を `Depends` で使っている。
- 直し:
  - `create_calendar_category` と `update_calendar_category` の引数 `user: User = Depends(get_current_user)` を `user: User = Depends(require_tenant_admin)` に変える。
  - 両方の関数の中の `if not is_tenant_admin(...): raise HTTPException(...)` の 2 行を消す。
  - `is_tenant_admin` と `get_user_system_keys` の import は消さない（`:633` と `:738` 付近で使っている）。
- 変更後に `calendar.py` の数え方の件数が基準どおり 13 になる。`backend/tests/error_detail_baseline.json` は触らない。

### 直し2 新しい書き込みルート 2 本を表に載せる

- 直し: `backend/app/realtime/topics.py` の `NO_SIGNAL_ROUTES` で、`("POST", "/api/v1/calendar/events"): _PENDING,` の行のすぐ上に次の 2 行を足す（並びは道すじ順）。

```
    ("POST", "/api/v1/calendar/categories"): _PENDING,
    ("PATCH", "/api/v1/calendar/categories/{key}"): _PENDING,
```

- 他の行は触らない。`WRITE_ROUTE_TOPICS` には足さない。

### 直し3 件数の試験を 67 にする

- `backend/tests/test_api_error_reason_sync.py:81-82` の `66` を `67` にする（2 か所）。他は触らない。

### 直し4 403 の試験を共通の部品の形に合わせる

- 事実: `backend/tests/test_calendar_categories.py:294-299` は受け口の関数を直接呼んで 403 を確かめている。直し1の後は、確かめが `Depends` に移るため、直接呼ぶと 403 にならない。
- 直し: `:294-299` の 2 つの `expect(403, ...)` を、次の 2 つの確かめに置き換える。
  - (a) 受け口の配線: `app.routers.calendar.router.routes` から道すじ `/calendar/categories`（POST）と `/calendar/categories/{key}`（PATCH）を探し、それぞれの `route.dependant.dependencies` の `call` に `require_tenant_admin` が入っていることを assert する。
  - (b) 部品の文: `patch("app.auth.dependencies.get_user_system_keys", return_value=set())` の中で `require_tenant_admin(tenant_id=_TENANT, user=_user(_STAFF_USER), db=db)` を呼び、`expect(403, "この操作は管理者のみ実行できます", ...)` で確かめる。
- 他の試験は触らない。

## 確かめ（生の出力を /tmp の下のファイルに残す）

- `git merge-base --is-ancestor origin/main HEAD` の終了コードが 0。
- `cd backend && python -m pytest tests/test_realtime_topics.py tests/test_api_error_reason_sync.py tests/test_error_detail_guard.py tests/test_calendar_categories.py tests/test_calendar_service.py -q` が全部通る。
- 手元の PostgreSQL 16 があれば `tests/test_calendar_sync_tenant_reset_pg.py` も流す。流せなければ「CI で確かめる」と書く。
- `git diff origin/main...HEAD -- backend/tests/error_detail_baseline.json` が空。
- `grep -n "管理者のみ" backend/app/routers/calendar.py` が 0 件。
- 提出前: `bash scripts/dev/check-before-submit.sh`。
- commit（`--no-verify` は使わない）→ `git push -u origin HEAD` → `git log origin/release/schedule-settings-bin2a -1 --oneline`。

## 停止する条件（BLOCKED: で返す）

- main の取り込みでぶつかりが出た。
- 上の 4 つ以外を変える必要が出た。
- 上の試験が、この直しと関係なく落ちる（落ちた試験の名前と原文を書く）。

END OF CARD
