from __future__ import annotations

"""
予定の種類（calendar_categories）の読み書き。

設計: docs/handoff/schedule-settings/design-bin2a.md §3-3
  - 種類の一覧の正本は各社の部屋の calendar_categories 1 つ（calendar_events.category は外部キーで結ぶ）
  - 消す道は作らない。使わなくする（is_active=false）だけ
  - 書いたあとは commit の直後に reset_tenant_context（ADR-072）
"""

import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import reset_tenant_context
from app.services import calendar_recurrence as rec
from app.services import calendar_service as cal_svc

logger = logging.getLogger(__name__)

# 使わなくできない種類。Google からの取り込みと、種類を送らない作成の既定がこの鍵のため
DEFAULT_CATEGORY_KEY = "meeting"

_COLUMNS = "key, name, color_key, default_share, sort_order, is_active"
# default_team_ids は列ではない（対応表 calendar_category_teams）ので、ここには入れない
_FIELD_COLUMNS = ("name", "color_key", "default_share", "is_active")

# 種類の共有の初期値の正本（裏側）。画面の型 CalendarShare・DB の CHECK と同じ 3 つ
CATEGORY_SHARE_VALUES = ("self", "all", "team")


def _row_to_dict(row, default_team_ids: Optional[list[int]] = None) -> dict:
    return {
        "key": row[0],
        "name": row[1],
        "color_key": row[2],
        "default_share": row[3],
        "sort_order": row[4],
        "is_active": row[5],
        "default_team_ids": default_team_ids or [],
    }


async def _default_team_map(db: AsyncSession, key: Optional[str] = None) -> dict[str, list[int]]:
    """種類ごとの初期のチーム（使っているチームだけ・id の昇順）。"""
    where = " WHERE cct.category_key = :key" if key is not None else ""
    result = await db.execute(
        text(
            "SELECT cct.category_key, cct.team_id FROM calendar_category_teams cct"
            " JOIN teams t ON t.id = cct.team_id AND t.is_active"
            f"{where} ORDER BY cct.category_key, cct.team_id"
        ),
        {"key": key} if key is not None else {},
    )
    out: dict[str, list[int]] = {}
    for category_key, team_id in result.fetchall():
        out.setdefault(category_key, []).append(team_id)
    return out


async def set_category_teams(db: AsyncSession, key: str, team_ids: list[int]) -> None:
    """種類の初期のチームを入れ替える書き手（唯一）。空なら消すだけ。commit しない＝呼び手の取引に乗る。"""
    await db.execute(text("DELETE FROM calendar_category_teams WHERE category_key = :key"), {"key": key})
    for team_id in team_ids:
        await db.execute(
            text("INSERT INTO calendar_category_teams (category_key, team_id) VALUES (:key, :tid)"),
            {"key": key, "tid": team_id},
        )


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


async def list_categories(db: AsyncSession) -> list[dict]:
    """全行（使わなくした行も is_active 付きで）を sort_order, key の順で返す。"""
    result = await db.execute(text(f"SELECT {_COLUMNS} FROM calendar_categories ORDER BY sort_order, key"))
    teams = await _default_team_map(db)
    return [_row_to_dict(r, teams.get(r[0])) for r in result.all()]


async def get_category(db: AsyncSession, key: str) -> Optional[dict]:
    result = await db.execute(
        text(f"SELECT {_COLUMNS} FROM calendar_categories WHERE key = :key"),
        {"key": key},
    )
    row = result.first()
    if not row:
        return None
    teams = await _default_team_map(db, key)
    return _row_to_dict(row, teams.get(key))


def _clean_name(name: Optional[str]) -> Optional[str]:
    """前後の空白を落として 1〜50 字を見る。空なら None。50 字を超えれば 422。"""
    if name is None:
        return None
    cleaned = name.strip()
    if cleaned == "":
        return None
    if len(cleaned) > 50:
        raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, "category_name_too_long")
    return cleaned


async def create_category(
    db: AsyncSession,
    tenant_id: int,
    name: str,
    color_key: Optional[str],
    default_share: str,
    default_team_ids: Optional[list[int]] = None,
) -> dict:
    """種類を足す。鍵は custom_ ＋ 今ある custom_ の最大の数＋1（数に直して取る）。

    default_share が team のときは使っているチームを 1 つ以上（default_team_ids）。確かめは書く前（422 invalid_team_ids）。
    """
    cleaned = _clean_name(name)
    if cleaned is None:
        raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, "category_name_required")
    team_ids = await cal_svc.validate_team_ids(db, default_share, default_team_ids)
    try:
        result = await db.execute(
            text(
                "INSERT INTO calendar_categories (key, name, color_key, default_share, sort_order)"
                " SELECT 'custom_' || (COALESCE(MAX(substring(key from '^custom_([0-9]+)$')::bigint), 0) + 1),"
                "        :name, :color_key, :default_share,"
                "        (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM calendar_categories)"
                " FROM calendar_categories WHERE key ~ '^custom_[0-9]+$'"
                f" RETURNING {_COLUMNS}"
            ),
            {"name": cleaned, "color_key": color_key or None, "default_share": default_share},
        )
        row = result.first()
        if team_ids:
            await set_category_teams(db, row[0], team_ids)
        await db.commit()
    except IntegrityError:
        # 同時に押されて鍵がぶつかった（または書く間にチームが消えた）。戻してから 409（その後の要求を普通に通すため）
        await db.rollback()
        await reset_tenant_context(db, tenant_id)
        raise _http(status.HTTP_409_CONFLICT, "category_conflict")
    await reset_tenant_context(db, tenant_id)  # ADR-072
    return _row_to_dict(row, team_ids)


async def update_category(
    db: AsyncSession,
    tenant_id: int,
    key: str,
    fields: dict,
) -> Optional[dict]:
    """名前・色・共有の初期値・使うかどうかを直す。無い鍵は None（受け口が 404 にする）。

    name: 7 種は空の文字で NULL に戻せる。custom_ は空にできず 422 category_name_required。
    color_key: 空の文字で NULL。
    meeting を is_active=false にする指定は 422 category_not_disableable。
    """
    current = await get_category(db, key)
    if current is None:
        return None

    sets: list[str] = []
    params: dict = {"key": key}
    for column in _FIELD_COLUMNS:
        if column not in fields:
            continue
        value = fields[column]
        if column == "name":
            value = _clean_name(value)
            if value is None and key.startswith("custom_"):
                raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, "category_name_required")
        elif column == "color_key":
            value = value or None
        elif column == "is_active":
            if value is False and key == DEFAULT_CATEGORY_KEY:
                raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, "category_not_disableable")
        sets.append(f"{column} = :{column}")
        params[column] = value

    # 初期のチーム: 共有の初期値かチームを送ったときだけ確かめる。今が team で team のまま送らないなら None（今の対応のまま）
    team_ids: Optional[list[int]] = None
    if "default_share" in fields or "default_team_ids" in fields:
        team_ids = await cal_svc.validate_team_ids(
            db, fields.get("default_share"), fields.get("default_team_ids"), current["default_share"]
        )

    if sets or team_ids is not None:
        try:
            if sets:
                await db.execute(
                    text(f"UPDATE calendar_categories SET {', '.join(sets)} WHERE key = :key"), params
                )
            if team_ids is not None:
                await set_category_teams(db, key, team_ids)
            await db.commit()
        except IntegrityError:
            # 書く間にチームが消えた。戻してから 409
            await db.rollback()
            await reset_tenant_context(db, tenant_id)
            raise _http(status.HTTP_409_CONFLICT, "category_conflict")
        await reset_tenant_context(db, tenant_id)  # ADR-072
    return await get_category(db, key)


async def validate_category_key(db: AsyncSession, key: str, current_key: Optional[str] = None) -> None:
    """予定に付ける種類の確かめ。表に無い・使っていない鍵は 422 invalid_category。

    直すときに今の種類と同じ鍵（current_key）なら、使わなくした種類でも通す（design A4）。
    """
    if current_key is not None and key == current_key:
        return
    category = await get_category(db, key)
    if category is None or not category["is_active"]:
        raise _http(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_category")


async def current_event_category(
    db: AsyncSession,
    event: dict,
    scope: Optional[str],
    occurrence_start: Optional[str],
) -> str:
    """直す前の予定の種類。繰り返しは、その回の例外の行が有ればその行、無ければ元の行の値。

    色の比べ方（calendar_service.update_recurring_event の「この予定だけ」）と同じ決め方。
    """
    is_exc = event.get("recurring_event_id") is not None
    if is_exc:
        return event["category"]
    if event.get("recurrence_rule") is None:
        return event["category"]
    # 元の行。回の指定が読めれば、その回の例外の行を探す
    occ_dt = cal_svc.parse_occurrence(occurrence_start)
    if occ_dt is not None:
        occ = rec.occurrence_of(
            rec.to_jst(event["start_datetime"]), bool(event["is_all_day"]), occ_dt
        )
        exception_row = await cal_svc._find_exception(db, event["id"], occ)
        if exception_row is not None:
            return exception_row["category"]
    return event["category"]
