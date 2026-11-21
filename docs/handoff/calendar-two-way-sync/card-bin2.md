# 実装カード 便2: Google で色を「なし」に戻したらアプリの色も外す

- 設計: docs/handoff/calendar-two-way-sync/design.md §10（正）。ADR-1059 改訂 2026-11-22。
- PO の決定: 2026-11-22「1. アプリの色も外して、Googleとそろえる」。実装・合流・反映まで委任済み。
- 枝: release/calendar-color-clear（origin/main 2560f963f 起点）。
- 触るファイルは 2 本だけ: `backend/app/services/calendar_service.py`・`backend/tests/test_calendar_service.py`。ほかは触らない。

## 0. 着手前の実物点検（違ったら止めて BLOCKED: で返す）

1. `backend/app/services/calendar_service.py:31` が `from app.services.event_colors import key_for_hex` であること。
2. `backend/app/services/calendar_service.py:1460-1464` が下の「変更前」と一字一句同じであること。
3. `backend/tests/test_calendar_service.py:685-698` に `test_color_only_when_label_matches` があること。

## 1. `backend/app/services/calendar_service.py`

### 1-1. 31 行目（import）

変更前:
```python
from app.services.event_colors import key_for_hex
```
変更後:
```python
from app.services.event_colors import EVENT_COLORS, key_for_hex
```

### 1-2. `_update_app_origin_from_google` の docstring（1416 行目）

変更前:
```python
    - 色は Google の名札がアプリの色に当たるときだけ入れる（名札が無い・表に無いときは触らない）。
```
変更後:
```python
    - 色は Google の名札がアプリの色に当たるときだけ入れる（名札が表に無いときは触らない）。
    - Google に名札も colorId も無く、アプリの色が名札の表にある色なら、色を外す（ADR-1059 改訂 2026-11-22）。
```

### 1-3. 色の比べ方（1460-1464 行目）

変更前:
```python
    if label_colors is not None:
        label_id = google_event.get("eventLabelId")
        g_color = key_for_hex(label_colors.get(label_id)) if label_id else None
        if g_color is not None and g_color != r_color:
            changes["color_key"] = g_color
```
変更後:
```python
    if label_colors is not None:
        label_id = google_event.get("eventLabelId")
        g_color = key_for_hex(label_colors.get(label_id)) if label_id else None
        if g_color is not None and g_color != r_color:
            changes["color_key"] = g_color
        elif (
            not label_id
            and not google_event.get("colorId")
            and r_color is not None
            and EVENT_COLORS.get(r_color) in label_colors.values()
        ):
            # Google で色を「なし」に戻した。Google でも表せた色のときだけ外す（ADR-1059 改訂 2026-11-22）
            changes["color_key"] = None
```

`EVENT_COLORS` を `backend/app/services/calendar_service.py` の中で別名で持たない。色の表は `backend/app/services/event_colors.py` の 1 か所だけ。

## 2. `backend/tests/test_calendar_service.py`

`TestUpdateAppOriginFromGoogle` の `test_color_only_when_label_matches`（685-698 行目）は変えない。その直後に次の試験を足す（`_app_origin_db`・`_g_event`・`_updates`・`_T1`・`_T2` は既存のものを使う）。

```python
    @pytest.mark.asyncio
    async def test_color_cleared_when_google_has_no_label(self):
        labels = {"L1": "#d50000"}  # tomato
        row = (5, "題", None, None, _T1, _T2, False, "tomato")
        db = _app_origin_db(row)
        assert await self._go(db, _g_event(), labels) == "upserted"
        (sql, params), = _updates(db)
        assert "color_key = :color_key" in sql.split("SET", 1)[1].split("WHERE", 1)[0]
        assert params["color_key"] is None
        db = _app_origin_db(row)
        assert await self._go(db, _g_event(eventLabelId=""), labels) == "upserted"
        assert _updates(db)[0][1]["color_key"] is None

    @pytest.mark.asyncio
    async def test_color_kept_unless_all_clear_conditions(self):
        tomato = (5, "題", None, None, _T1, _T2, False, "tomato")
        no_color = (5, "題", None, None, _T1, _T2, False, None)
        for row, ev, labels in (
            (tomato, _g_event(), None),                               # 名札の表が読めない
            (tomato, _g_event(colorId="11"), {"L1": "#d50000"}),      # 古い色の番号がある
            (tomato, _g_event(), {"L1": "#0000ff"}),                  # アプリの色が名札の表に無い
            (tomato, _g_event(), {}),                                 # 名札の表が空
            (tomato, _g_event(eventLabelId="L9"), {"L1": "#d50000"}), # 表に無い名札
            (no_color, _g_event(), {"L1": "#d50000"}),                # アプリに色が無い
        ):
            db = _app_origin_db(row)
            assert await self._go(db, ev, labels) == "skipped"
            assert _updates(db) == []
```

## 3. 確かめ（Mac では試験を回さない）

- 試験は GitHub の CI で回る。手元で pytest を流さない。
- `git diff --name-only origin/main...HEAD` が次の 2 本＋設計の docs だけであること: `backend/app/services/calendar_service.py`・`backend/tests/test_calendar_service.py`。
- `ruff check backend/app/services/calendar_service.py backend/tests/test_calendar_service.py` が通ること（入っていれば）。

## 4. commit と push

- commit 1 つ: `fix(calendar): clear app event color when Google label is removed`。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- `git push origin release/calendar-color-clear`。PR は作らない（Opus が作る）。
- 返事は最後の行を `DONE` か `BLOCKED: 理由` にする。diff と push の生出力を添える。
