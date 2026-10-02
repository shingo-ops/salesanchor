"""Discord への担当者名義送信（webhook 経由・ADR-159 便B）。

Bot の通常送信は表示名・アイコンを変えられないが、webhook 実行は username / avatar_url を
メッセージごとに上書きできる。チャンネルごとに webhook を 1 本作成して保管し、返信時にそれを使う。

### 方針

- send_as_staff は Bot 名義へのフォールバックを一切しない。失敗したら例外を投げて送らない（PO 決定 2026-10-01）。
- send_as_identity（サーバー名義の案内・ボタン・ウェルカム）も例外を投げるだけ。Bot 投稿へ戻す判断は呼び出し側
  （try_send_as_identity が None を返す。サーバー側の案内は欠落させないため Bot 投稿に戻す: PO 決定 2026-10-02）。
- webhook token は services/encryption.py（Fernet）で暗号化して保存する。ログ・例外文に token / 実行 URL を出さない。
- アイコン未登録の場合は avatar_url を省略する（Discord 標準アイコンと同じ表示）。
- webhook が消えていた（404/401）場合は保管行を消して 1 回だけ作り直し、1 回だけ再送する。
- 自動再試行は「確実に未送信」の場合だけ 1 回（429 で retry_after が小さい／接続前の失敗）。読み取りタイムアウト・5xx は二重送信を避けるため再試行しない。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import reset_tenant_context, tenant_table_ref
from app.services import encryption
from app.services.discord_guild_identity import GuildIdentity

logger = logging.getLogger(__name__)


_WEBHOOK_URL_TOKEN = re.compile(r"(/webhooks/[^/\s]+/)[^/?\s\"]+")
_REDACTED_LOGGER_PREFIXES = ("httpx", "httpcore")


def _redact_webhook_token(message: str) -> str:
    return _WEBHOOK_URL_TOKEN.sub(r"\1***", message)


def _install_log_redaction() -> None:
    """httpx / httpcore（子 logger を含む）の記録に出る webhook 実行 URL の token を伏せる。

    logger に付けた Filter は子 logger の記録に効かないため、記録の生成時（LogRecordFactory）に処理する。
    二重に装着しないよう目印属性で判定する。
    """
    previous = logging.getLogRecordFactory()
    if getattr(previous, "_redacts_webhook_token", False):
        return

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        if record.name.startswith(_REDACTED_LOGGER_PREFIXES):
            # 不正な log 呼び出し（引数の個数違い等）で呼び出し元に例外を投げない。失敗時は記録を変えない
            try:
                message = record.getMessage()
                if "/webhooks/" in message:
                    record.msg = _redact_webhook_token(message)
                    record.args = ()
            except Exception:
                pass
        return record

    factory._redacts_webhook_token = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(factory)


_install_log_redaction()

_DISCORD_API_BASE = "https://discord.com/api/v10"
_TIMEOUT_SEC = 10.0
_WEBHOOK_NAME = "Sales Anchor"
_USERNAME_MAX_LEN = 80
# Discord が username に使えないとする語（大文字小文字を区別しない）
_FORBIDDEN_USERNAME_WORDS = ("discord", "clyde")
# 429 の retry_after がこれを超える場合は待たずに失敗扱いにする（画面を長く止めない）
_MAX_RETRY_AFTER_SEC = 5.0
_RETRY_DELAY_SEC = 1.0
_GONE_STATUSES = (401, 404)


class DiscordWebhookError(Exception):
    """webhook 送信系エラーの基底。"""


class StaffNameInvalidError(DiscordWebhookError):
    """担当者の英語名が Discord の表示名として使えない。"""


class WebhookPermissionError(DiscordWebhookError):
    """Bot に Manage Webhooks 権限が無く webhook を作成できない。"""


class WebhookSendError(DiscordWebhookError):
    """再試行後も送信できなかった。"""


@dataclass(frozen=True)
class OutboundFile:
    filename: str
    data: bytes
    content_type: str


@dataclass(frozen=True)
class _Webhook:
    webhook_id: str
    token: str


def validate_username(given_name_en: str) -> str:
    """表示名（英語名の「名」）を検証して返す。1〜80 文字・discord / clyde を含まない。"""
    name = (given_name_en or "").strip()
    if not name or len(name) > _USERNAME_MAX_LEN:
        raise StaffNameInvalidError("length")
    lowered = name.lower()
    if any(word in lowered for word in _FORBIDDEN_USERNAME_WORDS):
        raise StaffNameInvalidError("forbidden_word")
    return name


def _bot_token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN") or ""
    if not token:
        logger.error("[discord_webhook] DISCORD_BOT_TOKEN が未設定")
        raise WebhookSendError("bot_token_missing")
    return token


async def _load_webhook(db: AsyncSession, tenant_id: int, channel_id: str) -> _Webhook | None:
    table = tenant_table_ref(db, tenant_id, "discord_channel_webhooks")
    result = await db.execute(
        text(
            f"SELECT webhook_id, webhook_token_encrypted FROM {table} "
            "WHERE channel_id = :channel_id AND tenant_id = :tenant_id"
        ),
        {"channel_id": channel_id, "tenant_id": tenant_id},
    )
    row = result.first()
    if row is None:
        return None
    try:
        return _Webhook(webhook_id=str(row[0]), token=encryption.decrypt(row[1]))
    except encryption.EncryptionError:
        # 復号できない行は使えない。消して作り直す（token は出さない）
        logger.warning("[discord_webhook] 保管 token の復号に失敗 channel=%s", channel_id)
        await _delete_webhook(db, tenant_id, channel_id)
        return None


async def _store_webhook(
    db: AsyncSession, tenant_id: int, channel_id: str, webhook: _Webhook,
) -> None:
    table = tenant_table_ref(db, tenant_id, "discord_channel_webhooks")
    await db.execute(
        text(
            f"INSERT INTO {table} (tenant_id, channel_id, webhook_id, webhook_token_encrypted) "
            "VALUES (:tenant_id, :channel_id, :webhook_id, :token) "
            "ON CONFLICT (channel_id) DO UPDATE SET "
            "webhook_id = excluded.webhook_id, "
            "webhook_token_encrypted = excluded.webhook_token_encrypted"
        ),
        {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "webhook_id": webhook.webhook_id,
            "token": encryption.encrypt(webhook.token),
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)


async def _delete_webhook(db: AsyncSession, tenant_id: int, channel_id: str) -> None:
    table = tenant_table_ref(db, tenant_id, "discord_channel_webhooks")
    await db.execute(
        text(f"DELETE FROM {table} WHERE channel_id = :channel_id AND tenant_id = :tenant_id"),
        {"channel_id": channel_id, "tenant_id": tenant_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)


async def _retry_pause(response: httpx.Response | None) -> bool:
    """再試行前の待機。待てない（retry_after が大きい）場合は False。"""
    if response is not None and response.status_code == 429:
        try:
            retry_after = float(response.json().get("retry_after", 1.0))
        except Exception:
            retry_after = 1.0
        if retry_after > _MAX_RETRY_AFTER_SEC:
            return False
        await asyncio.sleep(retry_after)
        return True
    await asyncio.sleep(_RETRY_DELAY_SEC)
    return True


async def _request_with_retry(
    *, label: str, send: Any,
) -> httpx.Response:
    """Discord がメッセージを作っていないと確実に言える場合だけ 1 回再試行する。

    顧客への二重送信を避けるため、再試行は次の 2 つに限る:
      - 429（レート制限。メッセージは作られていない。retry_after が小さいときだけ待つ）
      - 接続前の失敗（ConnectError / ConnectTimeout。リクエストは相手に届いていない）
    読み取りタイムアウトや 5xx は「送られたかもしれない」ため再試行せず失敗にする
    （担当者が「もう一度送る」で再送する）。

    send は引数なしで httpx.Response を返す coroutine 関数。例外・URL は token を含み得るためログに出さない。
    """
    for attempt in (1, 2):
        try:
            response = await send()
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.warning("[discord_webhook] %s connect error=%s attempt=%d", label, type(exc).__name__, attempt)
            if attempt == 2:
                raise WebhookSendError("network") from None
            await _retry_pause(None)
            continue
        except httpx.RequestError as exc:
            # リクエストが届いた可能性があるため再試行しない
            logger.warning("[discord_webhook] %s request error=%s（再試行しない）", label, type(exc).__name__)
            raise WebhookSendError("network") from None
        if response.status_code != 429 or attempt == 2:
            return response
        logger.warning("[discord_webhook] %s status=429 attempt=%d", label, attempt)
        if not await _retry_pause(response):
            return response
    raise WebhookSendError("unreachable")  # pragma: no cover


def _json_object(response: httpx.Response, *keys: str) -> dict[str, Any]:
    """成功応答の JSON から必要なキーを取り出す。形式が違えば WebhookSendError（500 にしない）。"""
    try:
        body = response.json()
        if not isinstance(body, dict) or any(key not in body for key in keys):
            raise KeyError("missing")
    except (ValueError, KeyError):
        logger.error("[discord_webhook] 想定外の応答形式 status=%d", response.status_code)
        raise WebhookSendError("malformed_response") from None
    return body


async def _create_webhook(
    db: AsyncSession, tenant_id: int, channel_id: str,
) -> _Webhook:
    """POST /channels/{id}/webhooks（avatar 指定なし）。作成して暗号化保管する。"""
    bot_token = _bot_token()
    url = f"{_DISCORD_API_BASE}/channels/{channel_id}/webhooks"
    headers = {"Authorization": f"Bot {bot_token}"}

    async def _send() -> httpx.Response:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SEC) as client:
            return await client.post(url, json={"name": _WEBHOOK_NAME}, headers=headers)

    response = await _request_with_retry(label=f"create channel={channel_id}", send=_send)
    if response.status_code == 403:
        logger.warning("[discord_webhook] webhook 作成が権限不足 channel=%s", channel_id)
        raise WebhookPermissionError(channel_id)
    if response.status_code not in (200, 201):
        logger.error(
            "[discord_webhook] webhook 作成失敗 channel=%s status=%d", channel_id, response.status_code,
        )
        raise WebhookSendError(f"create_status_{response.status_code}")
    body = _json_object(response, "id", "token")
    webhook = _Webhook(webhook_id=str(body["id"]), token=str(body["token"]))
    await _store_webhook(db, tenant_id, channel_id, webhook)
    return webhook


async def _execute_webhook(
    webhook: _Webhook,
    *,
    content: str | None,
    file: OutboundFile | None,
    username: str,
    avatar_url: str | None,
    components: list[dict[str, Any]] | None = None,
) -> httpx.Response:
    """POST /webhooks/{id}/{token}?wait=true。avatar_url が None なら省略する。

    components は application-owned webhook（Bot が作成した webhook）なら常に送れる（Discord docs: webhook.mdx）。
    """
    url = f"{_DISCORD_API_BASE}/webhooks/{webhook.webhook_id}/{webhook.token}"
    payload: dict[str, Any] = {"username": username}
    if avatar_url:
        payload["avatar_url"] = avatar_url
    if content is not None:
        payload["content"] = content
    if components:
        payload["components"] = components

    async def _send() -> httpx.Response:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SEC) as client:
            if file is None:
                return await client.post(url, params={"wait": "true"}, json=payload)
            return await client.post(
                url,
                params={"wait": "true"},
                data={"payload_json": json.dumps(payload)},
                files={"files[0]": (file.filename, file.data, file.content_type)},
            )

    return await _request_with_retry(label=f"execute webhook={webhook.webhook_id}", send=_send)


async def _send_via_webhook(
    db: AsyncSession,
    *,
    tenant_id: int,
    channel_id: str,
    username: str,
    avatar_url: str | None,
    content: str | None,
    file: OutboundFile | None,
    components: list[dict[str, Any]] | None,
) -> str:
    """webhook 取得（無ければ作成）→ 実行 → 消失時 1 回だけ作り直して再送。Discord メッセージ ID を返す。"""
    name = validate_username(username)
    webhook = await _load_webhook(db, tenant_id, channel_id)
    recreated = False
    while True:
        if webhook is None:
            webhook = await _create_webhook(db, tenant_id, channel_id)
            recreated = True
        response = await _execute_webhook(
            webhook,
            content=content,
            file=file,
            username=name,
            avatar_url=avatar_url,
            components=components,
        )
        if response.status_code in (200, 201):
            return str(_json_object(response, "id")["id"])
        if response.status_code in _GONE_STATUSES and not recreated:
            logger.warning("[discord_webhook] webhook 消失を検知 channel=%s → 作り直し", channel_id)
            await _delete_webhook(db, tenant_id, channel_id)
            webhook = None
            continue
        logger.error(
            "[discord_webhook] 送信失敗 channel=%s status=%d", channel_id, response.status_code,
        )
        raise WebhookSendError(f"execute_status_{response.status_code}")


async def send_as_staff(
    db: AsyncSession,
    *,
    tenant_id: int,
    channel_id: str,
    username: str,
    avatar_url: str | None = None,
    content: str | None = None,
    file: OutboundFile | None = None,
) -> str:
    """担当者名義で送信し、Discord メッセージ ID を返す。

    Raises:
        StaffNameInvalidError: username が使えない
        WebhookPermissionError: webhook 作成の権限が無い
        WebhookSendError: 再試行後も送れなかった（Bot 名義では送らない）
    """
    return await _send_via_webhook(
        db,
        tenant_id=tenant_id,
        channel_id=channel_id,
        username=username,
        avatar_url=avatar_url,
        content=content,
        file=file,
        components=None,
    )


async def send_as_identity(
    db: AsyncSession,
    *,
    tenant_id: int,
    channel_id: str,
    username: str,
    avatar_url: str | None = None,
    content: str | None = None,
    components: list[dict[str, Any]] | None = None,
) -> str:
    """任意の名前・アイコンで送信し（サーバー名義の案内用）、Discord メッセージ ID を返す。

    Raises:
        StaffNameInvalidError: username が使えない
        WebhookPermissionError: webhook 作成の権限が無い
        WebhookSendError: 再試行後も送れなかった
    """
    return await _send_via_webhook(
        db,
        tenant_id=tenant_id,
        channel_id=channel_id,
        username=username,
        avatar_url=avatar_url,
        content=content,
        file=None,
        components=components,
    )


async def try_send_as_identity(
    db: AsyncSession,
    *,
    tenant_id: int,
    channel_id: str,
    identity: GuildIdentity | None,
    content: str | None = None,
    components: list[dict[str, Any]] | None = None,
) -> str | None:
    """サーバー名義で送る。送れなければ None（呼び出し側が Bot 投稿に戻す）。

    identity が None（サーバー情報を取得できなかった）・名前が使えない・webhook 失敗のいずれでも
    例外は出さず warning を記録する。サーバー側の案内を欠落させないための方針。
    """
    if identity is None:
        logger.warning("[discord_webhook] サーバー情報なし → Bot 名義で送信 channel=%s", channel_id)
        return None
    try:
        return await send_as_identity(
            db,
            tenant_id=tenant_id,
            channel_id=channel_id,
            username=identity.name,
            avatar_url=identity.icon_url,
            content=content,
            components=components,
        )
    except DiscordWebhookError as exc:
        logger.warning(
            "[discord_webhook] サーバー名義送信に失敗 → Bot 名義で送信 channel=%s reason=%s",
            channel_id, type(exc).__name__,
        )
        return None
