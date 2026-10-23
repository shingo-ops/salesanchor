from __future__ import annotations

"""
運用の受け箱 → さくらの点検・障害のメールを運用 Discord へ通知するサービス。

運用の受け箱を読み、さくらの点検・障害のメールの件名・作業日時・影響範囲だけを
運用の Discord に送る。本文はその 2 行以外を投稿もログもしない。
設計: docs/handoff/outage-recovery-watch/design.md §3-1-1（outage-recovery-watch 便3）

セキュリティ:
  - 本文は、送るメールに限り先頭 64KB だけ読む（BODY.PEEK なので既読にしない）。
  - 作業日時・影響範囲の 2 行以外（会員 ID・契約者名など）は Discord にもログにも出さない。
  - パスワード・webhook・件名・差出人はログに出さない。
  - allowed_mentions の parse:[] により @everyone 等が発火しないようにする。
"""

import email
import email.utils
import imaplib
import logging
import os
import re
import time

import httpx

from app.services.review_mail_notifier import _decode_mime_header, _get_redis

logger = logging.getLogger(__name__)

_IMAP_HOST = os.getenv("REVIEW_MAIL_IMAP_HOST", "")
_IMAP_PORT = int(os.getenv("REVIEW_MAIL_IMAP_PORT", "993"))
_IMAP_USER = os.getenv("OPS_MAIL_IMAP_USER", "")
_IMAP_PASSWORD = os.getenv("OPS_MAIL_IMAP_PASSWORD", "")
_DISCORD_WEBHOOK = os.getenv("OPS_MAIL_DISCORD_WEBHOOK", "")

NOTIFIED_KEY_PREFIX = "ops_mail:notified:"
LAST_SAKURA_MAIL_TS_KEY = "ops_mail:last_sakura_mail_ts"
LAST_POLL_OK_TS_KEY = "ops_mail:last_poll_ok_ts"
_NOTIFIED_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 日
_SEARCH_DAYS = 7  # 7 日前から後だけ探す（30 日で鍵が消えた後に同じメールを送り直さないため）

_SENDER_DOMAIN = "sakura.ad.jp"
_SUBJECT_KEYWORDS = ("メンテナンス", "障害", "緊急", "停止", "工事", "再起動", "復旧", "作業")
_BODY_FETCH = "(BODY.PEEK[]<0.65536>)"  # 先頭 64KB だけ。既読にしない
# コロンの後ろの空白は改行をまたがない（値が空の行で次の行を拾わないため）
_SCHEDULE_RE = re.compile(
    r"^[■●◆・\s]*(?:作業日程|作業日時|実施日時|メンテナンス日時|作業期間|日時)\s*[:：][^\S\r\n]*(.+?)\s*$",
    re.MULTILINE,
)
_SCOPE_RE = re.compile(
    r"^[■●◆・\s]*(?:影響範囲|対象サービス)\s*[:：][^\S\r\n]*(.+?)\s*$",
    re.MULTILINE,
)
_MAX_LINE_CHARS = 200
_MAX_SUBJECT_CHARS = 200
_MAX_DISCORD_CHARS = 1800
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _is_configured() -> bool:
    return bool(_IMAP_HOST and _IMAP_USER and _IMAP_PASSWORD and _DISCORD_WEBHOOK)


def _is_sakura(from_header: str) -> bool:
    """差出人のドメインが sakura.ad.jp と完全に一致するか。"""
    addr = email.utils.parseaddr(from_header)[1].lower()
    if "@" not in addr:
        return False
    return addr.rsplit("@", 1)[1] == _SENDER_DOMAIN


def _is_ops_subject(subject: str) -> bool:
    return any(k in subject for k in _SUBJECT_KEYWORDS)


def _since_date(now: float) -> str:
    """IMAP SINCE 用の日付 DD-Mon-YYYY（月は英語 3 文字の表。地域設定に依存しない）。"""
    t = time.gmtime(now - _SEARCH_DAYS * 86400)
    return f"{t.tm_mday:02d}-{_MONTHS[t.tm_mon - 1]}-{t.tm_year}"


def _body_text(raw: bytes) -> str:
    """最初の text/plain を文字にして返す。読めなければ空文字（例外は出さない）。"""
    try:
        msg = email.message_from_bytes(raw)
        for part in msg.walk():
            if part.get_content_type() != "text/plain":
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                return ""
            charset = part.get_content_charset() or "iso-2022-jp"
            try:
                return payload.decode(charset, errors="replace")
            except LookupError:
                return payload.decode("utf-8", errors="replace")
        return ""
    except Exception:
        return ""


def _extract_lines(text: str) -> tuple[str | None, str | None]:
    """作業日時の行と影響範囲の行の中身だけを取り出す。ほかの行は見ない。"""
    sm = _SCHEDULE_RE.search(text)
    cm = _SCOPE_RE.search(text)
    schedule = sm.group(1).strip()[:_MAX_LINE_CHARS] if sm else None
    scope = cm.group(1).strip()[:_MAX_LINE_CHARS] if cm else None
    return schedule or None, scope or None


def _build_content(subject: str, schedule: str | None, scope: str | None, date_str: str) -> str:
    lines = [
        "📢 さくらからの点検・障害のお知らせ",
        f"件名: {subject}",
        (
            f"作業日時: {schedule}"
            if schedule
            else "作業日時: 本文から読み取れませんでした（業務用メールで確かめてください）"
        ),
    ]
    if scope:
        lines.append(f"影響範囲: {scope}")
    lines.append(f"受信: {date_str}" if date_str else "受信: 不明")
    lines.append("本文は業務用メールで確かめてください")
    return "\n".join(lines)


def _post_discord(content: str) -> bool:
    """Discord webhook に同期 POST する。失敗しても例外を投げない。"""
    webhook = _DISCORD_WEBHOOK.strip()
    if not webhook:
        logger.info("[ops_mail] Discord webhook 未設定 (skip)")
        return False
    payload: dict = {
        "content": content[:_MAX_DISCORD_CHARS],
        "username": "Sales Anchor 運用メール",
        "allowed_mentions": {"parse": []},
    }
    try:
        resp = httpx.post(webhook, json=payload, timeout=10.0)
        if resp.status_code >= 400:
            logger.warning("[ops_mail] Discord webhook HTTP %s", resp.status_code)
            return False
        return True
    except Exception as exc:
        logger.warning("[ops_mail] Discord POST 失敗: %s", type(exc).__name__)
        return False


def _mark(redis_client, key: str) -> None:
    redis_client.set(key, "1", ex=_NOTIFIED_TTL_SECONDS)


def check_and_notify() -> int:
    """受け箱を確認し、さくらの点検・障害のメールを Discord に通知する。

    Returns:
        送った件数。例外は外に出さず、ログに 1 行書いて 0 を返す。
    """
    if not _is_configured():
        logger.info("[ops_mail] 設定未完了 (skip)")
        return 0

    redis_client = _get_redis()
    if redis_client is None:
        logger.warning("[ops_mail] Redis 使用不可 — 重複通知防止不能のためスキップ")
        return 0

    conn = None
    try:
        conn = imaplib.IMAP4_SSL(_IMAP_HOST, _IMAP_PORT, timeout=30)
        conn.login(_IMAP_USER, _IMAP_PASSWORD)
        conn.select("INBOX")
        uidvalidity_raw = conn.response("UIDVALIDITY")[1][0]
        if uidvalidity_raw is None:
            uidvalidity = "0"
        elif isinstance(uidvalidity_raw, bytes):
            uidvalidity = uidvalidity_raw.decode()
        else:
            uidvalidity = str(uidvalidity_raw)

        now = time.time()
        status, data = conn.uid("search", None, "SINCE", _since_date(now))
        if status != "OK":
            logger.warning("[ops_mail] search 失敗 status=%s", status)
            return 0

        redis_client.set(LAST_POLL_OK_TS_KEY, now)
        redis_client.set(LAST_SAKURA_MAIL_TS_KEY, now, nx=True)

        uids: list[bytes] = data[0].split() if data and data[0] else []
        notified_count = 0

        for uid_bytes in uids:
            uid = uid_bytes.decode()
            key = f"{NOTIFIED_KEY_PREFIX}{uidvalidity}:{uid}"
            try:
                if redis_client.exists(key):
                    continue

                _, msg_data = conn.uid(
                    "fetch", uid_bytes, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
                )
                if not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple):
                    logger.warning("[ops_mail] header fetch unexpected response uid=%s", uid)
                    continue
                msg = email.message_from_bytes(msg_data[0][1])

                from_raw = str(msg.get("From", ""))
                subject = _decode_mime_header(str(msg.get("Subject", "")))[:_MAX_SUBJECT_CHARS]
                date_str = str(msg.get("Date", "")) or "不明"

                if not _is_sakura(from_raw):
                    _mark(redis_client, key)
                    logger.info("[ops_mail] skipped uid=%s reason=not_sakura", uid)
                    continue

                redis_client.set(LAST_SAKURA_MAIL_TS_KEY, now)

                if not _is_ops_subject(subject):
                    _mark(redis_client, key)
                    logger.info("[ops_mail] skipped uid=%s reason=subject_filtered", uid)
                    continue

                _, body_data = conn.uid("fetch", uid_bytes, _BODY_FETCH)
                raw_body = b""
                if body_data and body_data[0] and isinstance(body_data[0], tuple):
                    raw_body = body_data[0][1] or b""
                schedule, scope = _extract_lines(_body_text(raw_body))
                content = _build_content(subject, schedule, scope, date_str)

                if _post_discord(content):
                    _mark(redis_client, key)
                    notified_count += 1
                    logger.info("[ops_mail] notified uid=%s", uid)
                else:
                    logger.info("[ops_mail] skipped uid=%s reason=post_failed", uid)
            except Exception as exc:
                logger.warning("[ops_mail] 処理失敗 uid=%s: %s", uid, type(exc).__name__)
                continue

        logger.info("[ops_mail] done notified=%d", notified_count)
        return notified_count

    except Exception as exc:
        logger.warning("[ops_mail] IMAP 処理中エラー: %s", type(exc).__name__)
        return 0
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:
                pass


__all__ = ["check_and_notify"]
