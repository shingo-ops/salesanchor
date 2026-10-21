"""閲覧者向け文面のテンプレート（ADR-1019 段11 便1）。

コードに持つのは「台帳」（9件の鍵・送り方・差し込み項目の集合・画面の名前の i18n キー）だけ。
文面の本文は public.viewer_message_templates（DB）が正本（便2 で送る側 9件も DB から読む。コードに文面の写しは持たない）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from string import Formatter
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.discord_gateway import viewer_bot_texts

logger = logging.getLogger(__name__)

BODY_MAX_CHARS = 1800
AUTO_MAX_CHARS = 2000  # Discord の1通の上限。自動で送る文は差し込み後にこれを超えたら送らない（N-3）
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


async def load_body(db: AsyncSession, key: str) -> str | None:
    """DB の本文を読み、検査に通れば返す。行が無い・検査に通らないときは None（検査の例外は外へ出さない）。

    DB そのものの失敗は呼び出し側へ上がる（握りつぶすと、開いたトランザクションが壊れたまま進むため）。
    """
    if key not in _BY_KEY:
        return None
    row = (
        await db.execute(
            text("SELECT body FROM public.viewer_message_templates WHERE key = :k"), {"k": key}
        )
    ).first()
    if row is None:
        logger.warning("viewer template missing: key=%s", key)
        return None
    body = row[0]
    try:
        validate(key, body)
    except TemplateInvalid as exc:
        logger.warning("viewer template invalid: key=%s code=%s", key, exc.code)
        return None
    return body


def render(key: str, body: str, **values: object) -> str | None:
    """検査済みの本文に値を差し込む。失敗は None（例外を外へ出さない）。

    作り直し案内は、LINE名が空なら頭の「さん、」を外す。自動で送る文は差し込み後 2000 文字超で None。
    手で送る文（コピー用）は長さで落とさない。
    """
    spec = _BY_KEY.get(key)
    if spec is None:
        return None
    if spec.requires_line_name_prefix:
        values = {**values, "line_name": str(values.get("line_name") or "").strip()}
    try:
        validate(key, body)
        text_ = body.format(**{p: values[p] for p in spec.placeholders})
    except (TemplateInvalid, KeyError, ValueError, IndexError, AttributeError):
        logger.warning("viewer template render failed: key=%s", key)
        return None
    if spec.requires_line_name_prefix and not values["line_name"]:
        text_ = text_.removeprefix("さん、")
    if spec.send_mode == "auto" and len(text_) > AUTO_MAX_CHARS:
        logger.warning("viewer template too long after render: key=%s len=%d", key, len(text_))
        return None
    return text_


async def load_rendered(db: AsyncSession, key: str, **values: object) -> str | None:
    """load_body と render をまとめたもの。読めない・検査に通らない・差し込めないときは None。"""
    body = await load_body(db, key)
    if body is None:
        return None
    return render(key, body, **values)


class TemplateConflict(Exception):
    """他の人が先に直した（または先に作った）。"""


async def save_body(
    db: AsyncSession,
    key: str,
    body: str,
    expected_updated_at: datetime | None,
    user_id: int,
) -> None:
    """本文を保存する（commit は呼び出し側）。検査に通らなければ TemplateInvalid、競合は TemplateConflict。

    expected_updated_at が None: 行が無いときだけ INSERT（ON CONFLICT DO NOTHING で件数0なら競合）。
    あり: updated_at が一致するときだけ UPDATE（比べるのは SQL。Python で文字列比較しない）。
    """
    validate(key, body)
    if expected_updated_at is None:
        res = await db.execute(
            text(
                "INSERT INTO public.viewer_message_templates (key, body, updated_by_user_id) "
                "VALUES (:k, :b, :u) ON CONFLICT (key) DO NOTHING"
            ),
            {"k": key, "b": body, "u": user_id},
        )
    else:
        if expected_updated_at.tzinfo is None:
            expected_updated_at = expected_updated_at.replace(tzinfo=timezone.utc)
        res = await db.execute(
            text(
                "UPDATE public.viewer_message_templates SET body = :b, updated_by_user_id = :u, "
                "updated_at = now() WHERE key = :k AND updated_at = :expected"
            ),
            {"k": key, "b": body, "u": user_id, "expected": expected_updated_at},
        )
    if not res.rowcount:
        raise TemplateConflict()


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
