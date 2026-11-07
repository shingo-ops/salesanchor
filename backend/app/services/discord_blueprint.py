"""自社用 Discord サーバーの設計図の形と、今のサーバーとの比べ方（discord-server-management 便3a・設計 §4-5）。

約束:
  - この中は純粋な処理。Discord も DB も呼ばない
  - 権限の名前の表はこの 1 か所だけに置く
  - 表に無いビットは比べない（設計 改訂4）
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.notification import NotificationEventType

EVERYONE = "@everyone"
BOT = "@bot"

# 第2段 2c（設計 D2-11）: 知らせの部屋の key → 届ける知らせの種類。対応はここ 1 か所だけ
NOTICE_ROOMS: dict[str, str] = {
    "assign_notice": NotificationEventType.lead_assigned.value,
    "reply_notice": NotificationEventType.customer_reply_received.value,
    "outside_notice": NotificationEventType.discord_outside_ticket_post.value,
}
NOTICE_WEBHOOK_NAME = "Sales Anchor"  # Discord の決まり: clyde・discord を入れない・80 字まで

# 出典: Discord 公式 github.com/discord/discord-api-docs developers/topics/permissions.mdx
# （e3ea58903、2026-10-29 更新）の表。47 番は無い。
PERMISSION_BITS: dict[str, int] = {
    "CREATE_INSTANT_INVITE": 0, "KICK_MEMBERS": 1, "BAN_MEMBERS": 2, "ADMINISTRATOR": 3,
    "MANAGE_CHANNELS": 4, "MANAGE_GUILD": 5, "ADD_REACTIONS": 6, "VIEW_AUDIT_LOG": 7,
    "PRIORITY_SPEAKER": 8, "STREAM": 9, "VIEW_CHANNEL": 10, "SEND_MESSAGES": 11,
    "SEND_TTS_MESSAGES": 12, "MANAGE_MESSAGES": 13, "EMBED_LINKS": 14, "ATTACH_FILES": 15,
    "READ_MESSAGE_HISTORY": 16, "MENTION_EVERYONE": 17, "USE_EXTERNAL_EMOJIS": 18,
    "VIEW_GUILD_INSIGHTS": 19, "CONNECT": 20, "SPEAK": 21, "MUTE_MEMBERS": 22,
    "DEAFEN_MEMBERS": 23, "MOVE_MEMBERS": 24, "USE_VAD": 25, "CHANGE_NICKNAME": 26,
    "MANAGE_NICKNAMES": 27, "MANAGE_ROLES": 28, "MANAGE_WEBHOOKS": 29,
    "MANAGE_GUILD_EXPRESSIONS": 30, "USE_APPLICATION_COMMANDS": 31, "REQUEST_TO_SPEAK": 32,
    "MANAGE_EVENTS": 33, "MANAGE_THREADS": 34, "CREATE_PUBLIC_THREADS": 35,
    "CREATE_PRIVATE_THREADS": 36, "USE_EXTERNAL_STICKERS": 37, "SEND_MESSAGES_IN_THREADS": 38,
    "USE_EMBEDDED_ACTIVITIES": 39, "MODERATE_MEMBERS": 40,
    "VIEW_CREATOR_MONETIZATION_ANALYTICS": 41, "USE_SOUNDBOARD": 42,
    "CREATE_GUILD_EXPRESSIONS": 43, "CREATE_EVENTS": 44, "USE_EXTERNAL_SOUNDS": 45,
    "SEND_VOICE_MESSAGES": 46, "SET_VOICE_CHANNEL_STATUS": 48, "SEND_POLLS": 49,
    "USE_EXTERNAL_APPS": 50, "PIN_MESSAGES": 51, "BYPASS_SLOWMODE": 52,
}
KNOWN_MASK: int = sum(1 << bit for bit in PERMISSION_BITS.values())

_ADMINISTRATOR = 1 << PERMISSION_BITS["ADMINISTRATOR"]
_MANAGE_ROLES = 1 << PERMISSION_BITS["MANAGE_ROLES"]
_VIEW_CHANNEL = "VIEW_CHANNEL"


def names_to_bits(names: list[str]) -> int:
    """権限の名前の並びを数にする。表に無い名前は ValueError。"""
    value = 0
    for name in names:
        if name not in PERMISSION_BITS:
            raise ValueError(f"unknown permission name: {name}")
        value |= 1 << PERMISSION_BITS[name]
    return value


def bits_to_names(value: int) -> list[str]:
    """数を権限の名前の並びにする。並びは表の順。表に無いビットは捨てる。"""
    return [name for name, bit in PERMISSION_BITS.items() if value & (1 << bit)]


# ---------------------------------------------------------------- 設計図の形


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BpOverwrite(_Strict):
    target: str
    allow: list[str] = []
    deny: list[str] = []


class BpRole(_Strict):
    key: str
    discord_id: str | None = None
    name: str
    color: int = 0
    hoist: bool = False
    mentionable: bool = False
    permissions: list[str] = []


class BpCategory(_Strict):
    key: str
    discord_id: str | None = None
    name: str
    overwrites: list[BpOverwrite] = []


class BpChannel(_Strict):
    key: str
    discord_id: str | None = None
    name: str
    type: Literal["text"]
    category: str | None = None
    topic: str | None = None
    overwrites: list[BpOverwrite] = []


class Blueprint(_Strict):
    version: Literal[1]
    roles: list[BpRole]
    categories: list[BpCategory]
    channels: list[BpChannel]


_KEY_RE = re.compile(r"^[a-z0-9_]+$")
_ID_RE = re.compile(r"^[0-9]+$")


def validate_blueprint(bp: Blueprint) -> None:
    """形のほかの検査（設計 §4-5）。1 つでも外れたら ValueError（理由の文に key を入れる）。"""
    # 1. key は通して重ならない
    seen: set[str] = set()
    for key in [r.key for r in bp.roles] + [c.key for c in bp.categories] + [c.key for c in bp.channels]:
        if not _KEY_RE.match(key):
            raise ValueError(f"key is not allowed: {key}")
        if key in seen:
            raise ValueError(f"key is duplicated: {key}")
        seen.add(key)

    # 2. discord_id
    everyone_count = 0
    for role in bp.roles:
        if role.discord_id == EVERYONE:
            everyone_count += 1
            if role.name != EVERYONE:
                raise ValueError(f"@everyone role must be named @everyone: {role.key}")
        elif role.discord_id is not None and not _ID_RE.match(role.discord_id):
            raise ValueError(f"discord_id must be digits: {role.key}")
    if everyone_count > 1:
        raise ValueError("@everyone is used by more than one role")
    for item in [*bp.categories, *bp.channels]:
        if item.discord_id is not None and not _ID_RE.match(item.discord_id):
            raise ValueError(f"discord_id must be digits: {item.key}")

    # 3. 権限の名前
    for role in bp.roles:
        names_to_bits(role.permissions)
        if len(set(role.permissions)) != len(role.permissions):
            raise ValueError(f"permission is listed twice: {role.key}")
    role_keys = {r.key for r in bp.roles}
    category_keys = {c.key for c in bp.categories}
    for holder in [*bp.categories, *bp.channels]:
        targets: set[str] = set()
        for ow in holder.overwrites:
            names_to_bits(ow.allow)
            names_to_bits(ow.deny)
            both = set(ow.allow) & set(ow.deny)
            if both:
                raise ValueError(f"{holder.key}: {ow.target} has the same permission in allow and deny: {sorted(both)[0]}")
            # 4. target
            if ow.target in (EVERYONE, BOT):
                pass
            elif ow.target.startswith("role:") and ow.target[len("role:"):] in role_keys:
                pass
            else:
                raise ValueError(f"{holder.key}: unknown overwrite target: {ow.target}")
            if ow.target in targets:
                raise ValueError(f"{holder.key}: overwrite target is duplicated: {ow.target}")
            targets.add(ow.target)
        # 6. @everyone の VIEW_CHANNEL を deny するなら @bot の allow に VIEW_CHANNEL
        hides = any(ow.target == EVERYONE and _VIEW_CHANNEL in ow.deny for ow in holder.overwrites)
        bot_sees = any(ow.target == BOT and _VIEW_CHANNEL in ow.allow for ow in holder.overwrites)
        if hides and not bot_sees:
            raise ValueError(f"{holder.key}: hides VIEW_CHANNEL from @everyone but @bot is not allowed VIEW_CHANNEL")

    # 5. チャンネルの category
    for ch in bp.channels:
        if ch.category is not None and ch.category not in category_keys:
            raise ValueError(f"{ch.key}: unknown category: {ch.category}")
        # 7. 文字のチャンネル名
        if any(c.isspace() for c in ch.name) or ch.name != ch.name.lower():
            raise ValueError(f"{ch.key}: text channel name must not contain spaces or upper-case letters")


BLUEPRINT_DIR = Path(__file__).resolve().parents[1] / "discord_blueprints"


def blueprint_path(tenant_id: int) -> Path:
    return BLUEPRINT_DIR / f"tenant_{tenant_id}.json"


def load_blueprint(path: Path) -> Blueprint:
    """JSON を読み、形と検査を通す。外れたら ValueError。"""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    bp = Blueprint.model_validate(raw)
    validate_blueprint(bp)
    return bp


# ---------------------------------------------------------------- 比べ方

def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _names_text(value: int) -> str:
    return ", ".join(bits_to_names(value & KNOWN_MASK))


def _ow_text(allow: int, deny: int) -> str:
    return f"allow=[{_names_text(allow)}]; deny=[{_names_text(deny)}]"


def _row(kind: str, key: str, name: str, field: str | None, before: str | None, after: str | None,
         reason: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"kind": kind, "key": key, "name": name, "field": field,
                           "before": before, "after": after}
    if reason is not None:
        row["reason"] = reason
    return row


def _keep(have: int, want: int) -> int:
    """表に無いビットは今の値を残し、表にあるビットは設計図の値にする（設計 改訂4）。"""
    return (have & ~KNOWN_MASK) | (want & KNOWN_MASK)


def _action(method: str, path: str, body: dict[str, Any], creates: str | None = None) -> dict[str, Any]:
    """反映で Discord に送る 1 回分。{guild}・{ref:…} の置き換えは反映する係が行う。"""
    return {"method": method, "path": path, "json": body, "creates": creates}


# アプリの役割の行の key の頭（第2段 2a-2）。設計図の key は ^[a-z0-9_]+$ なのでぶつからない
APP_ROLE_KEY_PREFIX = "app_role:"
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def hex_color_to_int(value: Any) -> int:
    """アプリの役割の色（'#RRGGBB'）を Discord の色の数にする。空や形が違うときは 0（色なし）。"""
    if isinstance(value, str) and _HEX_COLOR.match(value):
        return int(value[1:], 16)
    return 0


def _app_state(app: dict[str, Any], state: str, reason: str | None = None) -> dict[str, Any]:
    return {"role_id": int(app["id"]), "name": str(app["name"]), "state": state, "reason": reason}


def build_plan(
    bp: Blueprint,
    roles: list[dict[str, Any]],
    channels: list[dict[str, Any]],
    guild_id: str,
    bot_role_ids: Any,
    app_roles: list[dict[str, Any]] | None = None,
    notice_links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """設計図と Discord の今の姿の差を出す。Discord の返事そのものを受ける純粋な関数。

    app_roles: アプリの役割（id・name・color・discord_role_id）。None なら今までと同じ結果（第2段 2a-2）。
    notice_links: 知らせの送り先の行（blueprint_key・event_types・is_active）。None なら今までと同じ結果（第2段 2c）。
    """
    guild_id = str(guild_id)
    bot_ids = {str(i) for i in bot_role_ids}

    roles_by_id = {str(r.get("id")): r for r in roles}
    everyone = roles_by_id.get(guild_id)
    everyone_perms = _int(everyone.get("permissions")) if everyone else 0
    bot_roles = [roles_by_id[i] for i in bot_ids if i in roles_by_id]
    bot_perms = everyone_perms
    for r in bot_roles:
        bot_perms |= _int(r.get("permissions"))
    bot_admin = bool(bot_perms & _ADMINISTRATOR)
    bot_top = max((_int(r.get("position")) for r in bot_roles), default=0)
    managed_bot = sorted((r for r in bot_roles if r.get("managed")), key=lambda r: _int(r.get("id")))
    bot_target_id: str | None = str(managed_bot[0].get("id")) if managed_bot else None

    d_roles = [r for r in roles if not r.get("managed") and str(r.get("id")) != guild_id]
    d_cats = [c for c in channels if c.get("type") == 4]
    d_chans = [c for c in channels if c.get("type") == 0]
    cats_by_id = {str(c.get("id")): c for c in d_cats}

    used_roles: set[str] = set()
    used_cats: set[str] = set()
    used_chans: set[str] = set()

    # rows[stage] = [(row, is_blocked)]
    changes: list[list[dict[str, Any]]] = [[], [], [], [], []]
    blocked: list[list[dict[str, Any]]] = [[], [], [], [], []]

    actions: list[list[dict[str, Any]]] = [[], [], [], [], []]

    def emit(stage: int, row: dict[str, Any], reason: str | None = None,
             action: dict[str, Any] | None = None) -> None:
        if reason is None:
            if action is None:
                raise AssertionError("a change row needs an action")
            changes[stage].append(row)
            actions[stage].append(action)
        else:
            row = dict(row)
            row["reason"] = reason
            blocked[stage].append(row)

    def perm_lacks(value: int) -> bool:
        return not bot_admin and bool((value & KNOWN_MASK) & ~bot_perms)

    # ---- ロール
    role_ids: dict[str, str] = {}  # bp key → Discord の番号（見つかったものだけ）
    role_state: dict[str, str] = {}  # bp key → "found" | "new" | "blocked:<reason>"
    for role in bp.roles:
        found: dict[str, Any] | None = None
        problem: str | None = None
        if role.discord_id == EVERYONE:
            found = everyone
            if found is None:
                problem = "missing_on_discord"
        elif role.discord_id:
            found = next((r for r in d_roles if str(r.get("id")) == role.discord_id), None)
            if found is None:
                problem = "missing_on_discord"
        else:
            same = [r for r in d_roles if r.get("name") == role.name]
            if len(same) > 1:
                problem = "ambiguous"
                used_roles.update(str(r.get("id")) for r in same)
            elif same:
                found = same[0]
        if problem:
            role_state[role.key] = f"blocked:{problem}"
            emit(0, _row("update_role", role.key, role.name, None, None, None), problem)
            continue
        want_perms = names_to_bits(role.permissions)
        if found is None:
            role_state[role.key] = "new"
            after = (f"name={role.name}; color={role.color}; hoist={_bool_text(role.hoist)}; "
                     f"mentionable={_bool_text(role.mentionable)}; permissions=[{_names_text(want_perms)}]")
            reason = "permission_bot_lacks" if perm_lacks(want_perms) else None
            create_json = {"name": role.name, "permissions": str(want_perms),
                           "colors": {"primary_color": role.color}, "hoist": role.hoist,
                           "mentionable": role.mentionable}
            emit(0, _row("create_role", role.key, role.name, None, None, after), reason,
                 _action("POST", "/guilds/{guild}/roles", create_json, f"role:{role.key}"))
            continue
        fid = str(found.get("id"))
        used_roles.add(fid)
        role_ids[role.key] = fid
        role_state[role.key] = "found"
        is_everyone = fid == guild_id
        above = _int(found.get("position")) >= bot_top
        diffs: list[tuple[str, str, str]] = []
        if found.get("name") != role.name:
            diffs.append(("name", str(found.get("name")), role.name))
        if _int(found.get("color")) != role.color:
            diffs.append(("color", str(_int(found.get("color"))), str(role.color)))
        if bool(found.get("hoist")) != role.hoist:
            diffs.append(("hoist", _bool_text(bool(found.get("hoist"))), _bool_text(role.hoist)))
        if bool(found.get("mentionable")) != role.mentionable:
            diffs.append(("mentionable", _bool_text(bool(found.get("mentionable"))), _bool_text(role.mentionable)))
        have_perms = _int(found.get("permissions"))
        if (have_perms & KNOWN_MASK) != (want_perms & KNOWN_MASK):
            diffs.append(("permissions", _names_text(have_perms), _names_text(want_perms)))
        role_path = "/guilds/{guild}/roles/" + ("{guild}" if is_everyone else fid)
        role_bodies: dict[str, dict[str, Any]] = {
            "name": {"name": role.name},
            "color": {"colors": {"primary_color": role.color}},
            "hoist": {"hoist": role.hoist},
            "mentionable": {"mentionable": role.mentionable},
            "permissions": {"permissions": str(_keep(have_perms, want_perms))},
        }
        for field, before, after in diffs:
            reason = None
            if field == "name" and is_everyone:
                reason = "everyone_name"
            elif above:
                reason = "role_above_bot"
            elif field == "permissions" and perm_lacks(want_perms):
                reason = "permission_bot_lacks"
            emit(0, _row("update_role", role.key, role.name, field, before, after), reason,
                 _action("PATCH", role_path, role_bodies[field]))

    # ---- アプリの役割（第2段 2a-2・設計 S2-3 D2-1）。設計図のロールの後に見る
    app_role_states: list[dict[str, Any]] = []
    if app_roles is not None:
        bp_role_names = {role.name for role in bp.roles}
        linked_ids = {str(a["discord_role_id"]) for a in app_roles if a.get("discord_role_id")}
        d_roles_by_id = {str(r.get("id")): r for r in d_roles}
        for app in sorted(app_roles, key=lambda a: int(a["id"])):
            key = f"{APP_ROLE_KEY_PREFIX}{int(app['id'])}"
            name = str(app["name"])
            color = hex_color_to_int(app.get("color"))
            linked = str(app["discord_role_id"]) if app.get("discord_role_id") else None
            if name in bp_role_names:
                emit(0, _row("update_role", key, name, None, None, None), "name_in_blueprint")
                app_role_states.append(_app_state(app, "blocked", "name_in_blueprint"))
                continue
            if linked is not None:
                found = d_roles_by_id.get(linked)
                if found is None:
                    emit(0, _row("update_role", key, name, None, None, None), "app_role_missing_on_discord")
                    app_role_states.append(_app_state(app, "blocked", "app_role_missing_on_discord"))
                    continue
                if linked in used_roles:
                    emit(0, _row("update_role", key, name, None, None, None), "app_role_link_in_use")
                    app_role_states.append(_app_state(app, "blocked", "app_role_link_in_use"))
                    continue
                used_roles.add(linked)
                app_diffs: list[tuple[str, str, str]] = []
                if found.get("name") != name:
                    app_diffs.append(("name", str(found.get("name")), name))
                if _int(found.get("color")) != color:
                    app_diffs.append(("color", str(_int(found.get("color"))), str(color)))
                if not app_diffs:
                    app_role_states.append(_app_state(app, "unchanged"))
                    continue
                app_above = _int(found.get("position")) >= bot_top
                for field, before, after in app_diffs:
                    body = {"name": name} if field == "name" else {"colors": {"primary_color": color}}
                    emit(0, _row("update_role", key, name, field, before, after),
                         "role_above_bot" if app_above else None,
                         _action("PATCH", "/guilds/{guild}/roles/" + linked, body))
                if app_above:
                    app_role_states.append(_app_state(app, "blocked", "role_above_bot"))
                else:
                    app_role_states.append(_app_state(app, "update"))
                continue
            same = [r for r in d_roles if r.get("name") == name
                    and str(r.get("id")) not in used_roles and str(r.get("id")) not in linked_ids]
            if len(same) > 1:
                used_roles.update(str(r.get("id")) for r in same)
                emit(0, _row("update_role", key, name, None, None, None), "ambiguous")
                app_role_states.append(_app_state(app, "blocked", "ambiguous"))
                continue
            if same:
                fid = str(same[0].get("id"))
                used_roles.add(fid)
                emit(0, _row("link_role", key, name, None, None, fid), None,
                     _action("DB", "", {"discord_role_id": fid}))
                app_role_states.append(_app_state(app, "link"))
                continue
            emit(0, _row("create_role", key, name, None, None, f"name={name}; color={color}"), None,
                 _action("POST", "/guilds/{guild}/roles",
                         {"name": name, "permissions": "0", "colors": {"primary_color": color},
                          "hoist": False, "mentionable": False}, key))
            app_role_states.append(_app_state(app, "create"))

    # ---- 上書き（カテゴリ・チャンネル共通）
    def target_id(target: str) -> tuple[str | None, str | None]:
        """設計図の相手 → (Discord の番号, 使えない理由)。"""
        if target == EVERYONE:
            return guild_id, None
        if target == BOT:
            return (bot_target_id, None) if bot_target_id else (None, "bot_role_missing")
        key = target[len("role:"):]
        state = role_state.get(key, "new")
        if state.startswith("blocked:"):
            return None, state.split(":", 1)[1]
        return role_ids.get(key), None

    def target_ref(target: str) -> str | None:
        """設計図の相手 → 送るときの相手の番号（サーバーの番号と、この反映で作る物は置き換えの印）。"""
        if target == EVERYONE:
            return "{guild}"
        if target == BOT:
            return bot_target_id
        key = target[len("role:"):]
        if role_state.get(key, "new") == "new":
            return "{ref:role:" + key + "}"
        rid = role_ids.get(key)
        return "{guild}" if rid == guild_id else rid

    def overwrite_list(overwrites: list[Any]) -> list[dict[str, Any]]:
        return [
            {"id": target_ref(ow.target), "type": 0,
             "allow": str(names_to_bits(ow.allow)), "deny": str(names_to_bits(ow.deny))}
            for ow in overwrites
        ]

    def overwrite_issue(allow: int, deny: int) -> str | None:
        if not bot_admin and ((allow | deny) & _MANAGE_ROLES):
            return "overwrite_manage_roles"
        if perm_lacks(allow | deny):
            return "permission_bot_lacks"
        return None

    def bp_overwrite_summary(overwrites: list[Any]) -> str:
        parts = []
        for ow in overwrites:
            parts.append(f"{ow.target}: {_ow_text(names_to_bits(ow.allow), names_to_bits(ow.deny))}")
        return "; ".join(parts)

    def create_issue(overwrites: list[Any]) -> str | None:
        for ow in overwrites:
            _, why = target_id(ow.target)
            if why:
                return why
            issue = overwrite_issue(names_to_bits(ow.allow), names_to_bits(ow.deny))
            if issue:
                return issue
        return None

    delete_ow: list[dict[str, Any]] = []

    def compare_overwrites(holder: Any, found: dict[str, Any], parent_name: str | None) -> None:
        current = {str(o.get("id")): o for o in (found.get("permission_overwrites") or []) if o.get("type") == 0}
        written: set[str] = set()
        for ow in holder.overwrites:
            tid, why = target_id(ow.target)
            allow, deny = names_to_bits(ow.allow), names_to_bits(ow.deny)
            field = f"overwrite:{ow.target}"
            if why:
                emit(3, _row("update_overwrite", holder.key, holder.name, field, None, None), why)
                continue
            if tid is not None:
                written.add(tid)
            cur = current.get(tid) if tid is not None else None
            cur_allow = _int(cur.get("allow")) if cur else 0
            cur_deny = _int(cur.get("deny")) if cur else 0
            if (cur_allow & KNOWN_MASK) == (allow & KNOWN_MASK) and (cur_deny & KNOWN_MASK) == (deny & KNOWN_MASK):
                continue
            emit(3, _row("update_overwrite", holder.key, holder.name, field,
                         _ow_text(cur_allow, cur_deny), _ow_text(allow, deny)), overwrite_issue(allow, deny),
                 _action("PUT", f"/channels/{found.get('id')}/permissions/{target_ref(ow.target)}",
                         {"type": 0, "allow": str(_keep(cur_allow, allow)), "deny": str(_keep(cur_deny, deny))}))
        for oid, cur in current.items():
            if oid in written:
                continue
            if oid == guild_id:
                label = EVERYONE
            elif oid == bot_target_id:
                label = BOT
            else:
                r = roles_by_id.get(oid)
                if r is None or r.get("managed"):
                    continue
                label = str(r.get("name"))
            delete_ow.append({"kind": "overwrite", "discord_id": str(found.get("id")), "name": holder.name,
                              "parent_name": parent_name, "target": label, "_sort": (_int(found.get("id")), _int(oid))})

    # ---- カテゴリ
    cat_ids: dict[str, str] = {}
    cat_state: dict[str, str] = {}
    for cat in bp.categories:
        found = None
        problem = None
        if cat.discord_id:
            found = next((c for c in d_cats if str(c.get("id")) == cat.discord_id), None)
            if found is None:
                problem = "missing_on_discord"
        else:
            same = [c for c in d_cats if c.get("name") == cat.name]
            if len(same) > 1:
                problem = "ambiguous"
                used_cats.update(str(c.get("id")) for c in same)
            elif same:
                found = same[0]
        if problem:
            cat_state[cat.key] = f"blocked:{problem}"
            emit(1, _row("update_category", cat.key, cat.name, None, None, None), problem)
            continue
        if found is None:
            cat_state[cat.key] = "new"
            after = f"name={cat.name}; overwrites=[{bp_overwrite_summary(cat.overwrites)}]"
            emit(1, _row("create_category", cat.key, cat.name, None, None, after), create_issue(cat.overwrites),
                 _action("POST", "/guilds/{guild}/channels",
                         {"name": cat.name, "type": 4, "permission_overwrites": overwrite_list(cat.overwrites)},
                         f"category:{cat.key}"))
            continue
        fid = str(found.get("id"))
        used_cats.add(fid)
        cat_ids[cat.key] = fid
        cat_state[cat.key] = "found"
        if found.get("name") != cat.name:
            emit(1, _row("update_category", cat.key, cat.name, "name", str(found.get("name")), cat.name),
                 None, _action("PATCH", f"/channels/{fid}", {"name": cat.name}))
        compare_overwrites(cat, found, None)

    # ---- チャンネル
    chan_ref: dict[str, str | None] = {}  # bp key → つなぎで送る部屋の番号か置き換えの印（第2段 2c）
    bp_cats = {c.key: c for c in bp.categories}
    for ch in bp.channels:
        parent_state = cat_state.get(ch.category) if ch.category else None
        if parent_state and parent_state.startswith("blocked:"):
            # 親が分からないので直さない。ただし Discord にある物は「消す候補」に出さない
            if ch.discord_id:
                used_chans.update(str(c.get("id")) for c in d_chans if str(c.get("id")) == ch.discord_id)
            else:
                used_chans.update(str(c.get("id")) for c in d_chans if c.get("name") == ch.name)
            chan_ref[ch.key] = None
            emit(2, _row("update_channel", ch.key, ch.name, None, None, None), parent_state.split(":", 1)[1])
            continue
        parent_id = cat_ids.get(ch.category) if ch.category else None
        # 送るときの親の番号：見つかっていればその番号、この反映で作るなら置き換えの印
        parent_ref = parent_id
        if parent_ref is None and ch.category and parent_state == "new":
            parent_ref = "{ref:category:" + ch.category + "}"
        parent_name = bp_cats[ch.category].name if ch.category else None
        found = None
        problem = None
        if ch.discord_id:
            found = next((c for c in d_chans if str(c.get("id")) == ch.discord_id), None)
            if found is None:
                problem = "missing_on_discord"
        elif ch.category is None or parent_id is not None:
            same = [
                c for c in d_chans
                if c.get("name") == ch.name and (str(c["parent_id"]) if c.get("parent_id") else None) == parent_id
            ]
            if len(same) > 1:
                problem = "ambiguous"
                used_chans.update(str(c.get("id")) for c in same)
            elif same:
                found = same[0]
        if problem:
            chan_ref[ch.key] = None
            emit(2, _row("update_channel", ch.key, ch.name, None, None, None), problem)
            continue
        if found is None:
            after = (f"name={ch.name}; parent={parent_name}; topic={ch.topic or ''}; "
                     f"overwrites=[{bp_overwrite_summary(ch.overwrites)}]")
            create_json: dict[str, Any] = {"name": ch.name, "type": 0,
                                           "permission_overwrites": overwrite_list(ch.overwrites)}
            if ch.topic:
                create_json["topic"] = ch.topic
            if parent_ref is not None:
                create_json["parent_id"] = parent_ref
            issue = create_issue(ch.overwrites)
            emit(2, _row("create_channel", ch.key, ch.name, None, None, after), issue,
                 _action("POST", "/guilds/{guild}/channels", create_json, f"channel:{ch.key}"))
            chan_ref[ch.key] = None if issue else "{ref:channel:" + ch.key + "}"
            continue
        chan_ref[ch.key] = str(found.get("id"))
        chan_path = f"/channels/{found.get('id')}"
        used_chans.add(str(found.get("id")))
        if found.get("name") != ch.name:
            emit(2, _row("update_channel", ch.key, ch.name, "name", str(found.get("name")), ch.name),
                 None, _action("PATCH", chan_path, {"name": ch.name}))
        if (found.get("topic") or "") != (ch.topic or ""):
            emit(2, _row("update_channel", ch.key, ch.name, "topic", found.get("topic") or None, ch.topic or None),
                 None, _action("PATCH", chan_path, {"topic": ch.topic or ""}))
        cur_parent = str(found["parent_id"]) if found.get("parent_id") else None
        if cur_parent != parent_id:
            cur_parent_name = str(cats_by_id[cur_parent].get("name")) if cur_parent in cats_by_id else cur_parent
            emit(2, _row("update_channel", ch.key, ch.name, "parent", cur_parent_name, parent_name),
                 None, _action("PATCH", chan_path, {"parent_id": parent_ref}))
        compare_overwrites(ch, found, parent_name)

    # ---- 知らせの部屋のつなぎ（第2段 2c・設計 D2-11）。webhook を作り、送り先の行は反映のあとアプリが書く
    if notice_links is not None:
        linked = {str(x.get("blueprint_key")) for x in notice_links if x.get("blueprint_key")}
        manual_events: set[str] = set()
        for x in notice_links:
            if x.get("blueprint_key") or not x.get("is_active"):
                continue
            raw = x.get("event_types")
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw or "[]")
                except ValueError:
                    raw = []
            if isinstance(raw, list):
                manual_events.update(str(e) for e in raw)
        for ch in bp.channels:
            event = NOTICE_ROOMS.get(ch.key)
            if event is None or ch.key in linked:
                continue
            note = "notice_other_route" if event in manual_events else None
            row = _row("link_notice", ch.key, ch.name, None, None, f"event={event}", note)
            ref = chan_ref.get(ch.key)
            if ref is None:
                emit(4, row, "notice_room_unavailable")
                continue
            action = _action("POST", f"/channels/{ref}/webhooks", {"name": NOTICE_WEBHOOK_NAME})
            action["webhook_for"] = ch.key
            emit(4, row, None, action)

    # ---- 消す候補
    deletes: list[list[dict[str, Any]]] = [[], [], [], []]
    for r in sorted(d_roles, key=lambda x: _int(x.get("id"))):
        if str(r.get("id")) not in used_roles:
            deletes[0].append({"kind": "role", "discord_id": str(r.get("id")), "name": r.get("name"),
                               "parent_name": None, "target": None})
    for c in sorted(d_cats, key=lambda x: _int(x.get("id"))):
        if str(c.get("id")) not in used_cats:
            deletes[1].append({"kind": "category", "discord_id": str(c.get("id")), "name": c.get("name"),
                               "parent_name": None, "target": None})
    for c in sorted(d_chans, key=lambda x: _int(x.get("id"))):
        if str(c.get("id")) not in used_chans:
            pid = str(c["parent_id"]) if c.get("parent_id") else None
            pname = cats_by_id[pid].get("name") if pid in cats_by_id else None
            deletes[2].append({"kind": "channel", "discord_id": str(c.get("id")), "name": c.get("name"),
                               "parent_name": pname, "target": None})
    for item in sorted(delete_ow, key=lambda x: x["_sort"]):
        item = dict(item)
        item.pop("_sort")
        deletes[3].append(item)

    out_changes = [row for stage in changes for row in stage]
    out_blocked = [row for stage in blocked for row in stage]
    out_deletes = [row for stage in deletes for row in stage]
    out_actions = [a for stage in actions for a in stage]
    digest = hashlib.sha256(
        json.dumps(
            {"changes": out_changes, "blocked": out_blocked, "delete_candidates": out_deletes},
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode()
    ).hexdigest()
    out: dict[str, Any] = {"changes": out_changes, "blocked": out_blocked, "delete_candidates": out_deletes,
                           "plan_digest": digest, "actions": out_actions}
    if app_roles is not None:
        out["app_roles"] = app_role_states
    return out
