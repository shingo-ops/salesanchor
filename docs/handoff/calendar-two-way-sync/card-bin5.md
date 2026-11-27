# 実装カード 便5: Google で繰り返しの「すべての予定」を消したら、アプリからも消す

- 設計: docs/handoff/calendar-two-way-sync/design.md §13（正）。ADR-1075 改訂 2026-11-27。
- 状態: PO 承認済み（2026-11-27「1」: この設計のまま作る）。実装してよい。
- 枝: release/calendar-google-series-delete（origin/main 起点。`bash scripts/new-worktree.sh release/calendar-google-series-delete --claude` で作られた場所で作業する。新しく作らない）。
- 触るファイルは 3 本だけ: `backend/app/services/calendar_service.py`・`backend/tests/test_calendar_service.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`。ほかは触らない（migration・画面・文言・ADR・google_webhook.py も触らない）。

## 0. 着手前の実物点検（違ったら止めて BLOCKED: で返す）

1. `backend/app/services/calendar_service.py` の `async def _apply_app_instance_from_google(` の中に、§1-2 の「変更前」の 7 行が 1 字も違わずにあること。
2. `_update_app_origin_from_google` の中に、§1-3 の「変更前」の行が 1 字も違わずにあること。
3. `async def _apply_app_instance_from_google(` のすぐ上が空行 2 つであること。
4. `backend/tests/test_calendar_service.py` に `def _inst_db(`・`class TestUpsertRecurringInstance:`・`def test_series_changed_in_google_is_skipped(self):`・`class TestUpdateAppOriginFromGoogle:`・`def test_cancelled_deletes_synced_single_row(self):` が 1 つずつあること。
5. `backend/tests/test_calendar_sync_tenant_reset_pg.py` に `async def _import_one(`・`def _g_master_for(`・`async def test_google_instance_with_taken_id_is_skipped_on_real_db():` があること。

## 1. `backend/app/services/calendar_service.py`

### 1-1. `async def _apply_app_instance_from_google(` のすぐ上（空行 2 つの前）に足す

```python
async def _delete_app_series_from_google(
    db: AsyncSession,
    tenant_id: int,
    master_id: int,
    series_cache: Optional[dict] = None,
) -> str:
    """Google で繰り返しの「すべて」を消したとき、アプリの元の行を消す（ADR-1075 改訂 2026-11-27）。

    - 例外の行に送り中（pending）・送れなかった（failed）の行が 1 つでもあれば消さない（"skipped"）。
      警告は 1 回の取り込みで元 1 つにつき 1 回だけ残す。
    - 消すのは、アプリから送り終えた繰り返しの元の行だけ。例外の行とチームの対応は外部キーで一緒に消える。
    Google へは書かない。commit は呼び元。戻り値は "deleted" | "skipped"。
    """
    cache = series_cache if series_cache is not None else {}
    held = await db.execute(
        text(
            "SELECT id FROM calendar_events"
            " WHERE recurring_event_id = :mid AND sync_status <> 'synced' LIMIT 1"
        ),
        {"mid": master_id},
    )
    if held.first() is not None:
        key = f"held:{master_id}"
        if key not in cache:
            cache[key] = True
            logger.warning(
                "Google で繰り返しを消しましたが、送り中の回があるのでアプリでは消しません (event_id=%s)",
                master_id,
            )
        return "skipped"
    res = await db.execute(
        text(
            "DELETE FROM calendar_events"
            " WHERE id = :id"
            " AND sync_origin_id LIKE 'app:" + str(int(tenant_id)) + ":%'"
            " AND sync_status = 'synced'"
            " AND recurrence_rule IS NOT NULL"
            " AND recurring_event_id IS NULL"
        ),
        {"id": master_id},
    )
    return "deleted" if (res.rowcount or 0) > 0 else "skipped"
```

### 1-2. `_apply_app_instance_from_google` の中

変更前:

```python
    if master_gid not in cache:
        try:
            cache[master_gid] = await gcal.get_event(db, tenant_id, master_gid)
        except Exception as e:
            logger.warning("Google の繰り返しの元の予定を読めませんでした (google_event_id=%s): %s", master_gid, e)
            cache[master_gid] = None
    if not _same_series(master, cache[master_gid]):
```

変更後（`if not _same_series(` の前に 6 行を足す。ほかは 1 字も変えない）:

```python
    if master_gid not in cache:
        try:
            cache[master_gid] = await gcal.get_event(db, tenant_id, master_gid)
        except Exception as e:
            logger.warning("Google の繰り返しの元の予定を読めませんでした (google_event_id=%s): %s", master_gid, e)
            cache[master_gid] = None
    g_master = cache[master_gid]
    # Google で「すべて」を消した: 回も元の予定も消した形で届く（ADR-1075 改訂 2026-11-27）。
    # 読めなかったとき（None）・「これ以降」・「すべて」を直したときは、今のまま下で飛ばす
    if google_event.get("status") == "cancelled" and isinstance(g_master, dict) and g_master.get("status") == "cancelled":
        return await _delete_app_series_from_google(db, tenant_id, master["id"], cache)
    if not _same_series(master, cache[master_gid]):
```

docstring の 2 つ目の「-」の行（「Google の元の予定を 1 回の取り込みに…」）の下に、次の 1 行を足す:

```
    - 回も Google の元の予定も消した形なら「すべて」を消したとみなし、_delete_app_series_from_google で元の行を消す（ADR-1075 改訂 2026-11-27）。
```

### 1-3. `_update_app_origin_from_google` の消した道

変更前:

```python
            {"gid": google_event["id"]},
        )
        return "deleted" if (res.rowcount or 0) > 0 else "skipped"
    if not _has_times(google_event):
```

変更後:

```python
            {"gid": google_event["id"]},
        )
        if (res.rowcount or 0) > 0:
            return "deleted"
        # 元の予定の id で消した形が届いた（繰り返しの「すべて」を消した）。届いた予定そのものが消した形なので、
        # Google には聞き直さない（ADR-1075 改訂 2026-11-27）
        master_row = await db.execute(
            text(
                "SELECT id FROM calendar_events"
                " WHERE google_event_id = :gid"
                " AND sync_origin_id LIKE 'app:" + str(int(tenant_id)) + ":%'"
                " AND sync_status = 'synced'"
                " AND recurrence_rule IS NOT NULL"
                " AND recurring_event_id IS NULL"
            ),
            {"gid": google_event["id"]},
        )
        found_master = master_row.first()
        if found_master is None:
            return "skipped"
        return await _delete_app_series_from_google(db, tenant_id, found_master[0])
    if not _has_times(google_event):
```

docstring の 1 つ目の「-」の行の下に、次の 1 行を足す:

```
    - 単発の行が無く、送り終えた繰り返しの元の行なら、元の行を消す（ADR-1075 改訂 2026-11-27）。
```

## 2. `backend/tests/test_calendar_service.py`

### 2-1. `class TestUpsertRecurringInstance:` の最後に足す

```python
    @staticmethod
    def _held_db(**kw):
        db = _inst_db(**kw)
        db.handlers.insert(0, ("sync_status <> 'synced'", [(9,)]))
        return db

    @pytest.mark.asyncio
    async def test_all_cancelled_in_google_deletes_master(self):
        db = _inst_db()
        out, _ = await self._go(db, _g_inst(status="cancelled"), g_master=_g_master(status="cancelled"))
        assert out == "deleted"
        dels = [(s, p) for s, p in self._writes(db) if s.lstrip().startswith("DELETE")]
        assert len(dels) == 1
        sql, params = dels[0]
        for guard in ("WHERE id = :id", "LIKE 'app:1:%'", "sync_status = 'synced'",
                      "recurrence_rule IS NOT NULL", "recurring_event_id IS NULL"):
            assert guard in sql
        assert params == {"id": 1}
        assert [s for s, _ in self._writes(db) if not s.lstrip().startswith("DELETE")] == []

    @pytest.mark.asyncio
    async def test_all_cancelled_with_pending_exception_is_held_and_warned_once(self, caplog):
        cache: dict = {}
        getter = AsyncMock(return_value=_g_master(status="cancelled"))
        for day in (19, 26):
            db = self._held_db()
            out, _ = await self._go(db, _g_inst(day, status="cancelled"), cache=cache, get_event=getter)
            assert out == "skipped"
            assert self._writes(db) == []
        assert sum("送り中の回があるので" in r.getMessage() for r in caplog.records) == 1

    @pytest.mark.asyncio
    async def test_cancelled_instance_when_master_unreadable_is_skipped(self):
        db = _inst_db()
        out, _ = await self._go(db, _g_inst(status="cancelled"), get_event=AsyncMock(side_effect=RuntimeError("x")))
        assert out == "skipped"
        assert self._writes(db) == []

    @pytest.mark.asyncio
    async def test_following_change_in_google_is_still_skipped(self):
        cut = _g_master(recurrence=["RRULE:FREQ=WEEKLY;BYDAY=TH;UNTIL=20261125T145959Z"])
        db = _inst_db()
        out, _ = await self._go(db, _g_inst(status="cancelled"), g_master=cut)
        assert out == "skipped"
        assert self._writes(db) == []
```

### 2-2. `class TestUpdateAppOriginFromGoogle:` の最後に足す

```python
    @pytest.mark.asyncio
    async def test_cancelled_master_id_deletes_app_series(self):
        db = _FakeDB(
            [
                ("SELECT 1 FROM calendar_events", [(1,)]),
                ("SELECT id FROM calendar_events WHERE google_event_id", [(1,)]),
            ],
            sync_mode=None,
        )
        rowcounts = iter([0, 1])
        orig_exec = db.execute

        async def _exec(stmt, params=None):
            r = await orig_exec(stmt, params)
            sql = stmt.text if hasattr(stmt, "text") else str(stmt)
            if sql.lstrip().startswith("DELETE"):
                r.rowcount = next(rowcounts)
            return r

        db.execute = _exec
        assert await self._go(db, {"id": "gm", "status": "cancelled"}) == "deleted"
        dels = db.find("DELETE FROM calendar_events")
        assert len(dels) == 2
        assert "recurrence_rule IS NULL" in dels[0][1]
        assert "WHERE id = :id" in dels[1][1] and dels[1][2] == {"id": 1}
```

### 2-3. 変えない試験

- `test_series_changed_in_google_is_skipped`（元の予定は消した形・回は消していない形）: 期待は "skipped" のまま。直さない。
- `test_cancelled_deletes_synced_single_row` の `db0`（0 行）: 新しい道で元の行を探す。偽の接続が MagicMock を返すので、送り中の確かめで止まり "skipped" になる。期待は変わらない。直さない。この試験が落ちたら止めて BLOCKED: で返す。

## 3. `backend/tests/test_calendar_sync_tenant_reset_pg.py` の最後に足す

```python
# Google で繰り返しの「すべて」を消したら、元の行と例外の行が DB の決まりに外れずに消える（ADR-1075 改訂 2026-11-27）
async def test_google_series_cancel_deletes_master_and_exceptions_on_real_db():
    admin_engine, app_engine, factory = await _setup()
    try:
        master = await _create_weekly_master(factory)
        await _mark_synced_from_app(admin_engine, master["id"], "gm978")
        edited = {
            "id": "gm978_20261217T010000Z", "status": "confirmed", "summary": "臨時",
            "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-17T10:00:00+09:00"},
            "start": {"dateTime": "2026-12-17T10:00:00+09:00"},
            "end": {"dateTime": "2026-12-17T11:00:00+09:00"},
        }
        assert await _import_one(factory, edited, _g_master_for(master)) == "upserted"
        g_gone = dict(_g_master_for(master), status="cancelled")
        cancelled = {
            "id": "gm978_20261210T010000Z", "status": "cancelled", "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-10T10:00:00+09:00"},
        }
        assert await _import_one(factory, cancelled, g_gone) == "deleted"
        assert await _count_rows(admin_engine, "id = :id", {"id": master["id"]}) == 0
        assert await _count_rows(admin_engine, "recurring_event_id = :id", {"id": master["id"]}) == 0
    finally:
        await _teardown(admin_engine, app_engine)


# 送り中の例外の行があるときは、Google で「すべて」を消しても 1 行も消さない
async def test_google_series_cancel_with_pending_exception_keeps_rows_on_real_db():
    from sqlalchemy import text

    admin_engine, app_engine, factory = await _setup()
    try:
        master = await _create_weekly_master(factory)
        await _mark_synced_from_app(admin_engine, master["id"], "gm978")
        edited = {
            "id": "gm978_20261217T010000Z", "status": "confirmed", "summary": "臨時",
            "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-17T10:00:00+09:00"},
            "start": {"dateTime": "2026-12-17T10:00:00+09:00"},
            "end": {"dateTime": "2026-12-17T11:00:00+09:00"},
        }
        assert await _import_one(factory, edited, _g_master_for(master)) == "upserted"
        async with admin_engine.begin() as conn:
            await conn.execute(
                text(f"UPDATE {_SCHEMA}.calendar_events SET sync_status = 'pending' WHERE recurring_event_id = :id"),
                {"id": master["id"]},
            )
        cancelled = {
            "id": "gm978_20261210T010000Z", "status": "cancelled", "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-10T10:00:00+09:00"},
        }
        g_gone = dict(_g_master_for(master), status="cancelled")
        assert await _import_one(factory, cancelled, g_gone) == "skipped"
        assert await _count_rows(admin_engine, "id = :id", {"id": master["id"]}) == 1
        assert await _count_rows(admin_engine, "recurring_event_id = :id", {"id": master["id"]}) == 1
    finally:
        await _teardown(admin_engine, app_engine)
```

## 4. 確かめ（Mac で試験は回さない。CI に任せる）

- `python -m py_compile backend/app/services/calendar_service.py backend/tests/test_calendar_service.py backend/tests/test_calendar_sync_tenant_reset_pg.py` が通ること。
- `git diff --name-only origin/main...HEAD` が、上の 3 本と docs だけであること。

## 5. 想定の分岐（起きたら止めて BLOCKED: で返す。推測で直さない）

- CI で `test_cancelled_deletes_synced_single_row` か `test_series_changed_in_google_is_skipped` が落ちた。
- 本物の PostgreSQL の試験で、外部キーや決まりの失敗（IntegrityError・ForeignKeyViolation）が出た。
- `_inst_db` の偽の接続の中身が §0 と違い、2-1 の `_held_db` がそのまま使えない。

## 6. commit と push

- commit の文: `feat(calendar): delete app series when the whole series is deleted in Google (ADR-1075 rev 2026-11-27)`。
- push は `git -C <作業場所の絶対パス> push -u origin release/calendar-google-series-delete` の 1 行だけで行う。
- PR は作らない（Opus が作る）。終わったら DONE と commit の id を返す。
