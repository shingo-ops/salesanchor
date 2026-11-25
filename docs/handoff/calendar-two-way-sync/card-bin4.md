# 実装カード 便4: Google で消したらアプリでも隠す・繰り返しの 1 回だけの直し・消しを入れる

- 設計: docs/handoff/calendar-two-way-sync/design.md §12（正）。ADR-1059 改訂 2026-11-25・ADR-1075 改訂 2026-11-25。
- PO の決定: 2026-11-25「３」・「1」（会社の予定も、アプリのみんなの画面から消す）。実装・合流・反映まで委任済み。
- 枝: release/calendar-google-delete（origin/main 起点。`bash scripts/new-worktree.sh release/calendar-google-delete --claude` で作る）。
- 触るファイルは 3 本だけ: `backend/app/services/calendar_service.py`・`backend/app/services/google_webhook.py`・`backend/tests/test_calendar_service.py`。ほかは触らない（migration・画面・文言・ADR も触らない）。

## 0. 着手前の実物点検（違ったら止めて BLOCKED: で返す）

1. `backend/app/services/calendar_service.py` の `def _same_times(` の関数が `return row_start == g_s and row_end == g_e` で終わり、そのすぐ下が空行 2 つと `async def _update_app_origin_from_google(` であること。
2. `_update_app_origin_from_google` の本文が §1-2 の「変更前」と 1 字も違わないこと。
3. `upsert_from_google` の中に §1-3 の「変更前」の 4 行があること。
4. `backend/app/services/google_webhook.py` に §2 の「変更前」の行があること。
5. `backend/tests/test_calendar_service.py` に `def test_cancelled_touches_nothing(self):` と `def test_instance_of_app_origin_is_skipped(self):` が 1 つずつあること。`class _Res:` の `__init__` が `self._rows = rows` の 1 行だけであること。

## 1. `backend/app/services/calendar_service.py`

### 1-1. `_same_times` のすぐ下（`_update_app_origin_from_google` の前）に足す

```python
def _has_times(google_event: dict) -> bool:
    """Google の予定に始まりと終わりがあるか。"""
    g_start = google_event.get("start") or {}
    g_end = google_event.get("end") or {}
    return bool(
        (g_start.get("dateTime") or g_start.get("date"))
        and (g_end.get("dateTime") or g_end.get("date"))
    )


def _content_changes(
    title: Optional[str],
    description: Optional[str],
    location: Optional[str],
    start: datetime,
    end: datetime,
    all_day: bool,
    google_event: dict,
) -> dict:
    """Google の予定とアプリの中身（題名・説明・場所・時間）を比べ、違う列だけを返す。色は見ない。

    始まりと終わりがあることは呼び元が _has_times で確かめる。
    """
    g_start = google_event.get("start") or {}
    g_end = google_event.get("end") or {}
    changes: dict = {}
    g_title = google_event.get("summary") or ""
    if g_title != (title or ""):
        changes["title"] = g_title
    g_desc = google_event.get("description")
    if _norm_text(g_desc) != _norm_text(description):
        changes["description"] = g_desc or None
    g_loc = google_event.get("location")
    if _norm_text(g_loc) != _norm_text(location):
        changes["location"] = g_loc or None
    if not _same_times(start, end, all_day, g_start, g_end):
        s_dt, e_dt, g_all_day = _google_times(g_start, g_end)
        changes["start_datetime"] = s_dt
        changes["end_datetime"] = e_dt
        changes["is_all_day"] = g_all_day
    return changes
```

### 1-2. `_update_app_origin_from_google` の docstring の 1 行目の下から `if not changes:` の前までを置き換える

変更前:

```python
    - Google で消されても消さない（"skipped"）。
    - アプリから送り終えた行（sync_status='synced'）で、中身が違う列だけを書く。
    - 見せ方・持ち主・起源・Meet の URL には触らない。Google へは書かない。
    - 色は Google の名札がアプリの色に当たるときだけ入れる（名札が表に無いときは触らない）。
    - Google に名札も colorId も無く、アプリの色が名札の表にある色なら、色を外す（ADR-1059 改訂 2026-11-22）。
    戻り値は "upserted"（1 行書いた）か "skipped"。commit は呼び元が行う。
    """
    if google_event.get("status") == "cancelled":
        return "skipped"
    g_start = google_event.get("start") or {}
    g_end = google_event.get("end") or {}
    if not (g_start.get("dateTime") or g_start.get("date")) or not (
        g_end.get("dateTime") or g_end.get("date")
    ):
        return "skipped"

    found = await db.execute(
        text(
            "SELECT id, title, description, location, start_datetime, end_datetime,"
            " is_all_day, color_key FROM calendar_events"
            " WHERE google_event_id = :gid"
            " AND sync_origin_id LIKE 'app:" + str(int(tenant_id)) + ":%'"
            " AND sync_status = 'synced'"
            " AND recurrence_rule IS NULL"
            " AND recurring_event_id IS NULL"
        ),
        {"gid": google_event["id"]},
    )
    row = found.first()
    if row is None:
        return "skipped"
    row_id, r_title, r_desc, r_loc, r_start, r_end, r_all_day, r_color = row

    changes: dict = {}
    g_title = google_event.get("summary") or ""
    if g_title != (r_title or ""):
        changes["title"] = g_title
    g_desc = google_event.get("description")
    if _norm_text(g_desc) != _norm_text(r_desc):
        changes["description"] = g_desc or None
    g_loc = google_event.get("location")
    if _norm_text(g_loc) != _norm_text(r_loc):
        changes["location"] = g_loc or None
    if not _same_times(r_start, r_end, r_all_day, g_start, g_end):
        s_dt, e_dt, all_day = _google_times(g_start, g_end)
        changes["start_datetime"] = s_dt
        changes["end_datetime"] = e_dt
        changes["is_all_day"] = all_day
    if label_colors is not None:
```

変更後:

```python
    - Google で消したら（別のカレンダーへ移したときも同じ形で届く）、行は消さず消した印を付けて隠す（"deleted"）。
      自分だけの予定も会社の予定も同じ（ADR-1059 改訂 2026-11-25）。
    - 消した印の行が Google で戻っていたら（cancelled でない）、印を外す。
    - アプリから送り終えた行（sync_status='synced'）で、中身が違う列だけを書く。
    - 見せ方・持ち主・起源・Meet の URL には触らない。Google へは書かない。
    - 色は Google の名札がアプリの色に当たるときだけ入れる（名札が表に無いときは触らない）。
    - Google に名札も colorId も無く、アプリの色が名札の表にある色なら、色を外す（ADR-1059 改訂 2026-11-22）。
    戻り値は "upserted"（1 行書いた）・"deleted"（消した印を付けた）・"skipped"。commit は呼び元が行う。
    """
    if google_event.get("status") == "cancelled":
        res = await db.execute(
            text(
                "UPDATE calendar_events SET is_cancelled = true, last_synced_at = NOW()"
                " WHERE google_event_id = :gid"
                " AND sync_origin_id LIKE 'app:" + str(int(tenant_id)) + ":%'"
                " AND sync_status = 'synced'"
                " AND recurrence_rule IS NULL"
                " AND recurring_event_id IS NULL"
                " AND NOT is_cancelled"
            ),
            {"gid": google_event["id"]},
        )
        return "deleted" if (res.rowcount or 0) > 0 else "skipped"
    if not _has_times(google_event):
        return "skipped"

    found = await db.execute(
        text(
            "SELECT id, title, description, location, start_datetime, end_datetime,"
            " is_all_day, color_key, is_cancelled FROM calendar_events"
            " WHERE google_event_id = :gid"
            " AND sync_origin_id LIKE 'app:" + str(int(tenant_id)) + ":%'"
            " AND sync_status = 'synced'"
            " AND recurrence_rule IS NULL"
            " AND recurring_event_id IS NULL"
        ),
        {"gid": google_event["id"]},
    )
    row = found.first()
    if row is None:
        return "skipped"
    row_id, r_title, r_desc, r_loc, r_start, r_end, r_all_day, r_color, r_cancelled = row

    changes = _content_changes(r_title, r_desc, r_loc, r_start, r_end, r_all_day, google_event)
    if r_cancelled:
        # Google のごみ箱から戻した（ADR-1059 改訂 2026-11-25）
        changes["is_cancelled"] = False
    if label_colors is not None:
```

`if label_colors is not None:` から下（色の扱い・`if not changes:`・UPDATE・return）は 1 字も変えない。

### 1-3. `upsert_from_google`

引数に `series_cache` を足す。変更前:

```python
    owner_user_id: int,
    label_colors: Optional[dict[str, str]] = None,
) -> str:
    """Google のイベントを DB に upsert する。戻り値は "upserted" | "deleted" | "skipped"。
```

変更後:

```python
    owner_user_id: int,
    label_colors: Optional[dict[str, str]] = None,
    series_cache: Optional[dict] = None,
) -> str:
    """Google のイベントを DB に upsert する。戻り値は "upserted" | "deleted" | "skipped"。
```

docstring の「アプリ起源（sync_origin_id が …」の段落のすぐ下に、次の 2 行（空行を挟んで 1 段落）を足す:

```python
    アプリで作った繰り返しの回は _apply_app_instance_from_google でその回だけを入れる（ADR-1075 改訂 2026-11-25）。
    series_cache は 1 回の取り込みで Google の元の予定を 1 回だけ読むための入れ物（取り込みが作って渡す）。
```

本文の変更前:

```python
    # アプリで作った繰り返しの回は飛ばす（ADR-1075 決定6）
    recurring_event_id = google_event.get("recurringEventId")
    if recurring_event_id and await _is_app_origin(db, recurring_event_id, tenant_id):
        return "skipped"
```

変更後:

```python
    # アプリで作った繰り返しの回は、その回だけの直し・消しを入れる（ADR-1075 改訂 2026-11-25）
    recurring_event_id = google_event.get("recurringEventId")
    if recurring_event_id and await _is_app_origin(db, recurring_event_id, tenant_id):
        return await _apply_app_instance_from_google(db, tenant_id, google_event, series_cache)
```

### 1-4. `upsert_from_google` のすぐ上（`_update_app_origin_from_google` の関数の後）に足す

```python
def _rule_parts(rule: str) -> dict[str, str]:
    """決まりの文字を「名前→値」の表にする（並びの違いを見ないで比べるため）。"""
    parts: dict[str, str] = {}
    for part in rule.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            parts[key.strip().upper()] = value.strip()
    return parts


def _same_series(master: dict, g_master: Optional[dict]) -> bool:
    """Google の元の予定が、アプリの元の行と同じ繰り返しのままか（ADR-1075 改訂 2026-11-25）。

    違えば Google で「これ以降」「すべて」を直した・消したとみなす。決まりは RRULE の行だけを比べる
    （EXDATE・RDATE の行は見ない）。題名・説明・場所・始まりと終わりも比べる。色は見ない。
    """
    if not g_master or g_master.get("status") == "cancelled" or not _has_times(g_master):
        return False
    rules = [
        line[len("RRULE:"):]
        for line in (g_master.get("recurrence") or [])
        if line.upper().startswith("RRULE:")
    ]
    if len(rules) != 1 or _rule_parts(rules[0]) != _rule_parts(master["recurrence_rule"] or ""):
        return False
    return not _content_changes(
        master["title"],
        master["description"],
        master["location"],
        master["start_datetime"],
        master["end_datetime"],
        bool(master["is_all_day"]),
        g_master,
    )


async def _adopt_google_instance(db: AsyncSession, tenant_id: int, row_id: int, google_event_id: str) -> None:
    """取り込みで作った例外の行に Google の回の id を持たせ、送り終えた印を付ける（commit は呼び元）。"""
    await db.execute(
        text(
            "UPDATE calendar_events SET google_event_id = :gid, sync_origin_id = :oid,"
            " sync_status = 'synced', last_synced_at = NOW() WHERE id = :id"
        ),
        {"gid": google_event_id, "oid": _build_sync_origin_id(tenant_id, row_id), "id": row_id},
    )


async def _apply_app_instance_from_google(
    db: AsyncSession,
    tenant_id: int,
    google_event: dict,
    series_cache: Optional[dict] = None,
) -> str:
    """アプリで作った繰り返しの 1 回分を Google で直した・消したとき、その回だけを入れる（ADR-1075 改訂 2026-11-25）。

    - 元の行は、アプリから送り終えた（synced）繰り返しの元の行だけ。無ければ "skipped"。
    - Google の元の予定を 1 回の取り込みに 1 回だけ読み（series_cache）、アプリの元の行と違えば
      「これ以降」「すべて」の直し・消しとみなして "skipped"（アプリは今のまま）。
    - 回は originalStartTime で決める。アプリの決まりの回でなければ "skipped"。
    - 例外の行が送り中（pending）・送れなかった（failed）ときは触らない。
    - 消した回: 例外の行に消した印を付ける（無ければ作る）。
    - 直した回: 期待する中身（例外の行、無ければ元の行の中身をその回の時間にしたもの）と違うときだけ書く。色は入れない。
    Google へは書かない。commit は呼び元。戻り値は "upserted" | "deleted" | "skipped"。
    """
    from app.services import google_calendar as gcal

    cache = series_cache if series_cache is not None else {}
    master_gid = google_event["recurringEventId"]
    found = await db.execute(
        text(
            f"SELECT {EVENT_COLUMNS_SQL} FROM calendar_events"
            " WHERE google_event_id = :gid"
            " AND sync_origin_id LIKE 'app:" + str(int(tenant_id)) + ":%'"
            " AND sync_status = 'synced'"
            " AND recurrence_rule IS NOT NULL"
            " AND recurring_event_id IS NULL"
        ),
        {"gid": master_gid},
    )
    record = found.first()
    if record is None:
        return "skipped"
    master = event_from_row(record)
    orig = google_event.get("originalStartTime") or {}
    if not (orig.get("dateTime") or orig.get("date")):
        return "skipped"

    if master_gid not in cache:
        try:
            cache[master_gid] = await gcal.get_event(db, tenant_id, master_gid)
        except Exception as e:
            logger.warning("Google の繰り返しの元の予定を読めませんでした (google_event_id=%s): %s", master_gid, e)
            cache[master_gid] = None
    if not _same_series(master, cache[master_gid]):
        return "skipped"

    m_all_day = bool(master["is_all_day"])
    m_start = rec.to_jst(master["start_datetime"])
    orig_start = _google_times(orig, orig)[0]
    if not rec.is_occurrence(master["recurrence_rule"], m_start, m_all_day, orig_start):
        return "skipped"
    occ = rec.occurrence_of(m_start, m_all_day, orig_start)
    duration = rec.to_jst(master["end_datetime"]) - m_start

    exc_found = await db.execute(
        text(
            "SELECT id, title, description, location, start_datetime, end_datetime,"
            " is_all_day, is_cancelled, sync_status FROM calendar_events"
            " WHERE recurring_event_id = :mid AND original_start_datetime = :orig"
        ),
        {"mid": master["id"], "orig": occ},
    )
    exc = exc_found.first()
    if exc is not None and exc[8] != "synced":
        return "skipped"

    if google_event.get("status") == "cancelled":
        if exc is None:
            new_id = await _insert_row(
                db,
                _row_values(
                    master,
                    start_datetime=occ,
                    end_datetime=occ + duration,
                    recurring_event_id=master["id"],
                    original_start_datetime=occ,
                    is_cancelled=True,
                ),
            )
            await _adopt_google_instance(db, tenant_id, new_id, google_event["id"])
            return "deleted"
        if exc[7]:
            return "skipped"
        res = await db.execute(
            text(
                "UPDATE calendar_events SET is_cancelled = true, last_synced_at = NOW()"
                " WHERE id = :id AND sync_status = 'synced'"
            ),
            {"id": exc[0]},
        )
        return "deleted" if (res.rowcount or 0) > 0 else "skipped"

    if not _has_times(google_event):
        return "skipped"
    if exc is None:
        changes = _content_changes(
            master["title"], master["description"], master["location"],
            occ, occ + duration, m_all_day, google_event,
        )
        if not changes:
            return "skipped"
        values = _row_values(
            master,
            start_datetime=occ,
            end_datetime=occ + duration,
            recurring_event_id=master["id"],
            original_start_datetime=occ,
        )
        values.update(changes)
        new_id = await _insert_row(db, values)
        await _adopt_google_instance(db, tenant_id, new_id, google_event["id"])
        return "upserted"

    changes = _content_changes(exc[1], exc[2], exc[3], exc[4], exc[5], bool(exc[6]), google_event)
    if exc[7]:
        changes["is_cancelled"] = False
    if not changes:
        return "skipped"
    sets = ", ".join(f"{col} = :{col}" for col in changes)
    res = await db.execute(
        text(
            f"UPDATE calendar_events SET {sets}, last_synced_at = NOW()"
            " WHERE id = :id AND sync_status = 'synced'"
        ),
        {**changes, "id": exc[0]},
    )
    return "upserted" if (res.rowcount or 0) > 0 else "skipped"
```

## 2. `backend/app/services/google_webhook.py`

変更前:

```python
        # 名札の表を読む中でトークン更新の commit が入ることがあるので文脈を張り直す
        await set_tenant_context(db, tenant_id)
        legacy_colorid = 0
        for item in items:
            if item.get("colorId") and not item.get("eventLabelId"):
                legacy_colorid += 1
            outcome = await upsert_from_google(
                db, tenant_id, item, owner_user_id, label_colors=label_colors
            )
```

変更後:

```python
        # 名札の表を読む中でトークン更新の commit が入ることがあるので文脈を張り直す
        await set_tenant_context(db, tenant_id)
        # アプリで作った繰り返しの Google の元の予定は、1 回の取り込みに 1 回だけ読む（ADR-1075 改訂 2026-11-25）
        series_cache: dict = {}
        legacy_colorid = 0
        for item in items:
            if item.get("colorId") and not item.get("eventLabelId"):
                legacy_colorid += 1
            outcome = await upsert_from_google(
                db, tenant_id, item, owner_user_id, label_colors=label_colors, series_cache=series_cache
            )
```

## 3. `backend/tests/test_calendar_service.py`

### 3-1. 試験の道具

`_app_origin_db` の docstring の下（`db = AsyncMock()` の前）に 2 行足す:

```python
    if row is not None and len(row) == 8:
        row = (*row, False)  # 便4 で消した印（is_cancelled）も読むようにした
```

`class _Res:` の `__init__` を次にする（UPDATE の行数を読む新しい道のため）:

```python
    def __init__(self, rows, rowcount=1):
        self._rows = rows
        self.rowcount = rowcount
```

### 3-2. `test_cancelled_touches_nothing` を消し、同じ場所に次の 2 つを置く

```python
    @pytest.mark.asyncio
    async def test_cancelled_marks_synced_row_cancelled(self):
        db = _app_origin_db((5, "題", None, None, _T1, _T2, False, None))
        assert await self._go(db, _g_event(status="cancelled")) == "deleted"
        sqls = [s for s, _ in db.calls]
        assert not any(s.lstrip().startswith(("SELECT id, title", "DELETE")) for s in sqls)
        ups = _updates(db)
        assert len(ups) == 1
        sql, params = ups[0]
        assert "is_cancelled = true" in sql
        for guard in ("sync_status = 'synced'", "recurrence_rule IS NULL", "recurring_event_id IS NULL", "NOT is_cancelled"):
            assert guard in sql
        assert params == {"gid": "ev_app"}
        db0 = _app_origin_db(None, rowcount=0)
        assert await self._go(db0, _g_event(status="cancelled")) == "skipped"

    @pytest.mark.asyncio
    async def test_restored_in_google_clears_cancel(self):
        db = _app_origin_db((5, "題", None, None, _T1, _T2, False, None, True))
        assert await self._go(db, _g_event()) == "upserted"
        ups = _updates(db)
        assert len(ups) == 1
        assert "is_cancelled = :is_cancelled" in ups[0][0]
        assert ups[0][1]["is_cancelled"] is False
        assert set(ups[0][1]) == {"is_cancelled", "id"}
```

### 3-3. `class TestUpsertRecurringInstance:` の中身を全部、次に置き換える

（`test_instance_of_app_origin_is_skipped` は消える。クラス名はそのまま。道具 `_inst_db`・`_g_master`・`_g_inst` はクラスのすぐ上に置く）

```python
def _inst_db(master=None, exc=None, new_id=77, has_master=True):
    """アプリで作った繰り返しの回の取り込み用。exc は (id, 題, 説明, 場所, 始, 終, 終日, 消した印, 送り) の 9 列。"""
    master = master or _ev()
    return _FakeDB(
        [
            ("SELECT 1 FROM calendar_events", [(1,)]),
            ("recurrence_rule IS NOT NULL", [_tup(master)] if has_master else []),
            ("is_cancelled, sync_status FROM", [exc] if exc else []),
            ("INSERT INTO calendar_events", [(new_id,)]),
        ],
        sync_mode=None,
    )


def _g_master(**over) -> dict:
    d = {
        "id": "gm", "status": "confirmed", "summary": "定例",
        "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=TH"],
        "start": {"dateTime": "2026-11-12T10:00:00+09:00"},
        "end": {"dateTime": "2026-11-12T11:00:00+09:00"},
    }
    d.update(over)
    return d


def _g_inst(day=26, **over) -> dict:
    d = {
        "id": f"gm_202611{day:02d}T010000Z", "status": "confirmed", "summary": "定例",
        "recurringEventId": "gm",
        "originalStartTime": {"dateTime": f"2026-11-{day:02d}T10:00:00+09:00"},
        "start": {"dateTime": f"2026-11-{day:02d}T10:00:00+09:00"},
        "end": {"dateTime": f"2026-11-{day:02d}T11:00:00+09:00"},
    }
    d.update(over)
    return d


class TestUpsertRecurringInstance:
    async def _go(self, db, event, g_master=None, cache=None, get_event=None):
        from app.services.calendar_service import upsert_from_google

        getter = get_event or AsyncMock(return_value=g_master or _g_master())
        with patch("app.services.google_calendar.get_event", new=getter):
            out = await upsert_from_google(db, 1, event, 5, series_cache=cache)
        return out, getter

    @staticmethod
    def _writes(db):
        return [(s, p) for s, p in db.calls if s.lstrip().startswith(("INSERT", "UPDATE", "DELETE"))]

    @pytest.mark.asyncio
    async def test_same_as_series_writes_nothing(self):
        db = _inst_db()
        out, getter = await self._go(db, _g_inst())
        assert out == "skipped"
        assert self._writes(db) == []
        assert getter.await_count == 1

    @pytest.mark.asyncio
    async def test_google_master_is_read_once_per_sync(self):
        cache: dict = {}
        getter = AsyncMock(return_value=_g_master())
        for day in (19, 26):
            db = _inst_db()
            await self._go(db, _g_inst(day), cache=cache, get_event=getter)
        assert getter.await_count == 1

    @pytest.mark.asyncio
    async def test_single_instance_edit_inserts_synced_exception(self):
        db = _inst_db()
        out, _ = await self._go(db, _g_inst(summary="臨時"))
        assert out == "upserted"
        (ins_sql, ins), (up_sql, up) = self._writes(db)
        assert ins_sql.lstrip().startswith("INSERT")
        assert ins["title"] == "臨時"
        assert ins["recurring_event_id"] == 1
        assert ins["original_start_datetime"] == _jt(2026, 11, 26)
        assert ins["start_datetime"] == _jt(2026, 11, 26) and ins["end_datetime"] == _jt(2026, 11, 26, 11)
        assert ins["is_cancelled"] is False
        assert ins["calendar_type"] == "shared" and ins["user_id"] == 5
        assert "sync_status = 'synced'" in up_sql
        assert up == {"gid": "gm_20261126T010000Z", "oid": "app:1:77", "id": 77}

    @pytest.mark.asyncio
    async def test_single_instance_delete_inserts_cancelled_exception(self):
        db = _inst_db()
        out, _ = await self._go(db, {"id": "gm_20261126T010000Z", "status": "cancelled", "recurringEventId": "gm",
                                     "originalStartTime": {"dateTime": "2026-11-26T10:00:00+09:00"}})
        assert out == "deleted"
        (ins_sql, ins), (_up_sql, up) = self._writes(db)
        assert ins["is_cancelled"] is True and ins["original_start_datetime"] == _jt(2026, 11, 26)
        assert up["gid"] == "gm_20261126T010000Z"

    @pytest.mark.asyncio
    async def test_cancel_existing_synced_exception(self):
        exc = (9, "定例", None, None, _jt(2026, 11, 26, 14), _jt(2026, 11, 26, 15), False, False, "synced")
        db = _inst_db(exc=exc)
        out, _ = await self._go(db, _g_inst(status="cancelled"))
        assert out == "deleted"
        writes = self._writes(db)
        assert len(writes) == 1
        assert "is_cancelled = true" in writes[0][0] and writes[0][1] == {"id": 9}

    @pytest.mark.asyncio
    async def test_already_cancelled_or_not_synced_is_skipped(self):
        cancelled = (9, "定例", None, None, _jt(2026, 11, 26), _jt(2026, 11, 26, 11), False, True, "synced")
        db = _inst_db(exc=cancelled)
        assert (await self._go(db, _g_inst(status="cancelled")))[0] == "skipped"
        assert self._writes(db) == []
        for status in ("pending", "failed"):
            pending = (9, "定例", None, None, _jt(2026, 11, 26), _jt(2026, 11, 26, 11), False, False, status)
            db = _inst_db(exc=pending)
            assert (await self._go(db, _g_inst(summary="臨時")))[0] == "skipped"
            assert self._writes(db) == []

    @pytest.mark.asyncio
    async def test_edit_existing_exception_and_restore(self):
        exc = (9, "定例", None, None, _jt(2026, 11, 26), _jt(2026, 11, 26, 11), False, False, "synced")
        db = _inst_db(exc=exc)
        out, _ = await self._go(db, _g_inst(location="会議室"))
        assert out == "upserted"
        (sql, params), = self._writes(db)
        assert "WHERE id = :id AND sync_status = 'synced'" in sql
        assert params == {"location": "会議室", "id": 9}
        restored = (9, "定例", None, None, _jt(2026, 11, 26), _jt(2026, 11, 26, 11), False, True, "synced")
        db = _inst_db(exc=restored)
        out, _ = await self._go(db, _g_inst())
        assert out == "upserted"
        (_sql, params), = self._writes(db)
        assert params == {"is_cancelled": False, "id": 9}

    @pytest.mark.asyncio
    async def test_series_changed_in_google_is_skipped(self):
        changed = [
            _g_master(recurrence=["RRULE:FREQ=WEEKLY;BYDAY=TH;UNTIL=20261119T145959Z"]),
            _g_master(summary="定例（新）"),
            _g_master(start={"dateTime": "2026-11-12T11:00:00+09:00"}, end={"dateTime": "2026-11-12T12:00:00+09:00"}),
            _g_master(status="cancelled"),
        ]
        for g in changed:
            db = _inst_db()
            out, _ = await self._go(db, _g_inst(summary="臨時"), g_master=g)
            assert out == "skipped"
            assert self._writes(db) == []
        db = _inst_db()
        out, _ = await self._go(db, _g_inst(summary="臨時"), get_event=AsyncMock(side_effect=RuntimeError("boom")))
        assert out == "skipped"
        assert self._writes(db) == []

    @pytest.mark.asyncio
    async def test_rule_order_and_exdate_lines_are_ignored(self):
        db = _inst_db()
        g = _g_master(recurrence=["RRULE:BYDAY=TH;FREQ=WEEKLY", "EXDATE;TZID=Asia/Tokyo:20261119T100000"])
        out, _ = await self._go(db, _g_inst(summary="臨時"), g_master=g)
        assert out == "upserted"

    @pytest.mark.asyncio
    async def test_not_an_occurrence_or_no_synced_master_is_skipped(self):
        db = _inst_db()
        fri = _g_inst(originalStartTime={"dateTime": "2026-11-27T10:00:00+09:00"}, summary="臨時")
        assert (await self._go(db, fri))[0] == "skipped"
        assert self._writes(db) == []
        db = _inst_db(has_master=False)
        out, getter = await self._go(db, _g_inst(summary="臨時"))
        assert out == "skipped"
        assert getter.await_count == 0
        assert self._writes(db) == []
```

### 3-4. `class TestSyncTenantFromGoogle:` の最後に 1 つ足す

```python
    @pytest.mark.asyncio
    async def test_passes_one_series_cache_per_sync(self):
        db = _make_sync_db(sync_token="T")
        service, _ = _make_list_service([{"items": [{"id": "a"}, {"id": "b"}], "nextSyncToken": "N"}])
        _result, up = await self._run(db, service)
        caches = [c.kwargs["series_cache"] for c in up.await_args_list]
        assert len(caches) == 2 and caches[0] is caches[1] and caches[0] == {}
```

## 4. 確かめ（Mac で試験は回さない。CI に任せる）

1. `git diff --name-only origin/main...HEAD` が §0 の 3 本だけであること。
2. `cd backend && ruff check app/services/calendar_service.py app/services/google_webhook.py tests/test_calendar_service.py` が通ること（入っていなければ「ruff なし」と書く）。
3. `python -c "import ast,sys; [ast.parse(open(f).read()) for f in sys.argv[1:]]" backend/app/services/calendar_service.py backend/app/services/google_webhook.py backend/tests/test_calendar_service.py` が何も出さないこと。

## 5. commit と push

- commit の文:

```
feat(calendar): reflect Google deletes and single-instance edits of app events (ADR-1059/1075 rev 2026-11-25)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

- `git push -u origin release/calendar-google-delete`。PR は作らない。
- 返事の最後の行は `DONE <HEAD の sha>` か `BLOCKED: <理由>`。

## 6. 改め（2026-11-25・DB の決まりに合わせる。design.md §12-10 が正）

この節は、上の 1〜5 を入れたコミット 70451bf3c の上に足す直しです。上の 1〜5 はもう入っているので、やり直さない。

- 枝: release/calendar-google-delete（HEAD 70451bf3c の上に 1 コミット足す。`git fetch origin` のあと `bash scripts/new-worktree.sh release/calendar-google-delete --claude` で場所を作り、`git log -1 --format=%H` が 70451bf3c で始まることを確かめる。違えば BLOCKED:）。
- 触るファイルは 3 本だけ: `backend/app/services/calendar_service.py`・`backend/tests/test_calendar_service.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`。ほかは触らない（文書は Opus が入れた）。

### 6-0. 着手前の実物点検（違ったら止めて BLOCKED:）

1. `calendar_service.py` の `_update_app_origin_from_google` に、6-1 の「変更前」がそのままあること。
2. 同じ関数に `" is_all_day, color_key, is_cancelled FROM calendar_events"` が 1 つと、`row_id, r_title, r_desc, r_loc, r_start, r_end, r_all_day, r_color, r_cancelled = row` が 1 つあること。
3. `_apply_app_instance_from_google` に `new_id = await _insert_row(` が 2 つあること。
4. `test_calendar_service.py` に `def test_cancelled_marks_synced_row_cancelled(self):` と `def test_restored_in_google_clears_cancel(self):` が 1 つずつあり、`_app_origin_db` の中に `row = (*row, False)  # 便4 で消した印（is_cancelled）も読むようにした` があること。
5. `test_calendar_sync_tenant_reset_pg.py` の最後の試験が `test_same_occurrence_exception_twice_is_rejected_by_unique_index` であること。

### 6-1. 単発の消しを「行を消す」に替える（`_update_app_origin_from_google`）

変更前:

```python
    if google_event.get("status") == "cancelled":
        res = await db.execute(
            text(
                "UPDATE calendar_events SET is_cancelled = true, last_synced_at = NOW()"
                " WHERE google_event_id = :gid"
                " AND sync_origin_id LIKE 'app:" + str(int(tenant_id)) + ":%'"
                " AND sync_status = 'synced'"
                " AND recurrence_rule IS NULL"
                " AND recurring_event_id IS NULL"
                " AND NOT is_cancelled"
            ),
            {"gid": google_event["id"]},
        )
        return "deleted" if (res.rowcount or 0) > 0 else "skipped"
```

変更後:

```python
    if google_event.get("status") == "cancelled":
        # 単発の行には消した印を付けられない（calendar_events_cancelled_exception_check）。
        # アプリで消すとき（delete_event）と同じく行を消す（ADR-1059 改訂 2026-11-25）
        res = await db.execute(
            text(
                "DELETE FROM calendar_events"
                " WHERE google_event_id = :gid"
                " AND sync_origin_id LIKE 'app:" + str(int(tenant_id)) + ":%'"
                " AND sync_status = 'synced'"
                " AND recurrence_rule IS NULL"
                " AND recurring_event_id IS NULL"
            ),
            {"gid": google_event["id"]},
        )
        return "deleted" if (res.rowcount or 0) > 0 else "skipped"
```

同じ関数の docstring の次の 2 行を、

```
    - Google で消したら（別のカレンダーへ移したときも同じ形で届く）、行は消さず消した印を付けて隠す（"deleted"）。
      自分だけの予定も会社の予定も同じ（ADR-1059 改訂 2026-11-25）。
    - 消した印の行が Google で戻っていたら（cancelled でない）、印を外す。
```

次の 2 行に替える（3 行目の「消した印の行が…」は消す）:

```
    - Google で消したら（別のカレンダーへ移したときも同じ形で届く）、送り終えた単発の行を消す（"deleted"）。
      自分だけの予定も会社の予定も同じ（ADR-1059 改訂 2026-11-25）。
```

docstring の `戻り値は "upserted"（1 行書いた）・"deleted"（消した印を付けた）・"skipped"。` は `戻り値は "upserted"（1 行書いた）・"deleted"（行を消した）・"skipped"。` に替える。

### 6-2. 単発の戻しの道を取る（届かない道）

同じ関数で:

- `" is_all_day, color_key, is_cancelled FROM calendar_events"` → `" is_all_day, color_key FROM calendar_events"`
- `row_id, r_title, r_desc, r_loc, r_start, r_end, r_all_day, r_color, r_cancelled = row` → `row_id, r_title, r_desc, r_loc, r_start, r_end, r_all_day, r_color = row`
- 次の 3 行を消す:

```python
    if r_cancelled:
        # Google のごみ箱から戻した（ADR-1059 改訂 2026-11-25）
        changes["is_cancelled"] = False
```

### 6-3. 例外の行を作る前に Google の id の重なりを確かめる（`_apply_app_instance_from_google`）

`_adopt_google_instance` の関数のすぐ下（空行 2 つを挟む）に足す:

```python
async def _google_id_taken(db: AsyncSession, google_event_id: str) -> bool:
    """回の Google の id を持つ行が既にあるか。あれば例外の行を作らない（重なり禁止 uq_calendar_events_google_event_id）。"""
    res = await db.execute(
        text("SELECT id FROM calendar_events WHERE google_event_id = :gid"),
        {"gid": google_event_id},
    )
    return res.first() is not None
```

`_apply_app_instance_from_google` の中の `new_id = await _insert_row(` の 2 か所それぞれのすぐ前に、同じ字下げで次を入れる:

```python
            if await _google_id_taken(db, google_event["id"]):
                logger.warning("回の Google の id を持つ行が既にあるため飛ばしました (google_event_id=%s)", google_event["id"])
                return "skipped"
```

（1 か所目は `if exc is None:` の中で字下げ 12、2 か所目は `values.update(changes)` の下で字下げ 8。それぞれ `new_id = await _insert_row(` と同じ字下げにそろえる。）

### 6-4. `backend/tests/test_calendar_service.py`

1. `_app_origin_db` の中の次の 2 行を消す:

```python
    if row is not None and len(row) == 8:
        row = (*row, False)  # 便4 で消した印（is_cancelled）も読むようにした
```

2. `test_cancelled_marks_synced_row_cancelled` を、次に置き換える（名前も替える）:

```python
    @pytest.mark.asyncio
    async def test_cancelled_deletes_synced_single_row(self):
        db = _app_origin_db((5, "題", None, None, _T1, _T2, False, None))
        assert await self._go(db, _g_event(status="cancelled")) == "deleted"
        sqls = [s for s, _ in db.calls]
        assert not any(s.lstrip().startswith("SELECT id, title") for s in sqls)
        assert _updates(db) == []
        dels = [(s, p) for s, p in db.calls if s.lstrip().startswith("DELETE")]
        assert len(dels) == 1
        sql, params = dels[0]
        assert "is_cancelled" not in sql
        for guard in ("sync_status = 'synced'", "recurrence_rule IS NULL", "recurring_event_id IS NULL", "LIKE 'app:1:%'"):
            assert guard in sql
        assert params == {"gid": "ev_app"}
        db0 = _app_origin_db(None, rowcount=0)
        assert await self._go(db0, _g_event(status="cancelled")) == "skipped"
```

3. `test_restored_in_google_clears_cancel` を関数ごと消す（デコレータの行も）。
4. `class TestUpsertRecurringInstance:` の最後に足す:

```python
    @pytest.mark.asyncio
    async def test_google_id_already_taken_is_skipped(self):
        for event in (
            {"id": "gm_20261126T010000Z", "status": "cancelled", "recurringEventId": "gm",
             "originalStartTime": {"dateTime": "2026-11-26T10:00:00+09:00"}},
            _g_inst(summary="臨時"),
        ):
            db = _inst_db()
            db.handlers.insert(0, ("SELECT id FROM calendar_events WHERE google_event_id", [(50,)]))
            out, _ = await self._go(db, event)
            assert out == "skipped"
            assert self._writes(db) == []
```

### 6-5. `backend/tests/test_calendar_sync_tenant_reset_pg.py`（本物の PostgreSQL で DB の決まりを通す）

ファイルの最後に足す（CI では本物の PostgreSQL がある。Mac では回さない）:

```python
async def _mark_synced_from_app(admin_engine, event_id: int, gid: str) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(
            text(
                f"UPDATE {_SCHEMA}.calendar_events SET google_event_id = :gid,"
                " sync_origin_id = :oid, sync_status = 'synced' WHERE id = :id"
            ),
            {"gid": gid, "oid": f"app:{_TENANT}:{event_id}", "id": event_id},
        )


async def _count_rows(admin_engine, where_sql: str, params: dict) -> int:
    from sqlalchemy import text

    async with admin_engine.connect() as conn:
        return (
            await conn.execute(
                text(f"SELECT count(*) FROM {_SCHEMA}.calendar_events WHERE {where_sql}"), params
            )
        ).scalar_one()


async def _import_one(factory, item: dict, g_master: dict | None = None) -> str:
    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    getter = AsyncMock(return_value=g_master)
    async with factory() as db:
        await set_tenant_context(db, _TENANT)
        with patch("app.services.google_calendar.get_event", new=getter):
            out = await calendar_service.upsert_from_google(db, _TENANT, item, _OWNER, series_cache={})
        await db.commit()
    return out


def _g_master_for(master: dict) -> dict:
    return {
        "id": "gm978", "status": "confirmed", "summary": master["title"],
        "recurrence": ["RRULE:" + master["recurrence_rule"]],
        "start": {"dateTime": "2026-12-03T10:00:00+09:00"},
        "end": {"dateTime": "2026-12-03T11:00:00+09:00"},
    }


# Google で消したアプリの単発の予定は、DB の決まりに外れずに行ごと消える（ADR-1059 改訂 2026-11-25）
async def test_google_cancel_deletes_app_single_row_on_real_db():
    from app.auth.dependencies import set_tenant_context
    from app.services import calendar_service

    admin_engine, app_engine, factory = await _setup()
    try:
        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            created = await calendar_service.create_event(db, _TENANT, _OTHER, _payload())
        await _mark_synced_from_app(admin_engine, created["id"], "g_single_978")
        out = await _import_one(factory, {"id": "g_single_978", "status": "cancelled"})
        assert out == "deleted"
        assert await _count_rows(admin_engine, "id = :id", {"id": created["id"]}) == 0
    finally:
        await _teardown(admin_engine, app_engine)


# 繰り返しの 1 回だけの消し・直しは、例外の行として DB の決まりに通る（ADR-1075 改訂 2026-11-25）
async def test_google_instance_cancel_and_edit_insert_exceptions_on_real_db():
    admin_engine, app_engine, factory = await _setup()
    try:
        master = await _create_weekly_master(factory)
        await _mark_synced_from_app(admin_engine, master["id"], "gm978")
        g_master = _g_master_for(master)
        cancelled = {
            "id": "gm978_20261210T010000Z", "status": "cancelled", "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-10T10:00:00+09:00"},
        }
        assert await _import_one(factory, cancelled, g_master) == "deleted"
        edited = {
            "id": "gm978_20261217T010000Z", "status": "confirmed", "summary": "臨時",
            "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-17T10:00:00+09:00"},
            "start": {"dateTime": "2026-12-17T10:00:00+09:00"},
            "end": {"dateTime": "2026-12-17T11:00:00+09:00"},
        }
        assert await _import_one(factory, edited, g_master) == "upserted"
        rows = sorted(await _exception_rows(admin_engine, master["id"]))
        assert rows == [(False, "synced"), (True, "synced")]
        assert await _count_rows(
            admin_engine,
            "recurring_event_id = :mid AND title = '臨時' AND google_event_id = :gid",
            {"mid": master["id"], "gid": "gm978_20261217T010000Z"},
        ) == 1
        # 同じ知らせがもう一度来ても、何も書かない
        assert await _import_one(factory, cancelled, g_master) == "skipped"
        assert await _import_one(factory, edited, g_master) == "skipped"
    finally:
        await _teardown(admin_engine, app_engine)


# 回の Google の id を持つ行が既にあれば、例外の行を作らずに飛ばす（取り込みを止めない）
async def test_google_instance_with_taken_id_is_skipped_on_real_db():
    from sqlalchemy import text

    admin_engine, app_engine, factory = await _setup()
    try:
        master = await _create_weekly_master(factory)
        await _mark_synced_from_app(admin_engine, master["id"], "gm978")
        async with admin_engine.begin() as conn:
            await conn.execute(
                text(
                    f"INSERT INTO {_SCHEMA}.calendar_events"
                    " (title, start_datetime, end_datetime, source, sync_status, google_event_id)"
                    " VALUES ('先にある行', :s, :e, 'google', 'synced', 'gm978_20261224T010000Z')"
                ),
                {
                    "s": datetime(2026, 12, 24, 1, 0, tzinfo=timezone.utc),
                    "e": datetime(2026, 12, 24, 2, 0, tzinfo=timezone.utc),
                },
            )
        cancelled = {
            "id": "gm978_20261224T010000Z", "status": "cancelled", "recurringEventId": "gm978",
            "originalStartTime": {"dateTime": "2026-12-24T10:00:00+09:00"},
        }
        assert await _import_one(factory, cancelled, _g_master_for(master)) == "skipped"
        assert await _exception_rows(admin_engine, master["id"]) == []
    finally:
        await _teardown(admin_engine, app_engine)
```

想定分岐（迷ったら止めて NEEDS_DECISION: で返す。推測で直さない）:

- `create_event` が `_OTHER`（つないでいない人）で作った単発の行の形が `_mark_synced_from_app` の UPDATE で決まりに外れる → 止める。
- `_create_weekly_master` の `master["recurrence_rule"]` が `FREQ=WEEKLY` で始まらない → 止める。
- 6-5 の 3 本のどれかが CI で落ちたら、その試験の失敗の全文を返事に貼って止める（コードを推測で直さない）。

### 6-6. 確かめ（Mac で試験は回さない。CI に任せる）

1. `git diff --name-only 70451bf3c..HEAD` が 6 の 3 本だけであること。
2. `git grep -n "is_cancelled = true" -- backend/app/services/calendar_service.py` の結果に、`recurring_event_id IS NULL` の行を直す文が無いこと（あるのは例外の行と、アプリの「この予定」を消す所だけ）。結果を返事に全部貼る。
3. ruff と ast の確かめは 4 と同じ（3 本に替える）。

### 6-7. commit と push

```
fix(calendar): delete app single rows on Google cancel and guard instance id collisions (ADR-1059 rev 2026-11-25)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

- `git push -u origin release/calendar-google-delete`。PR は作らない（もうある）。
- 返事の最後の行は `DONE <HEAD の sha>` か `BLOCKED: <理由>` か `NEEDS_DECISION: <理由>`。
