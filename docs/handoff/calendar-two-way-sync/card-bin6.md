# 実装カード 便6: 取り込みの「消した数」を、実際に消した分だけにする

- 設計: docs/handoff/calendar-two-way-sync/design.md §14（正）。
- 状態: PO 承認待ち（承認が出るまで実装しない）。
- 枝: release/calendar-import-deleted-count（origin/main 起点。`bash scripts/new-worktree.sh release/calendar-import-deleted-count --claude` で作る。クラウドでは clone のまま commit しない）。
- 触るファイルは 3 本だけ: `backend/app/services/calendar_service.py`・`backend/tests/test_calendar_service.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`。ほかは触らない（migration・画面・文言・ADR・google_webhook.py も触らない）。

## 0. 着手前の実物点検（違ったら止めて BLOCKED: で返す）

1. `backend/app/services/calendar_service.py` に、§1 の「変更前」の 10 行が 1 字も違わずに 1 か所だけあること。
2. `backend/tests/test_calendar_service.py` に `async def test_deletes_cancelled_event_only_google_rows(self):` が 1 つだけあり、その中に `delete_result = MagicMock()` があること。
3. `backend/tests/test_calendar_sync_tenant_reset_pg.py` に `async def test_google_series_cancel_deletes_master_and_exceptions_on_real_db():` があり、その中に §3 の「変更前」の 2 行があること。

## 1. `backend/app/services/calendar_service.py`

変更前:

```python
    # 削除済みイベントの処理
    if google_event.get("status") == "cancelled":
        await db.execute(
            text(
                "DELETE FROM calendar_events WHERE google_event_id = :gid"
                " AND source = 'google'"
            ),
            {"gid": google_event_id},
        )
        return "deleted"
```

変更後:

```python
    # 削除済みイベントの処理。消す行が無ければ数えない（繰り返しを消した後の残りの回など・便6 2026-11-27）
    if google_event.get("status") == "cancelled":
        res = await db.execute(
            text(
                "DELETE FROM calendar_events WHERE google_event_id = :gid"
                " AND source = 'google'"
            ),
            {"gid": google_event_id},
        )
        return "deleted" if (res.rowcount or 0) > 0 else "skipped"
```

## 2. `backend/tests/test_calendar_service.py`

### 2-1. `test_deletes_cancelled_event_only_google_rows` の中

変更前:

```python
        delete_result = MagicMock()
```

変更後:

```python
        delete_result = MagicMock()
        delete_result.rowcount = 1
```

### 2-2. その試験のすぐ後（同じクラスの中）に足す

```python
    @pytest.mark.asyncio
    async def test_cancelled_event_without_row_is_not_counted(self):
        """消す行が無い消した知らせは "skipped"（取り込みの消した数に足さない・便6）。"""
        from app.services.calendar_service import upsert_from_google

        db = AsyncMock()
        db.commit = AsyncMock()
        origin_result = MagicMock()
        origin_result.first = MagicMock(return_value=None)  # not app origin
        delete_result = MagicMock()
        delete_result.rowcount = 0
        db.execute = AsyncMock(side_effect=[origin_result, delete_result])

        out = await upsert_from_google(
            db, tenant_id=1, google_event={"id": "ev_gone", "status": "cancelled"}, owner_user_id=9
        )
        assert out == "skipped"
        sql = db.execute.call_args_list[1].args[0].text
        assert "source = 'google'" in sql
        db.commit.assert_not_called()
```

## 3. `backend/tests/test_calendar_sync_tenant_reset_pg.py`

`test_google_series_cancel_deletes_master_and_exceptions_on_real_db` の中。

変更前:

```python
        assert await _count_rows(admin_engine, "id = :id", {"id": master["id"]}) == 0
        assert await _count_rows(admin_engine, "recurring_event_id = :id", {"id": master["id"]}) == 0
```

変更後（2 行の後に足す。元の行を消した後に届く残りの回は数えない）:

```python
        assert await _count_rows(admin_engine, "id = :id", {"id": master["id"]}) == 0
        assert await _count_rows(admin_engine, "recurring_event_id = :id", {"id": master["id"]}) == 0
        later = {
            "id": "gm978_20261224T010000Z", "status": "cancelled", "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-24T10:00:00+09:00"},
        }
        assert await _import_one(factory, later, g_gone) == "skipped"
```

## 4. 確かめ（Mac で試験は回さない。CI に任せる）

- `python -m py_compile backend/app/services/calendar_service.py backend/tests/test_calendar_service.py backend/tests/test_calendar_sync_tenant_reset_pg.py` が通ること。
- `git diff --name-only origin/main...HEAD` が、上の 3 本と docs だけであること。

## 5. 想定の分岐（起きたら止めて BLOCKED: で返す。推測で直さない）

- §0 の点検で 1 字でも違う。
- `_import_one` が `g_gone` を 3 つ目の引数として受けない形だった。
- CI で、この 3 本以外の予定の試験が落ちた。

## 6. commit と push

- commit の文: `fix(calendar): count Google import deletions only when a row was deleted`。
- push は `git -C <作業場所の絶対パス> push -u origin release/calendar-import-deleted-count` の 1 行だけで行う。
- PR は作らない（Opus が作る）。終わったら DONE と commit の id を返す。
