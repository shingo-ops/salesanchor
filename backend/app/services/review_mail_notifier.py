from __future__ import annotations

"""
review@salesanchor.jp 新着メール → Discord 通知サービス。

設計:
  - IMAP over SSL で接続し INBOX を監視する。
  - BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)] のみ取得（本文・添付は絶対に読まない）。
  - 通知済み UID を Redis に記録し重複通知を防ぐ。
  - Discord webhook は REVIEW_MAIL_DISCORD_WEBHOOK を使用（専用チャンネル）。
  - IMAP 未設定・接続失敗・Redis 障害のいずれでも本体を止めない。

セキュリティ:
  - メール本文・添付・Firebase oobCode は Discord に投稿しない。
  - REVIEW_MAIL_IMAP_PASSWORD はログに出力しない。
  - REVIEW_MAIL_DISCORD_MENTION は <@USER_ID> / <@&ROLE_ID> 形式のみ許可する。
  - allowed_mentions の parse:[] により件名・差出人由来の @everyone や <@ID> が
    Discord 上でメンションとして発火しないようにする。
"""

import email
import email.header
import imaplib
import logging
import os
import re
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    import redis as redis_module

logger = logging.getLogger(__name__)

_IMAP_HOST = os.getenv("REVIEW_MAIL_IMAP_HOST", "")
_IMAP_PORT = int(os.getenv("REVIEW_MAIL_IMAP_PORT", "993"))
_IMAP_USER = os.getenv("REVIEW_MAIL_IMAP_USER", "")
_IMAP_PASSWORD = os.getenv("REVIEW_MAIL_IMAP_PASSWORD", "")
_WEBMAIL_URL = os.getenv("REVIEW_MAIL_WEBMAIL_URL", "")
_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_DISCORD_WEBHOOK = os.getenv("REVIEW_MAIL_DISCORD_WEBHOOK", "")
_DISCORD_MENTION = os.getenv("REVIEW_MAIL_DISCORD_MENTION", "")

_VALID_MENTION_RE = re.compile(r"^<@(?P<type>[!&]?)(?P<id>\d{17,20})>$")

_REDIS_KEY_PREFIX = "review_mail:notified:"
_REDIS_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 日
_MAX_SUBJECT_CHARS = 200
_MAX_FROM_CHARS = 300
_MAX_DISCORD_CHARS = 1800


def _parse_mention(raw: str) -> tuple[str | None, dict]:
    """REVIEW_MAIL_DISCORD_MENTION を検証し (mention_str, allowed_mentions) を返す。

    Returns:
        (mention_str, allowed_mentions):
          - mention_str: 有効なメンション文字列 or None（未設定・不正形式）
          - allowed_mentions: Discord payload 用辞書。parse:[] で誤発火防止済み。
    """
    raw = raw.strip()
    if not raw:
        return None, {"parse": []}
    m = _VALID_MENTION_RE.match(raw)
    if not m:
        logger.warning("[review_mail] REVIEW_MAIL_DISCORD_MENTION の形式が不正: %r (skip)", raw)
        return None, {"parse": []}
    kind = "roles" if m.group("type") == "&" else "users"
    return raw, {"parse": [], kind: [m.group("id")]}


def _is_configured() -> bool:
    return bool(_IMAP_HOST and _IMAP_USER and _IMAP_PASSWORD)


def _decode_mime_header(value: str) -> str:
    """RFC 2047 エンコードされたヘッダ値を UTF-8 文字列にデコードする。"""
    parts = email.header.decode_header(value)
    decoded: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _get_redis() -> "redis_module.Redis | None":
    """同期 Redis クライアントを返す。接続失敗時は None を返す。"""
    try:
        import redis

        client: redis_module.Redis = redis.from_url(_REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:
        logger.warning("[review_mail] Redis 接続失敗 (skip): %s", exc)
        return None


def _is_notified(client: "redis_module.Redis", uid: str) -> bool:
    try:
        return bool(client.exists(f"{_REDIS_KEY_PREFIX}{uid}"))
    except Exception as exc:
        logger.warning("[review_mail] Redis 確認失敗 uid=%s: %s", uid, exc)
        return False


def _mark_notified(client: "redis_module.Redis", uid: str) -> None:
    try:
        client.set(f"{_REDIS_KEY_PREFIX}{uid}", "1", ex=_REDIS_TTL_SECONDS)
    except Exception as exc:
        logger.warning("[review_mail] Redis 書き込み失敗 uid=%s: %s", uid, exc)


def _build_discord_content(
    from_addr: str, subject: str, date_str: str, mention: str | None = None
) -> str:
    """Discord に投稿するメッセージを組み立てる。本文・oobCode は含まない。"""
    prefix = f"{mention}\n" if mention else ""
    return (
        f"{prefix}"
        "📩 **Sales Anchor メール通知**\n\n"
        f"宛先: review@salesanchor.jp\n"
        f"差出人: {from_addr[:_MAX_FROM_CHARS]}\n"
        f"件名: {subject[:_MAX_SUBJECT_CHARS]}\n"
        f"受信時刻: {date_str}\n\n"
        f"さくらWebメールで確認:\n"
        f"{_WEBMAIL_URL}\n\n"
        "※メール本文・再設定リンク・添付ファイルはDiscordには表示しません。"
    )


def _post_discord(content: str, allowed_mentions: dict | None = None) -> bool:
    """Discord webhook に同期 POST する。失敗しても例外を投げない。"""
    webhook = _DISCORD_WEBHOOK.strip()
    if not webhook:
        logger.info("[review_mail] Discord webhook 未設定 (skip)")
        return False
    payload: dict = {
        "content": content[:_MAX_DISCORD_CHARS],
        "username": "Sales Anchor メール通知",
        "allowed_mentions": allowed_mentions if allowed_mentions is not None else {"parse": []},
    }
    try:
        resp = httpx.post(webhook, json=payload, timeout=10.0)
        if resp.status_code >= 400:
            logger.warning(
                "[review_mail] Discord webhook HTTP %s: %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
        return True
    except Exception as exc:
        logger.warning("[review_mail] Discord POST 失敗: %s", exc)
        return False


def check_and_notify() -> int:
    """INBOX を IMAP で確認し、未通知メールを Discord に通知する。

    Returns:
        通知した件数（0 = 設定未完了・Redis 不能・新着なし・全件通知済みのいずれか）

    例外を外に出さない。失敗はすべてログで記録して 0 を返す。

    Redis 不能時の設計:
        重複排除ができない状態では 5 分ごとに同じメールを再通知してしまう。
        本体障害を起こすより再通知させないことを優先し、Redis 不能なら即 return 0。
    """
    if not _is_configured():
        logger.info("[review_mail] IMAP 設定未完了 (skip: HOST/USER/PASSWORD を確認)")
        return 0

    mention_str, allowed_mentions = _parse_mention(_DISCORD_MENTION)

    redis_client = _get_redis()
    if redis_client is None:
        # Redis 不能 = 重複排除不能 → 再通知リスクを避けるため全処理をスキップ
        logger.warning("[review_mail] Redis 使用不可 — 重複通知防止不能のためスキップ")
        return 0

    try:
        conn = imaplib.IMAP4_SSL(_IMAP_HOST, _IMAP_PORT)
    except Exception as exc:
        logger.warning("[review_mail] IMAP 接続失敗: %s", exc)
        return 0

    try:
        conn.login(_IMAP_USER, _IMAP_PASSWORD)
        conn.select("INBOX")

        _, data = conn.uid("search", None, "ALL")
        if not data or not data[0]:
            return 0

        uids: list[bytes] = data[0].split()
        notified_count = 0

        for uid_bytes in uids:
            uid = uid_bytes.decode()

            if _is_notified(redis_client, uid):
                continue

            try:
                _, msg_data = conn.uid(
                    "fetch",
                    uid_bytes,
                    "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])",
                )
            except Exception as exc:
                logger.warning("[review_mail] メールヘッダ取得失敗 uid=%s: %s", uid, exc)
                continue

            if not msg_data or not msg_data[0]:
                continue

            raw_header = msg_data[0][1]
            if isinstance(raw_header, bytes):
                msg = email.message_from_bytes(raw_header)
            else:
                msg = email.message_from_string(str(raw_header))

            subject = _decode_mime_header(msg.get("Subject", "(件名なし)"))
            from_addr = _decode_mime_header(msg.get("From", "(不明)"))
            date_str = msg.get("Date", "(不明)")

            content = _build_discord_content(from_addr, subject, date_str, mention=mention_str)

            if _post_discord(content, allowed_mentions=allowed_mentions):
                _mark_notified(redis_client, uid)
                notified_count += 1

        return notified_count

    except Exception as exc:
        logger.warning("[review_mail] IMAP 処理中エラー: %s", exc)
        return 0
    finally:
        try:
            conn.logout()
        except Exception:
            pass


__all__ = ["check_and_notify"]
