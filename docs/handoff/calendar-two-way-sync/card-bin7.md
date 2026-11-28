# 実装カード 便7: アプリで消した繰り返しの 1 回を、Google への送りが失敗しても戻さず、あとで送り直す

- 設計: docs/handoff/calendar-two-way-sync/design.md §15（正）。
- 状態: PO 承認済み（2026-11-28「1」: この成功条件のまま作り、本番への反映まで進める）。実装してよい。
- 作業場所: 実装の枝は release/calendar-occurrence-cancel-resend-impl。クラウドでは clone のあと `bash scripts/new-worktree.sh release/calendar-occurrence-cancel-resend-impl` で origin/main から場所を作る。その場所で `git merge --no-edit origin/release/calendar-occurrence-cancel-resend` を流し、設計の commit を取り込んでから作業する（clone のまま commit しない）。
- 触るファイルは 5 本だけ: `backend/app/services/calendar_service.py`・`backend/app/services/google_calendar.py`・`backend/app/services/google_webhook.py`・`backend/tests/test_calendar_service.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`。ほかは触らない（migration・画面・文言・ADR・docs も触らない）。

## 0. 着手前の実物点検（違ったら止めて BLOCKED: で返す）

1. `backend/app/services/calendar_service.py` に、§1-2 の「変更前」が 1 字も違わずに 1 か所だけあること。
2. 同じファイルに `async def _mark_failed(db: AsyncSession, tenant_id: int, row_id: int, clear_ids: bool = False) -> None:` と `async def _google_id_taken(db: AsyncSession, google_event_id: str) -> bool:` が 1 つずつあること。`from datetime import date, datetime, time, timedelta, timezone` があること。
3. `backend/app/services/google_calendar.py` に §2 の「変更前」2 か所があること。
4. `backend/app/services/google_webhook.py` に §3 の「変更前」2 か所があること。
5. `backend/tests/test_calendar_service.py` に `async def test_this_inserts_cancelled_exception(self):`・`async def test_this_existing_exception_marked_cancelled(self):`・`async def test_failures_never_change_sync_status(self):`・`class TestSyncTenantFromGoogle:`・`def _make_sync_db(` が 1 つずつあること。

## 1. `backend/app/services/calendar_service.py`

### 1-1. `_mark_failed` の関数のすぐ後（`async def _exception_google_ids` の前）に足す

```python
def _google_status(e: BaseException) -> Optional[int]:
    """包んだ失敗の元（googleapiclient の HttpError）の HTTP の番号。読めなければ None。"""
    cause = e.__cause__
    return getattr(getattr(cause, "resp", None), "status", None)


async def _send_occurrence_cancel(
    db: AsyncSession,
    tenant_id: int,
    row_id: int,
    row_gid: Optional[str],
    master_gid: str,
    occ: datetime,
    all_day: bool,
    show_deleted: bool = False,
) -> bool:
    """繰り返しの 1 回の取り消しを Google へ送る（便7・design §15）。届いたら送り終えた印、届かなければ送れなかった印。

    Google が「既に消えている」（410）と返したとき・消した形の回が返ったときは届いたとみなす。
    回の Google の id がほかの行に既にあれば、書かずに送れなかった印にする（重なり禁止）。
    """
    from app.services import google_calendar as gcal

    try:
        gid = row_gid
        if not gid:
            instance = await gcal.get_instance(
                db, tenant_id, master_gid, occ, all_day, show_deleted=show_deleted
            )
            gid = instance["id"]
            if await _google_id_taken(db, gid):
                logger.warning("回の Google の id を持つ行が既にあるため印を付けませんでした (event_id=%s)", row_id)
                await _mark_failed(db, tenant_id, row_id)
                return False
            if instance.get("status") == "cancelled":
                await _mark_synced(db, tenant_id, row_id, gid)
                return True
        try:
            await gcal.update_event(db, tenant_id, gid, {"status": "cancelled"})
        except Exception as e:
            if _google_status(e) != 410:
                raise
            logger.info("Google の回は既に消えていました (event_id=%s)", row_id)
        await _mark_synced(db, tenant_id, row_id, None if row_gid else gid)
        return True
    except Exception as e:
        logger.warning("Google の回の取り消しに失敗 (event_id=%s): %s", row_id, e)
        await _mark_failed(db, tenant_id, row_id)
        return False


_RESEND_DAYS = 30
_RESEND_LIMIT = 50


async def resend_cancelled_occurrences(
    db: AsyncSession, tenant_id: int, now: Optional[datetime] = None
) -> int:
    """アプリで消した繰り返しの回のうち、Google へ届いていないものを送り直す（便7・design §15）。届いた数を返す。

    取り込みの鍵（advisory lock 1059）の中で、Google を読む前に呼ぶ。回の始まりが 30 日より前のものは送らない。
    """
    now = now or datetime.now(timezone.utc)
    rows = (
        await db.execute(
            text(
                "SELECT e.id, e.google_event_id, e.original_start_datetime, m.google_event_id, m.is_all_day"
                " FROM calendar_events e JOIN calendar_events m ON m.id = e.recurring_event_id"
                " WHERE e.is_cancelled = true AND e.sync_status IN ('pending', 'failed')"
                " AND m.google_event_id IS NOT NULL AND e.original_start_datetime >= :since"
                " ORDER BY e.original_start_datetime, e.id LIMIT :lim"
            ),
            {"since": now - timedelta(days=_RESEND_DAYS), "lim": _RESEND_LIMIT},
        )
    ).fetchall()
    done = 0
    for row_id, row_gid, orig, master_gid, all_day in rows:
        if await _send_occurrence_cancel(
            db, tenant_id, row_id, row_gid, master_gid, orig, bool(all_day), show_deleted=True
        ):
            done += 1
    return done
```

### 1-2. `delete_recurring_event` の「この予定」の枝

変更前:

```python
    if scope == "this":
        row = event if is_exc else await _find_exception(db, master["id"], occ)
        if row is not None:
            await db.execute(
                text("UPDATE calendar_events SET is_cancelled = true WHERE id = :id"),
                {"id": row["id"]},
            )
            row_id, row_gid = row["id"], row.get("google_event_id")
```

変更後:

```python
    if scope == "this":
        send = await _send_ok(db, tenant_id, master)
        row = event if is_exc else await _find_exception(db, master["id"], occ)
        if row is not None:
            # 送る会社では送り終えるまで送り中にする（取り込みで戻されない・便7）
            pending = ", sync_status = 'pending'" if send else ""
            await db.execute(
                text(f"UPDATE calendar_events SET is_cancelled = true{pending} WHERE id = :id"),
                {"id": row["id"]},
            )
            row_id, row_gid = row["id"], row.get("google_event_id")
```

同じ枝の終わり。変更前:

```python
        await _commit(db, tenant_id)
        if await _send_ok(db, tenant_id, master):
            try:
                gid = row_gid
                found_here = False
                if not gid:
                    instance = await gcal.get_instance(
                        db, tenant_id, master["google_event_id"], occ, m_all_day
                    )
                    gid = instance["id"]
                    found_here = True
                await gcal.update_event(db, tenant_id, gid, {"status": "cancelled"})
                if found_here:
                    await db.execute(
                        text("UPDATE calendar_events SET google_event_id = :gid, sync_origin_id = :oid WHERE id = :id"),
                        {"gid": gid, "oid": _build_sync_origin_id(tenant_id, row_id), "id": row_id},
                    )
                    await _commit(db, tenant_id)
            except Exception as e:
                logger.warning("Google の回の取り消しに失敗 (event_id=%s): %s", row_id, e)
        return
```

変更後:

```python
        await _commit(db, tenant_id)
        if send:
            await _send_occurrence_cancel(
                db, tenant_id, row_id, row_gid, master["google_event_id"], occ, m_all_day
            )
        return
```

- 間の新しい行を作る `else:` の枝（`_insert_row` の呼び出し）は 1 字も変えない。
- 関数の頭の `from app.services import google_calendar as gcal` は、ほかの枝が使うので残す。

## 2. `backend/app/services/google_calendar.py`（`get_instance`）

変更前:

```python
async def get_instance(
    db, tenant_id: int, recurring_event_id: str, original_start: datetime, is_all_day: bool
) -> dict:
```

変更後:

```python
async def get_instance(
    db,
    tenant_id: int,
    recurring_event_id: str,
    original_start: datetime,
    is_all_day: bool,
    show_deleted: bool = False,
) -> dict:
```

docstring の最後の行 `返った回のうち originalStartTime が一致するものを返す。見つからなければ RuntimeError。` の次に 1 行足す:

```
    show_deleted が真のときは消した回も返す（Google の showDeleted・初期値は返さない。便7 の送り直しで使う）。
```

変更前:

```python
    try:
        result = await asyncio.to_thread(
            service.events()
            .instances(
                calendarId=calendar_id,
                eventId=recurring_event_id,
                timeMin=window_start.isoformat(),
                timeMax=window_end.isoformat(),
                maxResults=10,
            )
            .execute
        )
```

変更後:

```python
    kwargs: dict = {
        "calendarId": calendar_id,
        "eventId": recurring_event_id,
        "timeMin": window_start.isoformat(),
        "timeMax": window_end.isoformat(),
        "maxResults": 10,
    }
    if show_deleted:
        kwargs["showDeleted"] = True
    try:
        result = await asyncio.to_thread(service.events().instances(**kwargs).execute)
```

## 3. `backend/app/services/google_webhook.py`（`sync_tenant_from_google`）

変更前:

```python
    from app.services.calendar_service import upsert_from_google
```

変更後:

```python
    from app.services.calendar_service import resend_cancelled_occurrences, upsert_from_google
```

変更前:

```python
        # _get_service は中で commit することがあるので文脈を張り直す
        await set_tenant_context(db, tenant_id)

        sub = (
```

変更後:

```python
        # _get_service は中で commit することがあるので文脈を張り直す
        await set_tenant_context(db, tenant_id)

        # アプリで消した繰り返しの回のうち Google へ届いていないものを、読む前に送り直す（便7・design §15）
        if cfg[1] == "bidirectional":
            try:
                resent = await resend_cancelled_occurrences(db, tenant_id)
                if resent:
                    logger.info("消した回を Google へ送り直しました (tenant=%s, count=%s)", tenant_id, resent)
            except Exception as e:
                logger.warning("消した回の送り直しに失敗 (tenant=%s): %s", tenant_id, e)
                await db.rollback()
            await set_tenant_context(db, tenant_id)

        sub = (
```

## 4. `backend/tests/test_calendar_service.py`

### 4-1. `test_this_inserts_cancelled_exception` の中

変更前:

```python
        ids = db.find("SET google_event_id = :gid, sync_origin_id = :oid WHERE id = :id")[0][2]
        assert ids["gid"] == "ginst" and ids["id"] == 77
```

変更後:

```python
        ids = db.find("SET google_event_id = :gid, sync_origin_id = :oid,")[0][2]
        assert ids["gid"] == "ginst" and ids["id"] == 77
        assert 77 in _statuses(db, "synced")
```

### 4-2. `test_this_existing_exception_marked_cancelled` の最後の `assert g.log == [...]` の行の後に足す

```python
        assert "sync_status = 'pending'" in db.find("UPDATE calendar_events SET is_cancelled")[0][1]
        assert 9 in _statuses(db, "synced") and _statuses(db, "failed") == []
```

### 4-3. `test_failures_never_change_sync_status`

変更前:

```python
        for scope in ("this", "following", "all"):
            db = _master_db(exceptions=["ge1"])
            await self._run(db, _ev(), scope, g=_G(fail=lambda n, a: True))
            assert _statuses(db, "failed") == [] and _statuses(db, "synced") == []
```

変更後:

```python
        for scope in ("following", "all"):
            db = _master_db(exceptions=["ge1"])
            await self._run(db, _ev(), scope, g=_G(fail=lambda n, a: True))
            assert _statuses(db, "failed") == [] and _statuses(db, "synced") == []
        # 「この予定」は送れなかった印を付け、次の取り込みで送り直す（便7・K1）
        db = _master_db(exceptions=["ge1"])
        await self._run(db, _ev(), "this", g=_G(fail=lambda n, a: True))
        assert _statuses(db, "failed") == [77] and _statuses(db, "synced") == []
```

### 4-4. `test_failures_never_change_sync_status` のすぐ後（同じ `TestDeleteRecurring` の中）に足す

```python
    @pytest.mark.asyncio
    async def test_this_without_google_keeps_status(self):
        """送り先の無い元の行では、送らず印も変えない（便7）。"""
        db = _master_db(exc_row=_exc())
        g = await self._run(db, _ev(google_event_id=None), "this")
        assert g.log == []
        assert "sync_status" not in db.find("UPDATE calendar_events SET is_cancelled")[0][1]
        assert _statuses(db, "synced") == [] and _statuses(db, "failed") == []

    @pytest.mark.asyncio
    async def test_this_gone_410_marks_synced(self):
        """Google が「既に消えている」（410）と返したら、届いたとみなす（便7・K3）。"""
        db = _master_db(exc_row=_exc())
        with patch(
            "app.services.google_calendar.update_event", new=AsyncMock(side_effect=_wrapped_http(410))
        ), patch("app.services.calendar_service.reset_tenant_context", new=AsyncMock()):
            from app.services.calendar_service import delete_recurring_event

            await delete_recurring_event(db, 1, _ev(), "this", _jt(2026, 11, 26))
        assert 9 in _statuses(db, "synced") and _statuses(db, "failed") == []
```

### 4-5. `class TestDeleteRecurring:` の行のすぐ前（モジュールの階層）に足す

```python
def _wrapped_http(status: int) -> RuntimeError:
    """google_calendar が包んだ失敗の形（RuntimeError の __cause__ に HTTP の番号）。"""
    from types import SimpleNamespace

    cause = Exception(f"http {status}")
    cause.resp = SimpleNamespace(status=status)
    err = RuntimeError("イベント更新に失敗")
    err.__cause__ = cause
    return err


def _resend_db(rows):
    """送り直しの読み（消した印があり送り終えていない例外の行）に rows を返す偽の接続。"""
    return _FakeDB([("e.is_cancelled = true AND e.sync_status IN", rows)], sync_mode=None)


class TestResendCancelledOccurrences:
    async def _run(self, db, g=None, now=None):
        from app.services.calendar_service import resend_cancelled_occurrences

        g = g or _G()
        with _google(g):
            n = await resend_cancelled_occurrences(db, 1, now=now or _jt(2026, 11, 28))
        return n, g

    @pytest.mark.asyncio
    async def test_reads_30_days_and_50_rows(self):
        db = _resend_db([])
        n, g = await self._run(db, now=_jt(2026, 11, 28))
        assert n == 0 and g.log == []
        params = db.find("e.is_cancelled = true AND e.sync_status IN ('pending', 'failed')")[0][2]
        assert params == {"since": _jt(2026, 10, 29), "lim": 50}

    @pytest.mark.asyncio
    async def test_row_with_id_is_resent_and_synced(self):
        """K2: Google の id を持つ行は取り消しを送り直し、届いたら送り終えた印。"""
        db = _resend_db([(9, "gx", _jt(2026, 11, 26), "gm", False)])
        n, g = await self._run(db)
        assert n == 1
        assert g.log == [("update_event", "gx", {"status": "cancelled"})]
        assert _statuses(db, "synced") == [9]

    @pytest.mark.asyncio
    async def test_row_without_id_finds_instance_with_deleted(self):
        """K2: id の無い行は消した回も返す形で回を引き、送り、id と送り終えた印を書く。"""
        db = _resend_db([(77, None, _jt(2026, 11, 26), "gm", False)])
        getter = AsyncMock(return_value={"id": "ginst", "status": "confirmed"})
        g = _G()
        with _google(g), patch("app.services.google_calendar.get_instance", new=getter):
            from app.services.calendar_service import resend_cancelled_occurrences

            n = await resend_cancelled_occurrences(db, 1, now=_jt(2026, 11, 28))
        assert n == 1
        assert getter.await_args.kwargs == {"show_deleted": True}
        assert g.log == [("update_event", "ginst", {"status": "cancelled"})]
        ids = db.find("SET google_event_id = :gid, sync_origin_id = :oid,")[0][2]
        assert ids["gid"] == "ginst" and ids["id"] == 77

    @pytest.mark.asyncio
    async def test_instance_already_cancelled_stops_resend(self):
        """K3: Google で既に消した回なら送らずに送り終えた印。"""
        db = _resend_db([(77, None, _jt(2026, 11, 26), "gm", False)])
        getter = AsyncMock(return_value={"id": "ginst", "status": "cancelled"})
        g = _G()
        with _google(g), patch("app.services.google_calendar.get_instance", new=getter):
            from app.services.calendar_service import resend_cancelled_occurrences

            n = await resend_cancelled_occurrences(db, 1, now=_jt(2026, 11, 28))
        assert n == 1 and g.log == []
        assert _statuses(db, "synced") == [77]

    @pytest.mark.asyncio
    async def test_gone_410_stops_resend(self):
        """K3: 410 は届いたとみなし送り終えた印。"""
        db = _resend_db([(9, "gx", _jt(2026, 11, 26), "gm", False)])
        with _google(_G()), patch(
            "app.services.google_calendar.update_event", new=AsyncMock(side_effect=_wrapped_http(410))
        ):
            from app.services.calendar_service import resend_cancelled_occurrences

            n = await resend_cancelled_occurrences(db, 1, now=_jt(2026, 11, 28))
        assert n == 1 and _statuses(db, "synced") == [9] and _statuses(db, "failed") == []

    @pytest.mark.asyncio
    async def test_not_found_404_stays_failed(self):
        """K3: 404 は送れなかったのまま（次の取り込みでまた送る）。"""
        db = _resend_db([(9, "gx", _jt(2026, 11, 26), "gm", False)])
        with _google(_G()), patch(
            "app.services.google_calendar.update_event", new=AsyncMock(side_effect=_wrapped_http(404))
        ):
            from app.services.calendar_service import resend_cancelled_occurrences

            n = await resend_cancelled_occurrences(db, 1, now=_jt(2026, 11, 28))
        assert n == 0 and _statuses(db, "failed") == [9] and _statuses(db, "synced") == []
```

### 4-6. `class TestSyncTenantFromGoogle:` の中の最後に足す

```python
    @pytest.mark.asyncio
    async def test_resends_cancelled_occurrences_before_reading_only_when_bidirectional(self):
        order: list[str] = []
        service, _ = _make_list_service([{"items": [], "nextSyncToken": "N"}])
        first_list = service.events.return_value.list.side_effect

        def _list(**kw):
            order.append("list")
            return first_list(**kw)

        service.events.return_value.list.side_effect = _list

        async def _resend(db, tenant_id):
            order.append("resend")
            return 0

        with patch("app.services.calendar_service.resend_cancelled_occurrences", new=_resend):
            await self._run(_make_sync_db(cfg=(9, "bidirectional"), sync_token="T"), service)
        assert order == ["resend", "list"]

        resend = AsyncMock(return_value=0)
        service2, _ = _make_list_service([{"items": [], "nextSyncToken": "N"}])
        with patch("app.services.calendar_service.resend_cancelled_occurrences", new=resend):
            await self._run(_make_sync_db(cfg=(9, "read_only"), sync_token="T"), service2)
        resend.assert_not_called()

    @pytest.mark.asyncio
    async def test_resend_failure_does_not_stop_import(self):
        db = _make_sync_db(cfg=(9, "bidirectional"), sync_token="T")
        service, kw = _make_list_service([{"items": [{"id": "a"}], "nextSyncToken": "N"}])
        resend = AsyncMock(side_effect=RuntimeError("boom"))
        with patch("app.services.calendar_service.resend_cancelled_occurrences", new=resend):
            _result, up = await self._run(db, service)
        assert len(kw) == 1 and up.await_count == 1
        db.rollback.assert_awaited()
```

## 5. `backend/tests/test_calendar_sync_tenant_reset_pg.py`

`test_google_series_cancel_with_pending_exception_keeps_rows_on_real_db` の関数の後に足す（本物の PostgreSQL で K1・K2）:

```python
# アプリで消した回は、送れないうちは取り込みで戻らず、送り直しで送り終えた印になる（便7・design §15）
async def test_app_cancelled_occurrence_not_revived_and_resent_on_real_db():
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo

    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    admin_engine, app_engine, factory = await _setup()
    try:
        master = await _create_weekly_master(factory)
        occ = _dt(2026, 12, 10, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            await calendar_service.delete_recurring_event(db, _TENANT, master, "this", occ)
        await _mark_synced_from_app(admin_engine, master["id"], "gm978")
        alive = {
            "id": "gm978_20261210T010000Z", "status": "confirmed", "summary": master["title"],
            "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-10T10:00:00+09:00"},
            "start": {"dateTime": "2026-12-10T10:00:00+09:00"},
            "end": {"dateTime": "2026-12-10T11:00:00+09:00"},
        }
        assert await _import_one(factory, alive, _g_master_for(master)) == "skipped"
        rows = await _exception_rows(admin_engine, master["id"])
        assert [(r[0], r[1]) for r in rows] == [(True, "pending")]

        getter = AsyncMock(return_value={"id": "gm978_20261210T010000Z", "status": "confirmed"})
        sender = AsyncMock(return_value={})
        now = _dt(2026, 12, 1, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            with patch("app.services.google_calendar.get_instance", new=getter), patch(
                "app.services.google_calendar.update_event", new=sender
            ):
                assert await calendar_service.resend_cancelled_occurrences(db, _TENANT, now=now) == 1
        rows = await _exception_rows(admin_engine, master["id"])
        assert [(r[0], r[1]) for r in rows] == [(True, "synced")]
        assert await _count_rows(
            admin_engine,
            "recurring_event_id = :mid AND google_event_id = :gid",
            {"mid": master["id"], "gid": "gm978_20261210T010000Z"},
        ) == 1
        assert sender.await_args.args[2:] == ("gm978_20261210T010000Z", {"status": "cancelled"})

        # もう送るものは無い
        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            assert await calendar_service.resend_cancelled_occurrences(db, _TENANT, now=now) == 0
    finally:
        await _teardown(admin_engine, app_engine)
```

## 6. 確かめ（Mac で試験は回さない。CI に任せる）

- `python -m py_compile` を触った 5 本に流して通ること。
- `git diff --name-only origin/main...HEAD` が、上の 5 本と設計の commit の docs（design.md・recon.md・card-bin7.md）だけであること。

## 7. 想定の分岐（起きたら止めて BLOCKED: で返す。推測で直さない）

- §0 の点検で 1 字でも違う。
- `_FakeDB` の `__init__` が `sync_mode=None` を受けない形だった。
- `_G.fn` が kwargs（`show_deleted=`）を受けない形だった。
- CI で、上の 5 本以外の試験が落ちた。または上の試験が、カードの書き方のままでは通らなかった（直し方を推測で決めない。落ちた試験の名前と生の出力を返す）。

## 8. commit と push

- commit の文: `fix(calendar): keep app-cancelled occurrences and resend the cancel to Google on import`。
- push は `git -C <作業場所の絶対パス> push -u origin release/calendar-occurrence-cancel-resend-impl` の 1 行だけで行う。
- PR は作らない（Opus が作る）。終わったら DONE と commit の id を返す。
