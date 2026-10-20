"""閲覧者向け文面のテンプレート（ADR-1019 段11 便1）。

コードに持つのは「台帳」（9件の鍵・送り方・差し込み項目の集合・画面の名前の i18n キー）だけ。
文面の本文は public.viewer_message_templates（DB）が正本。便1 は読むだけで、送る側からは使わない。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from string import Formatter
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.discord_gateway import viewer_bot_texts

BODY_MAX_CHARS = 1800
_I18N = "superAdmin.viewerTemplates"


@dataclass(frozen=True)
class TemplateSpec:
    key: str
    send_mode: Literal["manual", "auto"]
    placeholders: tuple[str, ...]  # 並びは画面に出す順
    # 先頭が {line_name}さん、 で始まる必要があるもの（名前が空のとき頭の「さん、」を外すため。審査 B-3）
    requires_line_name_prefix: bool = False

    @property
    def name_key(self) -> str:
        return f"{_I18N}.names.{self.key}"

    @property
    def when_key(self) -> str:
        return f"{_I18N}.when.{self.key}"


LEDGER: tuple[TemplateSpec, ...] = (
    TemplateSpec("signup_request", "manual", ("signup_url",)),
    TemplateSpec("reissue_notice", "manual", ("line_name", "code", "expires", "invite_url"), True),
    TemplateSpec("reissue_notice_no_invite", "manual", ("line_name", "code", "expires"), True),
    TemplateSpec("room_welcome", "auto", ("email", "password")),
    TemplateSpec("room_recreated", "auto", ("email",)),
    TemplateSpec("notice_extended", "auto", ("until_date",)),
    TemplateSpec("notice_activated", "auto", ()),
    TemplateSpec("notice_suspended", "auto", ()),
    TemplateSpec("interview_request", "auto", ("expires_date",)),
)
_BY_KEY = {s.key: s for s in LEDGER}
LINE_NAME_PREFIX = "{line_name}さん、"


class TemplateInvalid(ValueError):
    """code: unknown_key | empty | too_long | bad_syntax | format_spec | placeholders | line_name_prefix"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def get_spec(key: str) -> TemplateSpec | None:
    return _BY_KEY.get(key)


def validate(key: str, body: object) -> None:
    """本文が台帳に合うか確かめる。合わなければ TemplateInvalid（例外の code で理由を区別）。"""
    spec = _BY_KEY.get(key)
    if spec is None:
        raise TemplateInvalid("unknown_key")
    if not isinstance(body, str) or body == "":
        raise TemplateInvalid("empty")
    if len(body) > BODY_MAX_CHARS:
        raise TemplateInvalid("too_long")
    try:
        parsed = list(Formatter().parse(body))  # 遅延評価なので回し切る（`abc}` `{abc` はここで ValueError）
    except ValueError:
        raise TemplateInvalid("bad_syntax") from None
    names: set[str] = set()
    for _literal, field_name, format_spec, conversion in parsed:
        if field_name is None:
            continue
        if format_spec or conversion:
            raise TemplateInvalid("format_spec")
        names.add(field_name)  # `.` `[` で切らず文字列のまま比べる（`{a.b}` `{a[0]}` `{}` `{0}` は集合に無く不可）
    if names != set(spec.placeholders):
        raise TemplateInvalid("placeholders")
    if spec.requires_line_name_prefix and not body.startswith(LINE_NAME_PREFIX):
        raise TemplateInvalid("line_name_prefix")


def build_copy_text(key: str, body: str) -> str | None:
    """コピー用の文。{signup_url} だけ入れ、人ごとの項目は {…} のまま。検査に通らない本文は None。"""
    spec = _BY_KEY.get(key)
    if spec is None:
        return None
    try:
        validate(key, body)
    except TemplateInvalid:
        return None
    values = {p: "{" + p + "}" for p in spec.placeholders}
    if "signup_url" in values:
        values["signup_url"] = viewer_bot_texts.SIGNUP_URL
    return body.format(**values)


def seed_bodies() -> dict[str, str]:
    """viewer_bot_texts.py の今の9定数（seed と verify が使う。便2 で消す）。"""
    T = viewer_bot_texts
    return {
        "signup_request": T.SIGNUP_REQUEST,
        "reissue_notice": T.REISSUE_NOTICE,
        "reissue_notice_no_invite": T.REISSUE_NOTICE_NO_INVITE,
        "room_welcome": T.ROOM_WELCOME,
        "room_recreated": T.ROOM_RECREATED,
        "notice_extended": T.NOTICE_EXTENDED,
        "notice_activated": T.NOTICE_ACTIVATED,
        "notice_suspended": T.NOTICE_SUSPENDED,
        "interview_request": T.INTERVIEW_REQUEST,
    }


async def list_rows(db: AsyncSession) -> list[dict]:
    """台帳の9件を台帳の順で必ず返す。DB に行が無い鍵は body=None。"""
    result = await db.execute(
        text(
            "SELECT t.key, t.body, t.updated_at, "
            "COALESCE(NULLIF(u.full_name, ''), u.username) AS updated_by_name "
            "FROM public.viewer_message_templates t "
            "LEFT JOIN public.users u ON u.id = t.updated_by_user_id"
        )
    )
    found: dict[str, tuple[str, datetime, str | None]] = {
        r[0]: (r[1], r[2], r[3]) for r in result.all()
    }
    rows: list[dict] = []
    for spec in LEDGER:
        hit = found.get(spec.key)
        body, updated_at, updated_by = hit if hit else (None, None, None)
        rows.append(
            {
                "key": spec.key,
                "body": body,
                "copy_text": build_copy_text(spec.key, body) if body is not None else None,
                "placeholders": list(spec.placeholders),
                "send_mode": spec.send_mode,
                "updated_at": updated_at,
                "updated_by_name": updated_by,
            }
        )
    return rows
