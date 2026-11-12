from __future__ import annotations

"""
アプリ内カレンダーサービス。

担当範囲:
  - calendar_events テーブルの CRUD（テナントスキーマ）
  - Google Calendar との双方向同期ロジック
    - App → Google: イベント作成/更新/削除時に Google Calendar API を呼び出し
    - Google → App: Webhook 受信時の upsert（upsert_from_google）
  - 無限ループ防止: sync_origin_id による起源判定

設計判断:
  - calendar_events はテナントスキーマに配置（get_current_tenant で search_path 設定済み）
  - Google Calendar API は google_calendar サービスに委譲
  - sync_mode に応じて Google 同期の有無を切り替え
"""

import asyncio
import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import reset_tenant_context
from app.services import calendar_recurrence as rec

logger = logging.getLogger(__name__)


def _parse_dt(s: str) -> datetime:
    """ISO 8601 文字列を datetime に変換する。

    URL クエリパラメータで '+09:00' がスペースに変換されるケース（例: '2026-06-07T00:00:00 09:00'）も対処する。
    """
    return datetime.fromisoformat(s.replace(" ", "+"))


# ---------------------------------------------------------------------------
# 内部ヘルパー
# ---------------------------------------------------------------------------


async def _get_sync_mode(db: AsyncSession, tenant_id: int) -> str:
    """テナントの同期モードを返す。Google 未接続の場合は 'none' を返す。"""
    row = await db.execute(
        text(
            "SELECT sync_mode FROM tenant_google_calendar_config WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    record = row.first()
    return record[0] if record else "none"


async def _get_sync_target(db: AsyncSession, tenant_id: int) -> tuple[str, Optional[int]]:
    """同期モードと、Google をつないだ人の user_id を返す。未接続は ('none', None)。"""
    row = await db.execute(
        text(
            "SELECT sync_mode, connected_by_user_id FROM tenant_google_calendar_config"
            " WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    record = row.first()
    return (record[0], record[1]) if record else ("none", None)


async def can_add_meet(db: AsyncSession, tenant_id: int, user_id: int) -> bool:
    """この人の予定を Google に送れるか（= Google Meet を付けてよいか）。

    送る方式（bidirectional / write_only）で、Google をつないだ本人だけ真。
    予定を Google に送る条件と Meet を付けてよい条件は同じ式なので 1 か所に置く。
    """
    sync_mode, connected_by = await _get_sync_target(db, tenant_id)
    return sync_mode in ("bidirectional", "write_only") and connected_by == user_id


def _meet_create_request() -> dict:
    """Google に Meet を作らせる頼み。requestId は毎回新しい値にする（頼み直しのため）。"""
    return {
        "createRequest": {
            "requestId": uuid.uuid4().hex,
            "conferenceSolutionKey": {"type": "hangoutsMeet"},
        }
    }


async def _resolve_meet_url(db: AsyncSession, tenant_id: int, google_event: dict) -> Optional[str]:
    """Google の返事から Meet の URL を取り出す。作成が pending なら 1 秒おきに 2 回まで読み直す。

    取れなければ None（予定そのものは保存済みなので失敗にはしない）。
    """
    url = google_event.get("hangoutLink")
    if url:
        return url
    status_code = (
        ((google_event.get("conferenceData") or {}).get("createRequest") or {})
        .get("status", {})
        .get("statusCode")
    )
    google_event_id = google_event.get("id")
    if status_code == "pending" and google_event_id:
        from app.services import google_calendar as gcal

        for _ in range(2):
            await asyncio.sleep(1)
            try:
                reread = await gcal.get_event(db, tenant_id, google_event_id)
            except Exception as e:
                logger.warning("Google Meet の読み直しに失敗 (google_event_id=%s): %s", google_event_id, e)
                break
            if reread.get("hangoutLink"):
                return reread["hangoutLink"]
    logger.warning("Google Meet の URL を取得できませんでした (google_event_id=%s)", google_event_id)
    return None


def _build_sync_origin_id(tenant_id: int, calendar_event_id: int) -> str:
    """アプリ起源のイベントを識別する sync_origin_id を生成する。
    Webhook 受信時にこの値が存在するイベントはスキップして無限ループを防止する。
    """
    return f"app:{tenant_id}:{calendar_event_id}"


async def _is_app_origin(
    db: AsyncSession, google_event_id: str, tenant_id: int
) -> bool:
    """google_event_id がアプリ起源かどうかを判定する（無限ループ防止）。"""
    row = await db.execute(
        text(
            "SELECT 1 FROM calendar_events"
            " WHERE google_event_id = :gid"
            " AND sync_origin_id LIKE 'app:" + str(tenant_id) + ":%'"
            " LIMIT 1"
        ),
        {"gid": google_event_id},
    )
    return row.first() is not None


# 予定 1 行の読み方（受け口の持ち主の確かめ・繰り返しの判定・3 択の処理で同じ並びを使う）
EVENT_COLUMNS = (
    "created_by_user_id", "calendar_type", "user_id", "google_event_id", "meet_url",
    "id", "source", "recurrence_rule", "recurring_event_id", "original_start_datetime",
    "start_datetime", "end_datetime", "is_all_day", "is_cancelled",
    "title", "description", "location", "category",
)
EVENT_COLUMNS_SQL = ", ".join(EVENT_COLUMNS)


def event_from_row(row) -> dict:
    return {name: row[i] for i, name in enumerate(EVENT_COLUMNS)}


async def read_event(db: AsyncSession, event_id: int) -> Optional[dict]:
    row = await db.execute(
        text(f"SELECT {EVENT_COLUMNS_SQL} FROM calendar_events WHERE id = :id"),
        {"id": event_id},
    )
    record = row.first()
    return event_from_row(record) if record else None


def _google_body_for(ev: dict) -> dict:
    """表の 1 行（直した後の値）から Google の本文を作る。元の行なら recurrence を付ける（§12.7）。"""
    payload = {
        "title": ev.get("title") or "",
        "description": ev.get("description"),
        "location": ev.get("location"),
        "start_datetime": ev["start_datetime"].isoformat(),
        "end_datetime": ev["end_datetime"].isoformat(),
        "is_all_day": bool(ev.get("is_all_day")),
    }
    body = _to_google_event_body(payload)
    if ev.get("recurrence_rule"):
        body["recurrence"] = rec.google_recurrence(ev["recurrence_rule"])
    return body


# ---------------------------------------------------------------------------
# イベント一覧取得
# ---------------------------------------------------------------------------


async def list_events(
    db: AsyncSession,
    tenant_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    calendar_type: Optional[str] = None,
    user_id: Optional[int] = None,
    title_query: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    """期間・タイプでカレンダーイベントを取得する。

    calendar_type が 'shared' の場合は全ユーザーのイベント。
    calendar_type が 'personal' の場合は user_id のイベントのみ。
    どの指定でも、他人の 'personal' は返さない（'shared' か user_id 本人の予定だけ）。
    title_query は題名の部分一致（%・_・\\ は文字として扱う）。指定時は新しい順・limit 件まで。
    """
    filters: list[str] = []
    params: dict = {}
    # 期間の始まりと終わりの両方があり探すのでないとき、繰り返しの元の行を回に広げる（ADR-1075 §12.5）
    expand_recurring = start is not None and end is not None and title_query is None
    if end is not None:
        if not expand_recurring:
            filters.append("start_datetime < :end")
        params["end"] = _parse_dt(end)
    if start is not None:
        if not expand_recurring:
            filters.append("end_datetime > :start")
        params["start"] = _parse_dt(start)

    type_filters: list[str] = []
    if calendar_type == "shared":
        type_filters.append("calendar_type = 'shared'")
    elif calendar_type == "personal" and user_id:
        type_filters.append("calendar_type = 'personal'")
        type_filters.append("user_id = :uid")
        params["uid"] = user_id
    filters.extend(type_filters)

    where = " AND ".join(f"ce.{f}" for f in filters) or "TRUE"
    if expand_recurring:
        where += (
            " AND ((ce.start_datetime < :end AND ce.end_datetime > :start AND ce.recurrence_rule IS NULL)"
            " OR (ce.recurrence_rule IS NOT NULL AND ce.start_datetime < :end))"
        )
    # 見せ方の絞り: 他人の「自分だけ」予定は常に返さない
    if user_id is None:
        visibility_sql = "ce.calendar_type = 'shared'"
    else:
        visibility_sql = "(ce.calendar_type = 'shared' OR ce.user_id = :me)"
        params["me"] = user_id
    where += f" AND {visibility_sql}"
    where += " AND NOT ce.is_cancelled"
    if title_query is not None:
        escaped = title_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where += " AND ce.title ILIKE :title_q ESCAPE '\\'"
        params["title_q"] = f"%{escaped}%"
    if limit is not None:
        params["limit"] = limit
    result = await db.execute(
        text(
            f"SELECT ce.id, ce.user_id, ce.calendar_type, ce.category, ce.title, ce.description, ce.location,"
            f" ce.start_datetime, ce.end_datetime, ce.is_all_day, ce.google_event_id, ce.source,"
            f" ce.sync_status, ce.created_by_user_id, ce.created_at, ce.updated_at,"
            f" TRIM(COALESCE(owner.surname_jp,'') || ' ' || COALESCE(owner.given_name_jp,'')) AS owner_name,"
            f" TRIM(COALESCE(created.surname_jp,'') || ' ' || COALESCE(created.given_name_jp,'')) AS created_by_name,"
            f" ce.meet_url,"
            f" ce.recurrence_rule, ce.recurring_event_id, ce.original_start_datetime"
            f" FROM calendar_events ce"
            f" LEFT JOIN public.users owner_user ON owner_user.id = ce.user_id"
            f" LEFT JOIN staff owner ON owner.user_id = owner_user.id"
            f" LEFT JOIN public.users created_user ON created_user.id = ce.created_by_user_id"
            f" LEFT JOIN staff created ON created.user_id = created_user.id"
            f" WHERE {where}"
            f" ORDER BY ce.start_datetime{' DESC' if title_query is not None else ''}"
            f"{' LIMIT :limit' if limit is not None else ''}"
        ),
        params,
    )
    rows = result.fetchall()

    def _item(r) -> dict:
        return {
            "id": r[0],
            "user_id": r[1],
            "calendar_type": r[2],
            "category": r[3],
            "title": r[4],
            "description": r[5],
            "location": r[6],
            "start_datetime": r[7].isoformat() if r[7] else None,
            "end_datetime": r[8].isoformat() if r[8] else None,
            "is_all_day": r[9],
            "google_event_id": r[10],
            "source": r[11],
            "sync_status": r[12],
            "created_by_user_id": r[13],
            "created_at": r[14].isoformat() if r[14] else None,
            "updated_at": r[15].isoformat() if r[15] else None,
            "owner_name": r[16] or None,
            "created_by_name": r[17] or None,
            "meet_url": r[18],
            "recurrence_rule": r[19],
            "recurrence": rec.rule_to_recurrence(r[19]),
            "recurring_event_id": r[20],
            "occurrence_start": r[21].isoformat() if r[20] is not None and r[21] else None,
            "is_first_occurrence": bool(r[19]) and r[20] is None,
        }

    masters = [r for r in rows if r[19]]
    master_rules: dict = {r[0]: r[19] for r in masters}
    # 1 回目かの判定に使う元の行の始まりと終日（design §12.6.1 G1）
    master_starts: dict = {r[0]: (r[7], bool(r[9])) for r in masters}
    exception_rows = [r for r in rows if r[20] is not None]
    # 例外の行の recurrence と 1 回目かは元の行から決める。同じ結果に元の行が無いときだけ 1 本で引く
    missing_ids = sorted({r[20] for r in exception_rows if r[20] not in master_rules})
    if missing_ids:
        found = await db.execute(
            text("SELECT id, recurrence_rule, start_datetime, is_all_day FROM calendar_events WHERE id = ANY(:ids)"),
            {"ids": missing_ids},
        )
        for mid, mrule, mstart, mall_day in found.fetchall():
            master_rules[mid] = mrule
            master_starts[mid] = (mstart, bool(mall_day))

    items: list[dict] = []
    for r in rows:
        if expand_recurring and r[19]:
            continue
        item = _item(r)
        if r[20] is not None:
            item["recurrence"] = rec.rule_to_recurrence(master_rules.get(r[20]))
            ms = master_starts.get(r[20])
            item["is_first_occurrence"] = bool(
                ms and ms[0] and r[21] and rec.is_first_occurrence(ms[0], ms[1], r[21])
            )
        items.append(item)

    if not expand_recurring:
        return items

    if masters:
        # 例外の行（消した印も含む）を期間に関係なく 1 本で引き、広げた回から外す
        exc_params: dict = {"ids": [r[0] for r in masters]}
        for key in ("me", "uid"):
            if key in params:
                exc_params[key] = params[key]
        exc_where = " AND ".join(
            ["ce.recurring_event_id = ANY(:ids)", visibility_sql]
            + [f"ce.{f}" for f in type_filters]
        )
        exc_result = await db.execute(
            text(
                "SELECT ce.recurring_event_id, ce.original_start_datetime"
                f" FROM calendar_events ce WHERE {exc_where}"
            ),
            exc_params,
        )
        excluded = {
            (mid, orig.astimezone(timezone.utc))
            for mid, orig in exc_result.fetchall()
            if orig is not None
        }
        for r in masters:
            m_start, m_end = r[7], r[8]
            duration = m_end - m_start
            all_day = bool(r[9])
            for occ in rec.expand(r[19], m_start, duration, all_day, params["start"], params["end"]):
                key = (r[0], rec.occurrence_of(m_start, all_day, occ).astimezone(timezone.utc))
                if key in excluded:
                    continue
                item = _item(r)
                item["start_datetime"] = occ.isoformat()
                item["end_datetime"] = (occ + duration).isoformat()
                item["recurring_event_id"] = r[0]
                item["occurrence_start"] = occ.isoformat()
                item["is_first_occurrence"] = rec.is_first_occurrence(m_start, all_day, occ)
                items.append(item)

    def _sort_key(item: dict) -> datetime:
        value = item.get("start_datetime")
        if not value:
            return datetime.min.replace(tzinfo=timezone.utc)
        return rec.to_jst(datetime.fromisoformat(value))

    items.sort(key=_sort_key)
    return items


# ---------------------------------------------------------------------------
# イベント作成
# ---------------------------------------------------------------------------


async def create_event(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: dict,
) -> dict:
    """アプリ内にイベントを作成し、Google Calendar に同期する。

    同期モードが 'bidirectional' または 'write_only' で、Google をつないだ本人が作った予定だけ Google に送信する。
    """
    # 繰り返しの決まり（選べない値は受け口が先に 422 で止めている）
    recurrence_rule = rec.build_rule(
        payload.get("recurrence") or "none", _parse_dt(payload["start_datetime"])
    )
    # DB に保存（sync_status='pending' で開始）
    result = await db.execute(
        text(
            "INSERT INTO calendar_events"
            " (user_id, calendar_type, category, title, description, location,"
            "  start_datetime, end_datetime, is_all_day, source, sync_status,"
            "  created_by_user_id, recurrence_rule)"
            " VALUES"
            " (:uid, :ctype, :category, :title, :desc, :loc,"
            "  :start, :end, :all_day, 'app', 'pending',"
            "  :cuid, :rrule)"
            " RETURNING id"
        ),
        {
            "rrule": recurrence_rule,
            "uid": user_id,
            "ctype": payload.get("calendar_type", "shared"),
            "category": payload.get("category", "meeting"),
            "title": payload["title"],
            "desc": payload.get("description"),
            "loc": payload.get("location"),
            "start": _parse_dt(payload["start_datetime"]),
            "end": _parse_dt(payload["end_datetime"]),
            "all_day": payload.get("is_all_day", False),
            "cuid": user_id,
        },
    )
    event_id = result.scalar_one()
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072: commit 後は別接続になりうる。設定表は RLS（ADR-1018）

    # Google Calendar に同期
    meet_url: Optional[str] = None
    # 接続は会社で1つ。つないだ人が作った予定だけ送り、ほかの人の予定はその人の Google に入れない（PO 2026-11-02）
    if await can_add_meet(db, tenant_id, user_id):
        try:
            from app.services import google_calendar as cal_svc

            google_body = _to_google_event_body(payload)
            if recurrence_rule:
                google_body["recurrence"] = rec.google_recurrence(recurrence_rule)
            if payload.get("add_meet"):
                google_body["conferenceData"] = _meet_create_request()
                google_event = await cal_svc.create_event(
                    db, tenant_id, google_body, conference=True
                )
                meet_url = await _resolve_meet_url(db, tenant_id, google_event)
            else:
                google_event = await cal_svc.create_event(db, tenant_id, google_body)
            google_event_id = google_event.get("id")

            origin_id = _build_sync_origin_id(tenant_id, event_id)
            await db.execute(
                text(
                    "UPDATE calendar_events"
                    " SET google_event_id = :gid, sync_origin_id = :oid,"
                    "     sync_status = 'synced', last_synced_at = NOW(),"
                    "     meet_url = :meet_url"
                    " WHERE id = :id"
                ),
                {"gid": google_event_id, "oid": origin_id, "id": event_id, "meet_url": meet_url},
            )
            await db.commit()
        except Exception as e:
            logger.warning("Google Calendar 同期に失敗しました (event_id=%s): %s", event_id, e)
            await db.execute(
                text(
                    "UPDATE calendar_events SET sync_status = 'failed' WHERE id = :id"
                ),
                {"id": event_id},
            )
            await db.commit()
            meet_url = None

    return {"id": event_id, "meet_url": meet_url}


# ---------------------------------------------------------------------------
# イベント更新
# ---------------------------------------------------------------------------


async def update_event(
    db: AsyncSession,
    tenant_id: int,
    event_id: int,
    user_id: int,
    payload: dict,
) -> dict:
    """アプリ内のイベントを更新し、Google Calendar に同期する。"""
    # DB 更新
    set_clauses = []
    params: dict = {"id": event_id}

    field_map = {
        "title": "title",
        "description": "description",
        "location": "location",
        "start_datetime": "start_datetime",
        "end_datetime": "end_datetime",
        "is_all_day": "is_all_day",
        "calendar_type": "calendar_type",
        "user_id": "user_id",
    }
    for k, col in field_map.items():
        if k in payload:
            set_clauses.append(f"{col} = :{k}")
            if k in ("start_datetime", "end_datetime"):
                params[k] = _parse_dt(payload[k])
            else:
                params[k] = payload[k]

    add_meet = bool(payload.get("add_meet"))
    if not set_clauses:
        if add_meet:
            return await _attach_meet_only(db, tenant_id, event_id)
        return {"id": event_id, "meet_url": None}

    set_clauses.append("sync_status = 'pending'")
    set_sql = ", ".join(set_clauses)
    await db.execute(
        text(f"UPDATE calendar_events SET {set_sql} WHERE id = :id"),
        params,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    # Google Calendar に同期
    row = await db.execute(
        text("SELECT google_event_id, meet_url FROM calendar_events WHERE id = :id"),
        {"id": event_id},
    )
    record = row.first()
    google_event_id = record[0] if record else None
    meet_url: Optional[str] = record[1] if record is not None and len(record) > 1 else None

    sync_mode = await _get_sync_mode(db, tenant_id)
    if google_event_id and sync_mode in ("bidirectional", "write_only"):
        try:
            from app.services import google_calendar as cal_svc

            google_body = _to_google_event_body(payload)
            if add_meet and not meet_url:
                google_body["conferenceData"] = _meet_create_request()
                google_event = await cal_svc.update_event(
                    db, tenant_id, google_event_id, google_body, conference=True
                )
                meet_url = await _resolve_meet_url(db, tenant_id, google_event)
                if meet_url:
                    await db.execute(
                        text("UPDATE calendar_events SET meet_url = :url WHERE id = :id"),
                        {"url": meet_url, "id": event_id},
                    )
            else:
                await cal_svc.update_event(db, tenant_id, google_event_id, google_body)
            await db.execute(
                text(
                    "UPDATE calendar_events"
                    " SET sync_status = 'synced', last_synced_at = NOW()"
                    " WHERE id = :id"
                ),
                {"id": event_id},
            )
            await db.commit()
            await reset_tenant_context(db, tenant_id)
        except Exception as e:
            logger.warning("Google Calendar 更新同期に失敗 (event_id=%s): %s", event_id, e)
            await db.execute(
                text("UPDATE calendar_events SET sync_status = 'failed' WHERE id = :id"),
                {"id": event_id},
            )
            await db.commit()
            await reset_tenant_context(db, tenant_id)

    return {"id": event_id, "meet_url": meet_url}


async def _save_meet_url(db: AsyncSession, tenant_id: int, event_id: int, meet_url: str) -> None:
    """Meet の URL を calendar_events.meet_url（唯一の置き場所）に保存する。"""
    await db.execute(
        text("UPDATE calendar_events SET meet_url = :url WHERE id = :id"),
        {"url": meet_url, "id": event_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)


async def _attach_meet_only(db: AsyncSession, tenant_id: int, event_id: int) -> dict:
    """Meet を付けるだけの直し。題名・時刻は送らず conferenceData だけを patch する。

    _to_google_event_body は題名を空で作り時刻を空にするので、ここでは使わない。
    """
    row = await db.execute(
        text("SELECT google_event_id, meet_url FROM calendar_events WHERE id = :id"),
        {"id": event_id},
    )
    record = row.first()
    google_event_id = record[0] if record else None
    current_url = record[1] if record else None
    if not google_event_id or current_url:
        return {"id": event_id, "meet_url": current_url}
    sync_mode = await _get_sync_mode(db, tenant_id)
    if sync_mode not in ("bidirectional", "write_only"):
        return {"id": event_id, "meet_url": None}

    meet_url: Optional[str] = None
    try:
        from app.services import google_calendar as cal_svc

        google_event = await cal_svc.update_event(
            db,
            tenant_id,
            google_event_id,
            {"conferenceData": _meet_create_request()},
            conference=True,
        )
        meet_url = await _resolve_meet_url(db, tenant_id, google_event)
    except Exception as e:
        logger.warning("Google Meet の追加に失敗 (event_id=%s): %s", event_id, e)
    if meet_url:
        await _save_meet_url(db, tenant_id, event_id, meet_url)
    return {"id": event_id, "meet_url": meet_url}


# ---------------------------------------------------------------------------
# イベント削除
# ---------------------------------------------------------------------------


async def delete_event(
    db: AsyncSession,
    tenant_id: int,
    event_id: int,
) -> None:
    """アプリ内のイベントを削除し、Google Calendar からも削除する。"""
    row = await db.execute(
        text("SELECT google_event_id FROM calendar_events WHERE id = :id"),
        {"id": event_id},
    )
    record = row.first()
    google_event_id = record[0] if record else None

    await db.execute(
        text("DELETE FROM calendar_events WHERE id = :id"),
        {"id": event_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    sync_mode = await _get_sync_mode(db, tenant_id)
    if google_event_id and sync_mode in ("bidirectional", "write_only"):
        try:
            from app.services import google_calendar as cal_svc

            await cal_svc.delete_event(db, tenant_id, google_event_id)
        except Exception as e:
            logger.warning("Google Calendar 削除同期に失敗 (event_id=%s): %s", event_id, e)


# ---------------------------------------------------------------------------
# 繰り返しの判定（ADR-1075 §12.5。誤りの識別の文字か None を返す。表は読むだけ）
# ---------------------------------------------------------------------------

_TEXT_FIELDS = ("title", "description", "location", "calendar_type", "user_id")


def parse_occurrence(value: Optional[str]) -> Optional[datetime]:
    """occurrence_start の文字を日本時間の aware にする。無い・読めないものは None。"""
    if not value:
        return None
    try:
        return rec.to_jst(_parse_dt(value))
    except (ValueError, TypeError):
        return None


def _as_jst(value) -> datetime:
    if isinstance(value, str):
        value = _parse_dt(value)
    return rec.to_jst(value)


def check_create_recurrence(payload: dict) -> Optional[str]:
    """作るときの繰り返しの判定。"""
    recurrence = payload.get("recurrence") or "none"
    if recurrence == "none":
        return None
    if payload.get("add_meet"):
        return "recurrence_meet_not_allowed"
    try:
        start = _parse_dt(payload["start_datetime"])
    except (KeyError, ValueError, TypeError):
        return None
    try:
        rec.build_rule(recurrence, start)
    except ValueError:
        return "recurrence_not_available"
    return None


def _plan(master: dict, event: dict, payload: dict, occ_dt: datetime, scope: str) -> dict:
    """following・all・this の直し方を決める（判定と処理で同じ値を使う）。"""
    is_exc = event.get("recurring_event_id") is not None
    m_start = rec.to_jst(master["start_datetime"])
    m_end = rec.to_jst(master["end_datetime"])
    m_all_day = bool(master["is_all_day"])
    duration = m_end - m_start
    occ = rec.occurrence_of(m_start, m_all_day, occ_dt)
    if is_exc:
        cur_start = rec.to_jst(event["start_datetime"])
        cur_end = rec.to_jst(event["end_datetime"])
        cur_all_day = bool(event["is_all_day"])
    else:
        cur_start, cur_end, cur_all_day = occ, occ + duration, m_all_day
    new_start = _as_jst(payload["start_datetime"]) if "start_datetime" in payload else cur_start
    new_end = _as_jst(payload["end_datetime"]) if "end_datetime" in payload else cur_end
    new_all_day = bool(payload["is_all_day"]) if "is_all_day" in payload else cur_all_day
    cur_rec = rec.rule_to_recurrence(master["recurrence_rule"])
    choice = payload.get("recurrence")
    final_rec = choice if choice is not None else cur_rec
    rec_changed = final_rec != cur_rec
    time_changed = new_start != cur_start or new_end != cur_end or new_all_day != cur_all_day
    changed_fields = {
        k: payload[k] for k in _TEXT_FIELDS if k in payload and payload[k] != event.get(k)
    }
    start_shift = (new_start - occ) if "start_datetime" in payload else timedelta(0)
    end_shift = (new_end - (occ + duration)) if "end_datetime" in payload else start_shift
    first = rec.is_first_occurrence(m_start, m_all_day, occ)
    eff = "all" if (scope == "following" and first) else scope
    kind = "this"
    rule_start = None
    base_start = None
    if eff == "following":
        kind, rule_start, base_start = "C", new_start, occ
    elif eff == "all":
        if final_rec == "none" and rec_changed:
            kind = "D3"
        elif time_changed or rec_changed:
            kind = "D2"
            rule_start, base_start = m_start + start_shift, m_start
        else:
            kind = "D1"
    return {
        "kind": kind,
        "occ": occ,
        "duration": duration,
        "cur_start": cur_start,
        "cur_end": cur_end,
        "cur_all_day": cur_all_day,
        "new_start": new_start,
        "new_end": new_end,
        "new_all_day": new_all_day,
        "new_m_start": m_start + start_shift,
        "new_m_end": m_end + end_shift,
        "final_rec": final_rec,
        "rec_changed": rec_changed,
        "time_changed": time_changed,
        "changed_fields": changed_fields,
        "rule_start": rule_start,
        "base_start": base_start,
    }


def _rule_for(final_rec: str, start: datetime, master_rule: Optional[str], all_day: bool) -> Optional[str]:
    """新しい決まり。元の UNTIL は引き継ぐ。none は None。読み戻せない決まりは元のまま。"""
    if final_rec == "none":
        return None
    if final_rec == "custom":
        return master_rule
    return rec.carry_until(rec.build_rule(final_rec, start), master_rule, all_day)


def _plan_error(plan: dict, master: dict) -> Optional[str]:
    if plan["kind"] not in ("C", "D2") or plan["final_rec"] == "none":
        return None
    final = plan["final_rec"]
    if final == "custom":
        return "recurrence_not_available" if plan["rule_start"] != plan["base_start"] else None
    try:
        rule = _rule_for(final, plan["rule_start"], master["recurrence_rule"], plan["new_all_day"])
    except ValueError:
        return "recurrence_not_available"
    if rule and rec.starts_after_until(rule, plan["rule_start"], plan["new_all_day"]):
        return "recurrence_after_until"
    return None


async def check_recurrence_request(
    db: AsyncSession,
    *,
    event: dict,
    payload: Optional[dict],
    scope: Optional[str],
    occurrence_start: Optional[str],
) -> Optional[str]:
    """直す・消すときの繰り返しの判定。誤りの識別の文字か None。payload は消すとき None。"""
    is_delete = payload is None
    payload = payload or {}
    choice = payload.get("recurrence")
    is_exc = event.get("recurring_event_id") is not None
    is_master = event.get("recurrence_rule") is not None

    if not (is_exc or is_master):
        if scope is not None:
            return "recurrence_scope_not_allowed"
        if choice in (None, "none"):
            return None
        if event.get("source") == "google":
            return "recurrence_google_source"
        if payload.get("add_meet") or event.get("meet_url"):
            return "recurrence_meet_not_allowed"
        start = payload.get("start_datetime", event["start_datetime"])
        try:
            rec.build_rule(choice, _as_jst(start))
        except ValueError:
            return "recurrence_not_available"
        return None

    if scope is None:
        return "recurrence_scope_required"
    if payload.get("add_meet"):
        return "recurrence_meet_not_allowed"
    master = event if is_master else await read_event(db, event["recurring_event_id"])
    if master is None:
        return "recurrence_occurrence_invalid"
    occ_dt = parse_occurrence(occurrence_start)
    if occ_dt is None:
        return "recurrence_occurrence_invalid"
    if is_exc:
        if abs(rec.to_jst(event["original_start_datetime"]) - occ_dt) > timedelta(seconds=1):
            return "recurrence_occurrence_invalid"
    elif not rec.is_occurrence(
        master["recurrence_rule"], master["start_datetime"], bool(master["is_all_day"]), occ_dt
    ):
        return "recurrence_occurrence_invalid"

    if is_delete:
        return None
    if scope == "this":
        if "calendar_type" in payload and payload["calendar_type"] != event.get("calendar_type"):
            return "recurrence_this_not_allowed"
        if choice is not None and choice != rec.rule_to_recurrence(master["recurrence_rule"]):
            return "recurrence_this_not_allowed"
        return None
    return _plan_error(_plan(master, event, payload, occ_dt, scope), master)


# ---------------------------------------------------------------------------
# 繰り返しの 3 択（この予定／これ以降／すべて）の処理（ADR-1075 §12.5・§12.7）
# ---------------------------------------------------------------------------


async def _commit(db: AsyncSession, tenant_id: int) -> None:
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # Rule C: commit 後は別接続になりうる


async def _send_ok(db: AsyncSession, tenant_id: int, master: dict) -> bool:
    """Google に送るか: 元の行が Google の id を持ち、同期の向きが送る方式。"""
    if not master.get("google_event_id"):
        return False
    return await _get_sync_mode(db, tenant_id) in ("bidirectional", "write_only")


async def _mark_synced(db: AsyncSession, tenant_id: int, row_id: int, google_event_id: Optional[str] = None) -> None:
    if google_event_id:
        await db.execute(
            text(
                "UPDATE calendar_events SET google_event_id = :gid, sync_origin_id = :oid,"
                " sync_status = 'synced', last_synced_at = NOW() WHERE id = :id"
            ),
            {"gid": google_event_id, "oid": _build_sync_origin_id(tenant_id, row_id), "id": row_id},
        )
    else:
        await db.execute(
            text(
                "UPDATE calendar_events SET sync_status = 'synced', last_synced_at = NOW() WHERE id = :id"
            ),
            {"id": row_id},
        )
    await _commit(db, tenant_id)


async def _mark_failed(db: AsyncSession, tenant_id: int, row_id: int, clear_ids: bool = False) -> None:
    extra = ", google_event_id = NULL, sync_origin_id = NULL" if clear_ids else ""
    await db.execute(
        text(f"UPDATE calendar_events SET sync_status = 'failed'{extra} WHERE id = :id"),
        {"id": row_id},
    )
    await _commit(db, tenant_id)


async def _exception_google_ids(db: AsyncSession, master_id: int, from_occ: Optional[datetime] = None) -> list[str]:
    """消える例外の行の Google の id（消した印でないもの）。表を変える前に読む。"""
    sql = (
        "SELECT google_event_id FROM calendar_events"
        " WHERE recurring_event_id = :mid AND is_cancelled = false AND google_event_id IS NOT NULL"
    )
    params: dict = {"mid": master_id}
    if from_occ is not None:
        sql += " AND original_start_datetime >= :occ"
        params["occ"] = from_occ
    result = await db.execute(text(sql), params)
    return [r[0] for r in result.fetchall()]


async def _cancel_google_instances(db: AsyncSession, tenant_id: int, google_ids: list[str]) -> None:
    """例外の回を Google 側で取り消す。1 件ずつ別に送り、失敗は警告だけで次へ進む。"""
    from app.services import google_calendar as gcal

    for gid in google_ids:
        try:
            await gcal.update_event(db, tenant_id, gid, {"status": "cancelled"})
        except Exception as e:
            logger.warning("Google の例外の回の取り消しに失敗 (google_event_id=%s): %s", gid, e)


async def _find_exception(db: AsyncSession, master_id: int, occ: datetime) -> Optional[dict]:
    row = await db.execute(
        text(
            f"SELECT {EVENT_COLUMNS_SQL} FROM calendar_events"
            " WHERE recurring_event_id = :mid AND original_start_datetime = :orig"
        ),
        {"mid": master_id, "orig": occ},
    )
    record = row.first()
    return event_from_row(record) if record else None


async def _insert_row(db: AsyncSession, values: dict) -> int:
    """新しい行を入れる。sync_status と source は明示する（初期値の 'synced' にしない）。"""
    result = await db.execute(
        text(
            "INSERT INTO calendar_events"
            " (user_id, calendar_type, category, title, description, location,"
            "  start_datetime, end_datetime, is_all_day, source, sync_status,"
            "  created_by_user_id, recurrence_rule, recurring_event_id,"
            "  original_start_datetime, is_cancelled)"
            " VALUES"
            " (:user_id, :calendar_type, :category, :title, :description, :location,"
            "  :start_datetime, :end_datetime, :is_all_day, 'app', 'pending',"
            "  :created_by_user_id, :recurrence_rule, :recurring_event_id,"
            "  :original_start_datetime, :is_cancelled)"
            " RETURNING id"
        ),
        values,
    )
    return result.scalar_one()


def _row_values(master: dict, **over) -> dict:
    values = {
        "user_id": master["user_id"],
        "calendar_type": master["calendar_type"],
        "category": master["category"],
        "title": master["title"],
        "description": master["description"],
        "location": master["location"],
        "start_datetime": master["start_datetime"],
        "end_datetime": master["end_datetime"],
        "is_all_day": master["is_all_day"],
        "created_by_user_id": master["created_by_user_id"],
        "recurrence_rule": None,
        "recurring_event_id": None,
        "original_start_datetime": None,
        "is_cancelled": False,
    }
    values.update(over)
    return values


async def _update_fields(db: AsyncSession, where_sql: str, params: dict, fields: dict) -> None:
    """表を直す UPDATE。必ず sync_status = 'pending' を入れる。"""
    sets = [f"{k} = :f_{k}" for k in fields] + ["sync_status = 'pending'"]
    p = dict(params)
    for k, v in fields.items():
        p[f"f_{k}"] = v
    await db.execute(text(f"UPDATE calendar_events SET {', '.join(sets)} WHERE {where_sql}"), p)


async def _recreate_in_google(
    db: AsyncSession, tenant_id: int, row_id: int, old_google_id: str, body: dict
) -> None:
    """消して作り直す道。消しの失敗は 'failed'（id は古いまま）、作りの失敗は 'failed' で id を空にする。"""
    from app.services import google_calendar as gcal

    try:
        await gcal.delete_event(db, tenant_id, old_google_id)
    except Exception as e:
        logger.warning("Google の予定の削除に失敗 (event_id=%s): %s", row_id, e)
        await _mark_failed(db, tenant_id, row_id)
        return
    try:
        created = await gcal.create_event(db, tenant_id, body)
    except Exception as e:
        logger.warning("Google の予定の作り直しに失敗 (event_id=%s): %s", row_id, e)
        await _mark_failed(db, tenant_id, row_id, clear_ids=True)
        return
    await _mark_synced(db, tenant_id, row_id, created.get("id"))


def _merged(row: dict, **over) -> dict:
    out = dict(row)
    out.update(over)
    return out


async def update_recurring_event(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    event: dict,
    payload: dict,
    scope: Optional[str],
    occurrence_start: Optional[datetime],
) -> dict:
    """繰り返しの予定を直す（単発→繰り返し A・this B/B'・following C・all D1〜D3）。"""
    from app.services import google_calendar as gcal

    is_exc = event.get("recurring_event_id") is not None
    if not is_exc and event.get("recurrence_rule") is None:
        return await _update_single_to_recurring(db, tenant_id, event, payload)

    master = await read_event(db, event["recurring_event_id"]) if is_exc else event
    plan = _plan(master, event, payload, occurrence_start, scope or "all")
    occ = plan["occ"]
    kind = plan["kind"]
    fields = plan["changed_fields"]

    # ----- この予定（B / B'）
    if scope == "this":
        row = event if is_exc else await _find_exception(db, master["id"], occ)
        row_fields: dict = {k: payload[k] for k in ("title", "description", "location") if k in payload}
        if "start_datetime" in payload:
            row_fields["start_datetime"] = plan["new_start"]
        if "end_datetime" in payload:
            row_fields["end_datetime"] = plan["new_end"]
        if "is_all_day" in payload:
            row_fields["is_all_day"] = bool(payload["is_all_day"])
        if row is None:
            base = _row_values(
                master,
                start_datetime=plan["cur_start"],
                end_datetime=plan["cur_end"],
                is_all_day=plan["cur_all_day"],
                recurring_event_id=master["id"],
                original_start_datetime=occ,
            )
            base.update(row_fields)
            new_id = await _insert_row(db, base)
            row = _merged(base, id=new_id, google_event_id=None)
        else:
            if row_fields:
                await _update_fields(db, "id = :id", {"id": row["id"]}, row_fields)
            row = _merged(row, **row_fields)
        await _commit(db, tenant_id)
        if await _send_ok(db, tenant_id, master):
            try:
                gid = row.get("google_event_id")
                if not gid:
                    instance = await gcal.get_instance(
                        db, tenant_id, master["google_event_id"], occ, bool(master["is_all_day"])
                    )
                    gid = instance["id"]
                await gcal.update_event(db, tenant_id, gid, _google_body_for(row))
            except Exception as e:
                logger.warning("Google の例外の回の送りに失敗 (event_id=%s): %s", row["id"], e)
                await _mark_failed(db, tenant_id, row["id"])
            else:
                await _mark_synced(db, tenant_id, row["id"], gid)
        return {"id": row["id"], "meet_url": None}

    # ----- これ以降（C）
    if kind == "C":
        cut_rule = rec.with_until(
            master["recurrence_rule"], rec.until_before(occ, bool(master["is_all_day"]))
        )
        gone_ids = await _exception_google_ids(db, master["id"], occ)
        await db.execute(
            text("UPDATE calendar_events SET recurrence_rule = :r, sync_status = 'pending' WHERE id = :id"),
            {"r": cut_rule, "id": master["id"]},
        )
        await db.execute(
            text(
                "DELETE FROM calendar_events"
                " WHERE recurring_event_id = :mid AND original_start_datetime >= :occ"
            ),
            {"mid": master["id"], "occ": occ},
        )
        source = event if is_exc else master
        new_rule = _rule_for(
            plan["final_rec"], plan["new_start"], master["recurrence_rule"], plan["new_all_day"]
        )
        values = _row_values(
            source,
            user_id=fields.get("user_id", master["user_id"]),
            calendar_type=fields.get("calendar_type", master["calendar_type"]),
            category=master["category"],
            title=fields.get("title", source["title"]),
            description=fields.get("description", source["description"]),
            location=fields.get("location", source["location"]),
            start_datetime=plan["new_start"],
            end_datetime=plan["new_end"],
            is_all_day=plan["new_all_day"],
            created_by_user_id=master["created_by_user_id"],
            recurrence_rule=new_rule,
        )
        new_id = await _insert_row(db, values)
        await _commit(db, tenant_id)
        new_row = _merged(values, id=new_id)
        if await _send_ok(db, tenant_id, master):
            await _cancel_google_instances(db, tenant_id, gone_ids)
            try:
                await gcal.update_event(
                    db, tenant_id, master["google_event_id"], {"recurrence": rec.google_recurrence(cut_rule)}
                )
            except Exception as e:
                logger.warning("Google の元の予定の切り詰めに失敗 (event_id=%s): %s", master["id"], e)
                await _mark_failed(db, tenant_id, master["id"])
                await _mark_failed(db, tenant_id, new_id)
                return {"id": new_id, "meet_url": None}
            await _mark_synced(db, tenant_id, master["id"])
            try:
                created = await gcal.create_event(db, tenant_id, _google_body_for(new_row))
            except Exception as e:
                logger.warning("Google の新しい予定の作成に失敗 (event_id=%s): %s", new_id, e)
                await _mark_failed(db, tenant_id, new_id)
            else:
                await _mark_synced(db, tenant_id, new_id, created.get("id"))
        return {"id": new_id, "meet_url": None}

    # ----- すべて（D1 / D2 / D3）
    gone_ids = await _exception_google_ids(db, master["id"]) if kind in ("D2", "D3") else []
    if kind == "D1":
        if fields:
            await _update_fields(db, "id = :id", {"id": master["id"]}, fields)
            await _update_fields(db, "recurring_event_id = :id", {"id": master["id"]}, fields)
        after = _merged(master, **fields)
        await _commit(db, tenant_id)
        if fields and await _send_ok(db, tenant_id, master):
            body = _google_body_for(after)
            body.pop("recurrence", None)
            try:
                await gcal.update_event(db, tenant_id, master["google_event_id"], body)
            except Exception as e:
                logger.warning("Google の予定の更新に失敗 (event_id=%s): %s", master["id"], e)
                await _mark_failed(db, tenant_id, master["id"])
            else:
                await _mark_synced(db, tenant_id, master["id"])
        return {"id": master["id"], "meet_url": None}

    if kind == "D2":
        new_rule = _rule_for(
            plan["final_rec"], plan["new_m_start"], master["recurrence_rule"], plan["new_all_day"]
        )
        set_fields = dict(fields)
        set_fields.update(
            start_datetime=plan["new_m_start"],
            end_datetime=plan["new_m_end"],
            is_all_day=plan["new_all_day"],
            recurrence_rule=new_rule,
        )
    else:  # D3
        set_fields = dict(fields)
        set_fields.update(
            start_datetime=plan["new_start"],
            end_datetime=plan["new_end"],
            is_all_day=plan["new_all_day"],
            recurrence_rule=None,
        )
    await _update_fields(db, "id = :id", {"id": master["id"]}, set_fields)
    await db.execute(
        text("DELETE FROM calendar_events WHERE recurring_event_id = :mid"), {"mid": master["id"]}
    )
    after = _merged(master, **set_fields)
    await _commit(db, tenant_id)
    if await _send_ok(db, tenant_id, master):
        await _cancel_google_instances(db, tenant_id, gone_ids)
        await _recreate_in_google(
            db, tenant_id, master["id"], master["google_event_id"], _google_body_for(after)
        )
    return {"id": master["id"], "meet_url": None}


async def _update_single_to_recurring(
    db: AsyncSession, tenant_id: int, event: dict, payload: dict
) -> dict:
    """A: 単発の行に繰り返しを付ける。Google に id があれば消して作り直す。"""
    new_start = _as_jst(payload["start_datetime"]) if "start_datetime" in payload else rec.to_jst(event["start_datetime"])
    fields: dict = {}
    for k in ("title", "description", "location", "calendar_type", "user_id", "is_all_day"):
        if k in payload:
            fields[k] = payload[k]
    for k in ("start_datetime", "end_datetime"):
        if k in payload:
            fields[k] = _parse_dt(payload[k])
    fields["recurrence_rule"] = rec.build_rule(payload["recurrence"], new_start)
    await _update_fields(db, "id = :id", {"id": event["id"]}, fields)
    after = _merged(event, **fields)
    await _commit(db, tenant_id)
    if await _send_ok(db, tenant_id, event):
        await _recreate_in_google(
            db, tenant_id, event["id"], event["google_event_id"], _google_body_for(after)
        )
    return {"id": event["id"], "meet_url": None}


async def delete_recurring_event(
    db: AsyncSession,
    tenant_id: int,
    event: dict,
    scope: str,
    occurrence_start: datetime,
) -> None:
    """繰り返しの予定を消す（this・following・all）。Google への送りの失敗は警告だけ。"""
    from app.services import google_calendar as gcal

    is_exc = event.get("recurring_event_id") is not None
    master = await read_event(db, event["recurring_event_id"]) if is_exc else event
    m_all_day = bool(master["is_all_day"])
    m_start = rec.to_jst(master["start_datetime"])
    occ = rec.occurrence_of(m_start, m_all_day, occurrence_start)
    if scope == "following" and rec.is_first_occurrence(m_start, m_all_day, occ):
        scope = "all"

    if scope == "this":
        row = event if is_exc else await _find_exception(db, master["id"], occ)
        if row is not None:
            await db.execute(
                text("UPDATE calendar_events SET is_cancelled = true WHERE id = :id"),
                {"id": row["id"]},
            )
            row_id, row_gid = row["id"], row.get("google_event_id")
        else:
            duration = rec.to_jst(master["end_datetime"]) - m_start
            row_id = await _insert_row(
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
            row_gid = None
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

    if scope == "following":
        cut_rule = rec.with_until(master["recurrence_rule"], rec.until_before(occ, m_all_day))
        gone_ids = await _exception_google_ids(db, master["id"], occ)
        await db.execute(
            text("UPDATE calendar_events SET recurrence_rule = :r WHERE id = :id"),
            {"r": cut_rule, "id": master["id"]},
        )
        await db.execute(
            text(
                "DELETE FROM calendar_events"
                " WHERE recurring_event_id = :mid AND original_start_datetime >= :occ"
            ),
            {"mid": master["id"], "occ": occ},
        )
        await _commit(db, tenant_id)
        if await _send_ok(db, tenant_id, master):
            await _cancel_google_instances(db, tenant_id, gone_ids)
            try:
                await gcal.update_event(
                    db, tenant_id, master["google_event_id"], {"recurrence": rec.google_recurrence(cut_rule)}
                )
            except Exception as e:
                logger.warning("Google の元の予定の切り詰めに失敗 (event_id=%s): %s", master["id"], e)
        return

    # all
    gone_ids = await _exception_google_ids(db, master["id"])
    await db.execute(text("DELETE FROM calendar_events WHERE id = :id"), {"id": master["id"]})
    await _commit(db, tenant_id)
    if await _send_ok(db, tenant_id, master):
        await _cancel_google_instances(db, tenant_id, gone_ids)
        try:
            await gcal.delete_event(db, tenant_id, master["google_event_id"])
        except Exception as e:
            logger.warning("Google の予定の削除に失敗 (event_id=%s): %s", master["id"], e)


# ---------------------------------------------------------------------------
# Webhook 受信時の upsert
# ---------------------------------------------------------------------------


_JST = ZoneInfo("Asia/Tokyo")


def _google_times(start: dict, end: dict) -> tuple[datetime, datetime, bool]:
    """Google の start/end を (開始, 終了, 終日か) の datetime に直す（ADR-1059 便2）。

    終日: Google の終わりの日は「次の日」なので、アプリの形
    （開始日 00:00〜終了日 23:59・日本時間）に直す。
    時刻あり: dateTime を datetime にする。時差が無いときは timeZone、無ければ日本時間を付ける。
    """
    if "date" in start:
        start_date = date.fromisoformat(start["date"])
        start_dt = datetime.combine(start_date, time(0, 0), tzinfo=_JST)
        end_date = date.fromisoformat(end["date"]) - timedelta(days=1)
        if end_date < start_date:
            end_date = start_date
        end_dt = datetime.combine(end_date, time(23, 59), tzinfo=_JST)
        return start_dt, end_dt, True

    def _one(part: dict) -> datetime:
        dt = datetime.fromisoformat(part["dateTime"])
        if dt.tzinfo is None:
            tz_name = part.get("timeZone")
            try:
                tz = ZoneInfo(tz_name) if tz_name else _JST
            except Exception:
                tz = _JST
            dt = dt.replace(tzinfo=tz)
        return dt

    return _one(start), _one(end), False


async def upsert_from_google(
    db: AsyncSession,
    tenant_id: int,
    google_event: dict,
    owner_user_id: int,
) -> str:
    """Google のイベントを DB に upsert する。戻り値は "upserted" | "deleted" | "skipped"。

    commit は呼び元が 1 回だけ行う。

    無限ループ防止:
      - sync_origin_id が "app:tenant_id:*" で始まるイベントはアプリ起源なのでスキップ。
      - これにより「アプリ → Google → Webhook → アプリ → ...」の無限ループを防ぐ。

    新規は calendar_type='personal'・持ち主 = owner_user_id。既にある行の
    calendar_type・user_id は上書きしない（ADR-1059 K4）。
    """
    google_event_id = google_event.get("id")
    if not google_event_id:
        return "skipped"

    # アプリ起源のイベントか確認（ループ防止）
    if await _is_app_origin(db, google_event_id, tenant_id):
        logger.debug("スキップ（アプリ起源）: google_event_id=%s", google_event_id)
        return "skipped"
    recurring_event_id = google_event.get("recurringEventId")
    if recurring_event_id and await _is_app_origin(db, recurring_event_id, tenant_id):
        return "skipped"

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

    title = google_event.get("summary", "")
    description = google_event.get("description")
    location = google_event.get("location")

    start_raw = (google_event.get("start") or {})
    end_raw = (google_event.get("end") or {})

    if not (start_raw.get("dateTime") or start_raw.get("date")) or not (
        end_raw.get("dateTime") or end_raw.get("date")
    ):
        logger.warning("start/end が不正: google_event_id=%s", google_event_id)
        return "skipped"

    start_dt, end_dt, is_all_day = _google_times(start_raw, end_raw)

    origin_id = f"google:{tenant_id}:{google_event_id}"

    await db.execute(
        text(
            "INSERT INTO calendar_events"
            " (user_id, created_by_user_id, calendar_type, title, description, location,"
            "  start_datetime, end_datetime, is_all_day,"
            "  google_event_id, google_calendar_id, source, sync_status,"
            "  sync_origin_id, last_synced_at, meet_url)"
            " VALUES"
            " (:owner, :owner, 'personal', :title, :desc, :loc,"
            "  :start, :end, :all_day,"
            "  :gid, :gcal_id, 'google', 'synced',"
            "  :origin, NOW(), :meet_url)"
            " ON CONFLICT (google_event_id) WHERE google_event_id IS NOT NULL DO UPDATE SET"
            "   title            = EXCLUDED.title,"
            "   description      = EXCLUDED.description,"
            "   location         = EXCLUDED.location,"
            "   start_datetime   = EXCLUDED.start_datetime,"
            "   end_datetime     = EXCLUDED.end_datetime,"
            "   is_all_day       = EXCLUDED.is_all_day,"
            "   meet_url         = EXCLUDED.meet_url,"
            "   sync_status      = 'synced',"
            "   last_synced_at   = NOW(),"
            "   updated_at       = NOW()"
            " WHERE calendar_events.source = 'google'"
        ),
        {
            "owner": owner_user_id,
            "title": title,
            "desc": description,
            "loc": location,
            "start": start_dt,
            "end": end_dt,
            "all_day": is_all_day,
            "gid": google_event_id,
            "gcal_id": "primary",
            "origin": origin_id,
            "meet_url": google_event.get("hangoutLink"),
        },
    )
    return "upserted"


# ---------------------------------------------------------------------------
# Google Calendar API 用ボディ変換
# ---------------------------------------------------------------------------


def _to_google_event_body(payload: dict) -> dict:
    """アプリのイベント payload を Google Calendar API 用ボディに変換する。"""
    body: dict = {
        "summary": payload.get("title", ""),
    }

    start_dt = payload.get("start_datetime", "")
    end_dt = payload.get("end_datetime", "")

    if payload.get("is_all_day"):

        def _jst_date(value: object) -> tuple[date, bool]:
            # 日付だけの値はそのまま（2 つ目は「日付だけか」）。時刻つきは日本時間の日付にする
            # （時差なしは日本時間とみなす）
            s = str(value)
            if "T" not in s:
                return date.fromisoformat(s[:10]), True
            dt = _parse_dt(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_JST)
            return dt.astimezone(_JST).date(), False

        start_day, start_plain = _jst_date(start_dt)
        end_day, end_plain = _jst_date(end_dt)
        if not end_plain:
            # Google の終わりの日は「次の日」
            end_day = end_day + timedelta(days=1)
        if not (start_plain and end_plain) and end_day <= start_day:
            end_day = start_day + timedelta(days=1)
        body["start"] = {"date": start_day.isoformat()}
        body["end"] = {"date": end_day.isoformat()}
    else:
        body["start"] = {"dateTime": start_dt, "timeZone": "Asia/Tokyo"}
        body["end"] = {"dateTime": end_dt, "timeZone": "Asia/Tokyo"}

    if payload.get("description"):
        body["description"] = payload["description"]
    if payload.get("location"):
        body["location"] = payload["location"]

    return body
