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

(2) `upsert_from_google` のすぐ上に新しい関数を足す:

```python
async def _update_app_origin_from_google(
    db: AsyncSession,
    tenant_id: int,
    google_event: dict,
    label_colors: Optional[dict[str, str]] = None,
) -> str:
    """アプリで作った予定を Google で直したとき、中身の列だけを入れる（ADR-1059 改訂 2026-11-20）。

    - Google で消されても消さない（"skipped"）。
    - アプリから送り終えた行（sync_status='synced'）で、中身が違うときだけ書く。
    - 見せ方・持ち主・起源・Meet の URL には触らない。Google へは書かない。
    戻り値は "upserted"（1 行以上書いた）か "skipped"。commit は呼び元が行う。
    """
    if google_event.get("status") == "cancelled":
        return "skipped"
    start_raw = google_event.get("start") or {}
    end_raw = google_event.get("end") or {}
    if not (start_raw.get("dateTime") or start_raw.get("date")) or not (
        end_raw.get("dateTime") or end_raw.get("date")
    ):
        return "skipped"
    start_dt, end_dt, is_all_day = _google_times(start_raw, end_raw)

    params: dict = {
        "gid": google_event["id"],
        "title": google_event.get("summary", ""),
        "desc": google_event.get("description"),
        "loc": google_event.get("location"),
        "start": start_dt,
        "end": end_dt,
        "all_day": is_all_day,
    }
    sets = [
        "title = :title",
        "description = :desc",
        "location = :loc",
        "start_datetime = :start",
        "end_datetime = :end",
        "is_all_day = :all_day",
    ]
    diffs = [
        "title IS DISTINCT FROM :title",
        "description IS DISTINCT FROM :desc",
        "location IS DISTINCT FROM :loc",
        "start_datetime IS DISTINCT FROM :start",
        "end_datetime IS DISTINCT FROM :end",
        "is_all_day IS DISTINCT FROM :all_day",
    ]
    if label_colors is not None:
        label_id = google_event.get("eventLabelId")
        params["color_key"] = key_for_hex(label_colors.get(label_id)) if label_id else None
        sets.append("color_key = :color_key")
        diffs.append("color_key IS DISTINCT FROM :color_key")

    res = await db.execute(
        text(
            "UPDATE calendar_events SET "
            + ", ".join(sets)
            + ", last_synced_at = NOW()"
            " WHERE google_event_id = :gid"
            " AND sync_origin_id LIKE 'app:" + str(int(tenant_id)) + ":%'"
            " AND sync_status = 'synced'"
            " AND recurrence_rule IS NULL"
            " AND recurring_event_id IS NULL"
            " AND (" + " OR ".join(diffs) + ")"
        ),
        params,
    )
    return "upserted" if (res.rowcount or 0) > 0 else "skipped"
```

SET に `calendar_type`・`user_id`・`created_by_user_id`・`source`・`sync_origin_id`・`sync_status`・`meet_url`・`google_event_id` を入れない。

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

- 既存の `test_skips_app_origin` は、今の「飛ばす」を確かめている。中身を次に変える（名前も `test_app_origin_updates_content_only` に変える）: `_is_app_origin` が真の予定で、UPDATE が 1 回だけ流れ、その SQL に `sync_status = 'synced'`・`IS DISTINCT FROM`・`recurrence_rule IS NULL` が入り、SET の部分に `calendar_type`・`user_id`・`source`・`sync_origin_id`・`meet_url` が入らないこと、`rowcount=1` なら `"upserted"` を返すこと（K7）。
- 足す試験（同じクラスか近くに。DB は今の試験と同じモックの形で）:
  1. `rowcount=0` なら `"skipped"`（K6・K8：送る途中の行・中身が同じ行は UPDATE の WHERE で外れる）。
  2. アプリ起源で `status="cancelled"` なら UPDATE も DELETE も流れず `"skipped"`（K9）。
  3. `label_colors=None` のとき SQL に `color_key` が入らない。`label_colors` があるとき `eventLabelId` から `color_key` を入れる（K2）。
  4. 終日（`start.date="2026-11-21"`・`end.date="2026-11-22"`）のとき、`start` が 2026-11-21 00:00 JST・`end` が 2026-11-21 23:59 JST・`all_day=True` で渡る。
  5. 取り込みが Google へ書かない（K5）: `app.services.google_calendar` の `create_event`・`update_event`・`delete_event` を、呼ばれたら落ちる偽物に差し替えて、アプリ起源と Google 起源の両方の `upsert_from_google` を呼んでも落ちない。
  6. 既存の `test_instance_of_app_origin_is_skipped` は、判定の順が変わったので `_is_app_origin` の side_effect の並びが合わなくなる。繰り返しの回の判定が先になったことに合わせて並びだけ直す（確かめる中身＝「アプリで作った繰り返しの回は "skipped"」は変えない）。
- `sync_tenant_from_google` の試験（同じファイルの既存の形に合わせる）:
  7. `upsert_from_google` が 1 件 `"upserted"` を返すとき `publish_change` が `("calendar.events", "tenant", <tenant_id>)` で 1 回呼ばれる（K11）。
  8. 全部 `"skipped"` のとき `publish_change` は呼ばれない（K11）。

### backend/tests/test_realtime_topics.py

- `test_frontend_topic_names_match_backend` の集合に `| set(TENANT_TASK_TOPICS)` を足す（読み込みも足す）。
- 足す: `test_tenant_task_topics_are_tenant_only`（`TENANT_TASK_TOPICS` の範囲が全部 `SCOPE_TENANT`）。

### frontend

- `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`（または近くの予定の画面の試験）に 1 本足す（K12）: `useRealtimeRefresh` を偽物にして、`[TOPICS.calendarEvents]` で呼ばれ、渡された関数を呼ぶと `["calendar", "events"]` の読み直しが走ることを確かめる。今の試験の偽物の作り方に合わせる。合わせ方が分からなければ止めて NEEDS_DECISION。

## 7. 走らせる確かめ（生の出力をファイルに残し、最後の数行を報告に貼る）

- `cd backend && python -m pytest tests/test_calendar_service.py tests/test_realtime_topics.py -q`
- `cd frontend && npx vitest run src/pages/schedule src/hooks/useRealtimeRefresh.test.tsx`
- `cd frontend && npx tsc --noEmit -p .` と `npx eslint src/pages/schedule/SchedulePageImpl.tsx src/lib/realtime/topics.ts`
- 効き目の確かめ: `_update_app_origin_from_google` の WHERE から `AND sync_status = 'synced'` を一時的に外すと試験が落ちること（確かめたら元に戻す）。

## 8. 触らないもの

design.md §3-5 のとおり。migration・deploy.yml・本番 scripts/ は触らない。ほかのファイルを直したくなったら止めて NEEDS_DECISION。

## 9. 終わり方

- commit は 1 つか 2 つ。メッセージの終わりに `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push origin release/calendar-two-way-sync`（force しない）。PR は作らない。
- 最後の 1 行を `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <理由>` のどれかにする。
