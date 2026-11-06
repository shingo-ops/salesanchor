"""自社用 Discord サーバーへの反映（discord-server-management 便3b・設計 §4-8）。

約束:
  - 確認（build_plan）が作った actions を前から順に Discord へ送る。比べ方はここに書かない（SSOT）
  - 作る・変えるだけ。消す操作は無い（送ってよい method は POST・PATCH・PUT だけ）
  - blocked の行は Discord を呼ばない
  - 1 行失敗しても残りの行を続ける。先に作る物が失敗した行は呼ばずに失敗にする
  - 結果にサーバーの番号を入れない
"""
from __future__ import annotations

import re
from typing import Any

from app.services.discord_rest import DiscordAPIError, discord_api_request

_ALLOWED_METHODS = ("POST", "PATCH", "PUT")
_GUILD_MARK = "{guild}"
_REF_RE = re.compile(r"\{ref:[a-z]+:[a-z0-9_]+\}")


class _Unresolved(Exception):
    """先に作る物の番号が無い（その行は呼ばない）。"""


def _fix_text(text: str, guild_id: str, created: dict[str, str]) -> str:
    """path の中の印を本物の番号に直す。"""
    text = text.replace(_GUILD_MARK, guild_id)

    def _sub(match: re.Match[str]) -> str:
        return _lookup(match.group(0), created)

    return _REF_RE.sub(_sub, text)


def _lookup(mark: str, created: dict[str, str]) -> str:
    # "{ref:role:abc}" → "role:abc"
    key = mark[len("{ref:"):-1]
    if key not in created:
        raise _Unresolved(key)
    return created[key]


def _fix_value(value: Any, guild_id: str, created: dict[str, str]) -> Any:
    """json の値を、入れ子の dict と list まで見て直す。値がちょうど印のときだけ置き換える。"""
    if isinstance(value, dict):
        return {k: _fix_value(v, guild_id, created) for k, v in value.items()}
    if isinstance(value, list):
        return [_fix_value(v, guild_id, created) for v in value]
    if isinstance(value, str):
        if value == _GUILD_MARK:
            return guild_id
        if _REF_RE.fullmatch(value):
            return _lookup(value, created)
    return value


def _result(row: dict[str, Any], status: str, reason: str | None = None,
            discord_id: str | None = None, discord_status: int | None = None) -> dict[str, Any]:
    return {
        "kind": row.get("kind"),
        "key": row.get("key"),
        "name": row.get("name"),
        "field": row.get("field"),
        "status": status,
        "reason": reason,
        "discord_id": discord_id,
        "discord_status": discord_status,
    }


async def apply_plan(plan: dict[str, Any], guild_id: str, bot_token: str) -> list[dict[str, Any]]:
    """確認の結果（changes と actions）を Discord に反映し、行ごとの結果を返す。"""
    guild_id = str(guild_id)
    created: dict[str, str] = {}
    results: list[dict[str, Any]] = []

    for row, action in zip(plan["changes"], plan["actions"]):
        if action.get("method") == "DB":
            # アプリの側に番号を書くだけの行（第2段 2a-2 のロールをつなぐ）。Discord には送らない
            results.append(_result(row, "success", discord_id=str(action["json"]["discord_role_id"])))
            continue
        if action.get("method") not in _ALLOWED_METHODS:
            results.append(_result(row, "failed", "method_not_allowed"))
            continue
        try:
            path = _fix_text(action["path"], guild_id, created)
            body = _fix_value(action["json"], guild_id, created)
        except _Unresolved:
            results.append(_result(row, "failed", "depends_failed"))
            continue
        try:
            reply = await discord_api_request(
                method=action["method"],
                path=path,
                bot_token=bot_token,
                json=body,
                expected_statuses=(200, 201, 204),
            )
        except DiscordAPIError as exc:
            results.append(_result(row, "failed", "discord_error", discord_status=exc.status_code))
            continue
        new_id: str | None = None
        creates = action.get("creates")
        if creates and isinstance(reply, dict) and reply.get("id") is not None:
            new_id = str(reply["id"])
            created[creates] = new_id
        results.append(_result(row, "success", discord_id=new_id))

    for row in plan["blocked"]:
        results.append(_result(row, "blocked", row.get("reason")))
    return results
