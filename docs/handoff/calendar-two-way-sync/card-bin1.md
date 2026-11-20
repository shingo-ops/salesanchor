# 実装カード 便1: 予定の中身を Google とアプリの両方向でそろえる

- 設計: docs/handoff/calendar-two-way-sync/design.md（§3 が変更の正・§2 が受け入れ）
- 現在地: docs/handoff/calendar-two-way-sync/recon.md
- ブランチ: release/calendar-two-way-sync（この枝の上で作業する。main へは入れない）
- 区分: 実装役は書いてあることだけをする。迷ったら止めて「NEEDS_DECISION: <理由>」で返す。

## 0. 始める前の点検（実物で確かめ、違えば止める）

1. `backend/app/services/calendar_service.py` に `async def upsert_from_google(` があり、その中で `if await _is_app_origin(db, google_event_id, tenant_id):` の次に `recurring_event_id = google_event.get("recurringEventId")` と `if recurring_event_id and await _is_app_origin(db, recurring_event_id, tenant_id):` がある。
2. 同じファイルに `def _google_times(` と `key_for_hex` の読み込みがある。
3. `backend/app/services/google_webhook.py` の `sync_tenant_from_google` に `await db.commit()` → `await reset_tenant_context(db, tenant_id)` → `logger.info("Google 取り込み完了` の並びがある。
4. `backend/app/realtime/topics.py` に `TASK_TOPICS: dict[str, str] = {` がある。`frontend/src/lib/realtime/topics.ts` に `notices: "notices",` がある。
5. `frontend/src/pages/schedule/SchedulePageImpl.tsx` に `const invalidate = useInvalidateApi();` が 1 か所ある。

## 1. backend/app/services/calendar_service.py

(1) `upsert_from_google` の頭の判定の順を変える。変更後:

```python
    google_event_id = google_event.get("id")
    if not google_event_id:
        return "skipped"

    # アプリで作った繰り返しの回は飛ばす（ADR-1075 決定6）
    recurring_event_id = google_event.get("recurringEventId")
    if recurring_event_id and await _is_app_origin(db, recurring_event_id, tenant_id):
        return "skipped"

    # アプリで作った予定は、中身の列だけを入れる（ADR-1059 改訂 2026-11-20）
    if await _is_app_origin(db, google_event_id, tenant_id):
        return await _update_app_origin_from_google(
            db, tenant_id, google_event, label_colors=label_colors
        )
```

それより下（消された予定の処理・INSERT ON CONFLICT）は 1 文字も変えない。docstring の「無限ループ防止」の 2 行は次に置き換える:
「アプリ起源（sync_origin_id が "app:tenant_id:" で始まる）の予定は _update_app_origin_from_google で中身の列だけを UPDATE する。取り込みは DB にだけ書き Google へは書かないので、行ったり来たりは起きない。」

(2) `upsert_from_google` のすぐ上に新しい関数を足す（再審査の指摘 B3・B4 を受け、1 本の UPDATE ではなく「行を読む → Python で比べる → 違う列だけ UPDATE」にした）:

```python
def _norm_text(value: Optional[str]) -> str:
    """説明・場所の比べ方: 空と NULL は同じ。改行は \n にそろえる（Google の正規化で毎回差が出ないように）。"""
    return (value or "").replace("\r\n", "\n")


def _same_times(row_start, row_end, row_all_day: bool, g_start: dict, g_end: dict) -> bool:
    """アプリの行の時間と Google の時間が同じか。終日はアプリが Google へ送る日付の形で比べる。"""
    google_all_day = "date" in g_start
    if bool(row_all_day) != google_all_day:
        return False
    if google_all_day:
        sent = _to_google_event_body(
            {
                "start_datetime": row_start.isoformat(),
                "end_datetime": row_end.isoformat(),
                "is_all_day": True,
            }
        )
        return sent["start"] == {"date": g_start["date"]} and sent["end"] == {"date": g_end["date"]}
    g_s, g_e, _ = _google_times(g_start, g_end)
    return row_start == g_s and row_end == g_e


async def _update_app_origin_from_google(
    db: AsyncSession,
    tenant_id: int,
    google_event: dict,
    label_colors: Optional[dict[str, str]] = None,
) -> str:
    """アプリで作った予定を Google で直したとき、中身の列だけを入れる（ADR-1059 改訂 2026-11-20）。

    - Google で消されても消さない（"skipped"）。
    - アプリから送り終えた行（sync_status='synced'）で、中身が違う列だけを書く。
    - 見せ方・持ち主・起源・Meet の URL には触らない。Google へは書かない。
    - 色は Google の名札がアプリの色に当たるときだけ入れる（名札が無い・表に無いときは触らない）。
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
        label_id = google_event.get("eventLabelId")
        g_color = key_for_hex(label_colors.get(label_id)) if label_id else None
        if g_color is not None and g_color != r_color:
            changes["color_key"] = g_color

    if not changes:
        return "skipped"
    sets = ", ".join(f"{col} = :{col}" for col in changes)
    res = await db.execute(
        text(
            f"UPDATE calendar_events SET {sets}, last_synced_at = NOW()"
            " WHERE id = :id AND sync_status = 'synced'"
        ),
        {**changes, "id": row_id},
    )
    return "upserted" if (res.rowcount or 0) > 0 else "skipped"
```

列の名前は `changes` の鍵（上の 7 つの固定の文字）だけから作る。外から来た文字を SQL に入れない。UPDATE の `sync_status = 'synced'` は、読んでから書くまでにアプリで直された行（`pending` になる）を上書きしないための再確認。

SET に `calendar_type`・`user_id`・`created_by_user_id`・`source`・`sync_origin_id`・`sync_status`・`meet_url`・`google_event_id` を入れない。

(3) `_to_google_event_body` の説明・場所の送り方を直す（審査の指摘 A: アプリで空にしても Google の古い値が残り、取り込みで戻ってしまう）。変更前:

```python
    if payload.get("description"):
        body["description"] = payload["description"]
    if payload.get("location"):
        body["location"] = payload["location"]
```

変更後（鍵が payload にあれば、空でも送る。空は "" で送り Google 側も消す。鍵が無ければ今と同じく送らない）:

```python
    # 鍵があれば空でも送る（アプリで消したら Google でも消す・ADR-1059 改訂 2026-11-20）
    if "description" in payload:
        body["description"] = payload["description"] or ""
    if "location" in payload:
        body["location"] = payload["location"] or ""
```

ほかの行は変えない。

## 2. backend/app/services/google_webhook.py

`sync_tenant_from_google` の `await reset_tenant_context(db, tenant_id)`（commit の直後の方）と `logger.info("Google 取り込み完了` の間に足す:

```python
        # 予定の画面へ合図（ADR-1016 改訂 2026-11-20）。書いた件数が 0 なら出さない。失敗は握られる
        if upserted + deleted > 0:
            from app.realtime.publisher import publish_change
            from app.realtime.topics import SCOPE_TENANT, TOPIC_CALENDAR_EVENTS

            await publish_change(TOPIC_CALENDAR_EVENTS, SCOPE_TENANT, tenant_id)
```

（読み込みを関数の中に置くのは、ファイルの頭の読み込みの並びを変えないため。ファイルの頭で既に読み込んでいる形なら、頭に足してもよい。）

## 3. backend/app/realtime/topics.py

- `TOPIC_NOTICES = "notices"` の次の行に `TOPIC_CALENDAR_EVENTS = "calendar.events"` を足す。
- `TASK_TOPICS` の閉じかっこの次（空行のあと）に足す:

```python
# 会社の分かる裏の処理が出す topic → 範囲（ADR-1016 改訂 2026-11-20）。範囲は tenant だけ（試験で固定）。
# calendar.events の送り口は services/google_webhook.py の sync_tenant_from_google の 1 か所
TENANT_TASK_TOPICS: dict[str, str] = {
    TOPIC_CALENDAR_EVENTS: SCOPE_TENANT,
}
```

## 4. frontend/src/lib/realtime/topics.ts

`notices: "notices",` の次の行に `calendarEvents: "calendar.events",` を足す。

## 5. frontend/src/pages/schedule/SchedulePageImpl.tsx

- 読み込みに `import { useRealtimeRefresh } from "../../hooks/useRealtimeRefresh";` と `import { TOPICS } from "../../lib/realtime/topics";` を足す（既にあれば足さない）。
- `const invalidate = useInvalidateApi();` の次の行に足す:

```tsx
  // Google からの取り込みで予定が変わったら読み直す（ADR-1016 改訂 2026-11-20）。保存の後と同じ頭で読み直す
  useRealtimeRefresh([TOPICS.calendarEvents], () => {
    void invalidate(["calendar", "events"]);
  });
```

画面の見た目・文字・色は変えない（t() の鍵もデザイントークンも足さない）。

## 6. 試験

### backend/tests/test_calendar_service.py

- 既存の `test_skips_app_origin` は、今の「飛ばす」を確かめている。中身を次に変える（名前も `test_app_origin_updates_content_only` に変える）: `_is_app_origin` が真、SELECT が 1 行（題名だけ違う）を返す予定で、2 本目の SQL が `UPDATE` で、SET に `title` だけが入り `calendar_type`・`user_id`・`source`・`sync_origin_id`・`meet_url` が入らず、WHERE に `sync_status = 'synced'` があること。`rowcount=1` なら `"upserted"`（K7）。
- 足す試験（同じクラスか近くに。DB は今の試験と同じモックの形で）:
  1. SELECT の WHERE に `sync_status = 'synced'`・`recurrence_rule IS NULL`・`recurring_event_id IS NULL` があり、行が無ければ UPDATE は流れず `"skipped"`（K6）。UPDATE の `rowcount=0` でも `"skipped"`。
  2. アプリ起源で `status="cancelled"` なら SELECT も UPDATE も DELETE も流れず `"skipped"`（K9）。
  3. 中身が全部同じなら UPDATE は流れず `"skipped"`（K8）。この試験の「同じ」は: 題名同じ・DB の説明が `""` で Google に鍵なし・DB の場所が `"a\r\nb"` で Google が `"a\nb"`・時間同じ。
  4. 終日の比べ方（K8・指摘 B4）: DB が開始 2026-11-21 00:00 JST・終了 2026-11-21 23:59 JST の行と、DB が開始 2026-11-21 00:00 JST・終了 2026-11-22 00:00 JST の行の 2 つで、それぞれ `_to_google_event_body` が作る日付と同じ Google の値（`start.date`・`end.date`）を返したとき、どちらも UPDATE は流れない。Google が 1 日のばした値なら、`start_datetime`・`end_datetime`・`is_all_day` が UPDATE に入り、値は `_google_times` の形（終了日 23:59 JST）。
  5. 色（K2・指摘 B3）: `label_colors` に名札があり当たる鍵が DB と違えば `color_key` が入る。`label_colors=None`・`eventLabelId` 無し・表に無い名札、の 3 つでは `color_key` が UPDATE に入らない（DB に色があっても消さない）。
  6. 取り込みが Google へ書かない（K5）: `app.services.google_calendar` の `create_event`・`update_event`・`delete_event` を、呼ばれたら落ちる偽物に差し替えて、アプリ起源と Google 起源の両方の `upsert_from_google` を呼んでも落ちない。
  7. 時刻ありの予定で、DB と Google が同じ時刻を別の時差の書き方（`+09:00` と `Z`）で持つとき UPDATE は流れない。
  8. `TestToGoogleEventBody` に足す: `description=""`・`location=None` を鍵ありで渡すと `body["description"] == ""`・`body["location"] == ""`。既存の `test_without_description_and_location`（鍵なし→送らない）はそのまま通ること。
  9. 既存の `test_instance_of_app_origin_is_skipped`（`:1939` 付近）は、判定の順が変わり最初の `_is_app_origin` の呼び出しが親の `"gm"` になる。`AsyncMock(side_effect=[False, True])` を `AsyncMock(side_effect=[True])` に、`origin.await_args_list[1].args[1] == "gm"` を `origin.await_args_list[0].args[1] == "gm"` に変える（確かめる中身＝「アプリで作った繰り返しの回は "skipped"」は変えない）。
- `sync_tenant_from_google` の試験（同じファイルの既存の形に合わせる）:
  - 先に、既存の `_sync_patches`（`:852` 付近）の patch の並びに `patch("app.realtime.publisher.publish_change", new=AsyncMock())` を足す（既存の試験が本物の Redis へ送りに行かないように・指摘 B1）。下の 10・11 はこの偽物で数える。
  10. `upsert_from_google` が 1 件 `"upserted"` を返すとき `publish_change` が `("calendar.events", "tenant", <tenant_id>)` で 1 回呼ばれる（K11）。
  11. 全部 `"skipped"` のとき `publish_change` は呼ばれない（K11）。

### backend/tests/test_realtime_topics.py

- `test_frontend_topic_names_match_backend` の集合に `| set(TENANT_TASK_TOPICS)` を足す（読み込みも足す）。
- 足す: `test_tenant_task_topics_are_tenant_only`（`TENANT_TASK_TOPICS` の範囲が全部 `SCOPE_TENANT`）。

### frontend

- `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`（または近くの予定の画面の試験）に 1 本足す（K12）: `useRealtimeRefresh` を偽物にして、`[TOPICS.calendarEvents]` で呼ばれ、渡された関数を呼ぶと `["calendar", "events"]` の読み直しが走ることを確かめる。今の試験の偽物の作り方に合わせる。合わせ方が分からなければ止めて NEEDS_DECISION。

## 7. 走らせる確かめ（生の出力をファイルに残し、最後の数行を報告に貼る）

- `cd backend && python -m pytest tests/test_calendar_service.py tests/test_realtime_topics.py -q`
- `cd frontend && npx vitest run src/pages/schedule src/hooks/useRealtimeRefresh.test.tsx`
- `cd frontend && npx tsc --noEmit -p .` と `npx eslint src/pages/schedule/SchedulePageImpl.tsx src/lib/realtime/topics.ts`
- 効き目の確かめ: `_update_app_origin_from_google` の SELECT の WHERE から `AND sync_status = 'synced'` を一時的に外すと試験 1 が落ちること。`_same_times` を常に False にすると試験 3・4 が落ちること（確かめたら元に戻す）。

## 8. 触らないもの

design.md §3-5 のとおり。migration・deploy.yml・本番 scripts/ は触らない。ほかのファイルを直したくなったら止めて NEEDS_DECISION。

## 9. 終わり方

- commit は 1 つか 2 つ。メッセージの終わりに `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push origin release/calendar-two-way-sync`（force しない）。PR は作らない。
- 最後の 1 行を `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <理由>` のどれかにする。
