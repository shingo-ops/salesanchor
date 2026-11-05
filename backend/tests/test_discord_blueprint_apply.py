"""自社用 Discord サーバーへの反映の係（discord-server-management 便3b）の試験。

apply_plan を直接呼ぶ。Discord への呼び出しは AsyncMock に差し替える（本物の Discord には繋がない）。
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services import discord_blueprint_apply
from app.services.discord_blueprint_apply import apply_plan
from app.services.discord_rest import DiscordAPIError

_GUILD = "333333333333333333"
_TARGET = "app.services.discord_blueprint_apply.discord_api_request"


def _row(kind: str, key: str, field: str | None = None) -> dict:
    return {"kind": kind, "key": key, "name": key, "field": field, "before": None, "after": None}


def _plan(blocked: list[dict] | None = None) -> dict:
    ow = [{"id": "{ref:role:r1}", "type": 0, "allow": "1024", "deny": "0"}]
    return {
        "changes": [
            _row("create_role", "r1"),
            _row("create_category", "c1"),
            _row("create_channel", "n1"),
            _row("update_overwrite", "old", "overwrite:role:r1"),
        ],
        "actions": [
            {"method": "POST", "path": "/guilds/{guild}/roles", "json": {"name": "r1"}, "creates": "role:r1"},
            {"method": "POST", "path": "/guilds/{guild}/channels",
             "json": {"name": "c1", "type": 4, "permission_overwrites": []}, "creates": "category:c1"},
            {"method": "POST", "path": "/guilds/{guild}/channels",
             "json": {"name": "n1", "type": 0, "permission_overwrites": ow, "parent_id": "{ref:category:c1}"},
             "creates": "channel:n1"},
            {"method": "PUT", "path": "/channels/555/permissions/{ref:role:r1}",
             "json": {"type": 0, "allow": "1024", "deny": "0"}, "creates": None},
        ],
        "blocked": blocked or [],
        "delete_candidates": [],
        "plan_digest": "x" * 64,
    }


async def _reply(**kwargs):
    path = kwargs["path"]
    if kwargs["method"] == "PUT":
        return None
    if path.endswith("/roles"):
        return {"id": "900"}
    body = kwargs["json"]
    return {"id": "901" if body.get("type") == 4 else "902"}


def _calls(mock: AsyncMock) -> list[tuple[str, str]]:
    return [(c.kwargs["method"], c.kwargs["path"]) for c in mock.await_args_list]


@pytest.mark.asyncio
async def test_all_rows_succeed_and_guild_mark_is_replaced():
    mock = AsyncMock(side_effect=_reply)
    with patch(_TARGET, mock):
        results = await apply_plan(_plan(), _GUILD, "token")
    assert [r["status"] for r in results] == ["success"] * 4
    assert _calls(mock) == [
        ("POST", f"/guilds/{_GUILD}/roles"),
        ("POST", f"/guilds/{_GUILD}/channels"),
        ("POST", f"/guilds/{_GUILD}/channels"),
        ("PUT", "/channels/555/permissions/900"),
    ]
    assert [r["discord_id"] for r in results] == ["900", "901", "902", None]
    for call in mock.await_args_list:
        assert call.kwargs["expected_statuses"] == (200, 201, 204)
        assert call.kwargs["bot_token"] == "token"


@pytest.mark.asyncio
async def test_created_role_id_is_used_in_the_later_overwrite_path():
    mock = AsyncMock(side_effect=_reply)
    with patch(_TARGET, mock):
        await apply_plan(_plan(), _GUILD, "token")
    assert _calls(mock)[3][1].endswith("/permissions/900")


@pytest.mark.asyncio
async def test_created_category_id_is_used_as_parent_id_of_the_later_channel():
    mock = AsyncMock(side_effect=_reply)
    with patch(_TARGET, mock):
        await apply_plan(_plan(), _GUILD, "token")
    body = mock.await_args_list[2].kwargs["json"]
    assert body["parent_id"] == "901"
    # 入れ子の list の中の印も直る
    assert body["permission_overwrites"][0]["id"] == "900"


@pytest.mark.asyncio
async def test_failed_create_fails_dependents_without_calling_discord_and_continues():
    async def reply(**kwargs):
        if kwargs["path"].endswith("/roles"):
            raise DiscordAPIError("forbidden", status_code=403)
        return await _reply(**kwargs)

    mock = AsyncMock(side_effect=reply)
    with patch(_TARGET, mock):
        results = await apply_plan(_plan(), _GUILD, "token")
    assert [(r["status"], r["reason"], r["discord_status"]) for r in results] == [
        ("failed", "discord_error", 403),
        ("success", None, None),
        ("failed", "depends_failed", None),
        ("failed", "depends_failed", None),
    ]
    # 呼んだのは role の POST とカテゴリの POST だけ
    assert _calls(mock) == [("POST", f"/guilds/{_GUILD}/roles"), ("POST", f"/guilds/{_GUILD}/channels")]


@pytest.mark.asyncio
async def test_blocked_rows_are_reported_and_discord_is_not_called():
    plan = _plan(blocked=[{**_row("update_role", "boss", "name"), "reason": "role_above_bot"}])
    plan["changes"] = []
    plan["actions"] = []
    mock = AsyncMock()
    with patch(_TARGET, mock):
        results = await apply_plan(plan, _GUILD, "token")
    assert [(r["status"], r["reason"], r["key"]) for r in results] == [("blocked", "role_above_bot", "boss")]
    mock.assert_not_called()


@pytest.mark.asyncio
async def test_blocked_rows_come_after_the_changes():
    plan = _plan(blocked=[{**_row("update_role", "boss", "name"), "reason": "role_above_bot"}])
    mock = AsyncMock(side_effect=_reply)
    with patch(_TARGET, mock):
        results = await apply_plan(plan, _GUILD, "token")
    assert [r["status"] for r in results] == ["success"] * 4 + ["blocked"]


@pytest.mark.asyncio
async def test_a_method_outside_post_patch_put_is_refused_without_calling():
    plan = {
        "changes": [_row("update_channel", "x", "name")],
        "actions": [{"method": "DELETE", "path": "/channels/1", "json": {}, "creates": None}],
        "blocked": [],
    }
    mock = AsyncMock()
    with patch(_TARGET, mock):
        results = await apply_plan(plan, _GUILD, "token")
    assert [(r["status"], r["reason"]) for r in results] == [("failed", "method_not_allowed")]
    mock.assert_not_called()


def test_only_action_method_is_passed_as_method_and_no_delete_word():
    source = Path(discord_blueprint_apply.__file__).read_text(encoding="utf-8")
    assert '"DELETE"' not in source
    tree = ast.parse(source)
    values = [
        kw.value
        for call in ast.walk(tree) if isinstance(call, ast.Call)
        for kw in call.keywords if kw.arg == "method"
    ]
    assert len(values) == 1
    node = values[0]
    assert isinstance(node, ast.Subscript)
    assert isinstance(node.value, ast.Name) and node.value.id == "action"
    assert isinstance(node.slice, ast.Constant) and node.slice.value == "method"


@pytest.mark.asyncio
async def test_results_do_not_contain_the_guild_id():
    mock = AsyncMock(side_effect=_reply)
    with patch(_TARGET, mock):
        results = await apply_plan(_plan(), _GUILD, "token")
    assert _GUILD not in repr(results)
