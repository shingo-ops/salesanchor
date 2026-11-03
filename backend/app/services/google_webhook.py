from __future__ import annotations

"""
Google Calendar Webhook（Push Notification）管理サービス。

担当範囲:
  - Webhook チャンネル登録（google.calendar.events.watch()）
  - Webhook チャンネルの有効期限管理と再登録
  - Webhook 受信時のイベント差分取得と DB 反映

Google Calendar Push Notification の制約:
  - 最大有効期限: ~7日（最大 604800000ms ≈ 7 * 24 * 60 * 60 * 1000）
  - 通知は 100% 保証されない（ドロップあり）→ Polling フォールバックと併用推奨
  - channel_id は UUID（毎回新規生成）
  - チャンネル登録後、最初に 'sync' 状態の通知が届く（無視する）
  - HTTPS 公開エンドポイントが必要（本番: https://api.salesanchor.jp）

環境変数:
  API_BASE_URL - Webhook 受信エンドポイントのベース URL
                 デフォルト: https://api.salesanchor.jp
"""

import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    clear_tenant_context,
    reset_tenant_context,
    set_tenant_context,
)

logger = logging.getLogger(__name__)

_WEBHOOK_PATH = "/api/v1/google-calendar/webhook"
# Google Calendar Webhook の最大有効期限（7日 = 604800000ms）
_MAX_TTL_MS = 604800000
# 更新トリガー: 残り 2 日以下になったら再登録
_RENEW_THRESHOLD_HOURS = 48
# 全部読みの対象期間（今 − 30 日以降）
_FULL_SYNC_DAYS = 30


def _get_webhook_address() -> str:
    base = os.getenv("API_BASE_URL", "https://api.salesanchor.jp").rstrip("/")
    return f"{base}{_WEBHOOK_PATH}"


# ---------------------------------------------------------------------------
# Webhook チャンネル登録
# ---------------------------------------------------------------------------


async def register_webhook(db: AsyncSession, tenant_id: int) -> Optional[dict]:
    """Google Calendar の Push Notification チャンネルを登録する。

    登録成功時は google_webhook_subscriptions に channel 情報を保存する。
    既存のチャンネルがある場合は 新規登録 → 古いものを stop の順で更新する。
    合言葉（token）を作り、sha256 だけ channel_token_hash に保存する。

    Returns:
        成功時: {"channel_id": str, "expiration": str}
        Google 未接続時: None
    """
    from app.services import google_calendar as cal_svc

    try:
        service = await cal_svc._get_service(db, tenant_id)
    except RuntimeError as e:
        logger.info("Google Calendar 未接続のため Webhook 登録スキップ (tenant=%s): %s", tenant_id, e)
        return None

    old_row = (
        await db.execute(
            text(
                "SELECT channel_id, resource_id FROM google_webhook_subscriptions"
                " WHERE tenant_id = :tid"
            ),
            {"tid": tenant_id},
        )
    ).first()

    channel_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    webhook_address = _get_webhook_address()

    try:
        response = await asyncio.to_thread(
            service.events().watch(
                calendarId="primary",
                body={
                    "id": channel_id,
                    "type": "web_hook",
                    "address": webhook_address,
                    "token": token,
                    "expiration": str(int(datetime.now(timezone.utc).timestamp() * 1000) + _MAX_TTL_MS),
                },
            ).execute
        )
    except Exception as e:
        logger.error("Webhook チャンネル登録に失敗 (tenant=%s): %s", tenant_id, e)
        return None

    expiration_ms = int(response.get("expiration", 0))
    expiration_dt = datetime.fromtimestamp(expiration_ms / 1000, tz=timezone.utc)
    resource_id = response.get("resourceId", "")

    await db.execute(
        text(
            "INSERT INTO google_webhook_subscriptions"
            " (tenant_id, channel_id, resource_id, calendar_id, expiration,"
            "  channel_token_hash)"
            " VALUES (:tid, :cid, :rid, 'primary', :exp, :thash)"
            " ON CONFLICT (tenant_id) DO UPDATE SET"
            "   channel_id  = EXCLUDED.channel_id,"
            "   resource_id = EXCLUDED.resource_id,"
            "   expiration  = EXCLUDED.expiration,"
            "   channel_token_hash = EXCLUDED.channel_token_hash,"
            "   created_at  = NOW()"
        ),
        {
            "tid": tenant_id,
            "cid": channel_id,
            "rid": resource_id,
            "exp": expiration_dt,
            "thash": hashlib.sha256(token.encode()).hexdigest(),
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    # 古いチャンネルを止める（失敗しても 7 日で切れるので warning だけ）
    if old_row and old_row[0] != channel_id:
        try:
            await asyncio.to_thread(
                service.channels().stop(
                    body={"id": old_row[0], "resourceId": old_row[1]}
                ).execute
            )
        except Exception as e:
            logger.warning("古い Webhook チャンネル停止に失敗 (tenant=%s): %s", tenant_id, e)

    logger.info(
        "Webhook チャンネル登録完了 (tenant=%s, channel=%s, expiry=%s)",
        tenant_id, channel_id, expiration_dt,
    )
    return {"channel_id": channel_id, "expiration": expiration_dt.isoformat()}


# ---------------------------------------------------------------------------
# Webhook チャンネル停止
# ---------------------------------------------------------------------------


async def stop_webhook(db: AsyncSession, tenant_id: int) -> None:
    """Google Calendar の Push Notification チャンネルを停止する。"""
    from app.services import google_calendar as cal_svc

    row = await db.execute(
        text(
            "SELECT channel_id, resource_id FROM google_webhook_subscriptions"
            " WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    record = row.first()
    if not record:
        return

    channel_id, resource_id = record[0], record[1]
    try:
        service = await cal_svc._get_service(db, tenant_id)
        await asyncio.to_thread(
            service.channels().stop(
                body={"id": channel_id, "resourceId": resource_id}
            ).execute
        )
    except Exception as e:
        logger.warning("Webhook チャンネル停止に失敗 (tenant=%s): %s", tenant_id, e)

    await db.execute(
        text("DELETE FROM google_webhook_subscriptions WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)


# ---------------------------------------------------------------------------
# テナント特定（Webhook 受信時）
# ---------------------------------------------------------------------------


async def verify_channel(
    db: AsyncSession, channel_id: str, token: str
) -> Optional[int]:
    """channel_id と合言葉（X-Goog-Channel-Token）を照合し、合えば tenant_id を返す。

    行が無い・channel_token_hash が NULL・合言葉の sha256 が一致しないときは None。
    """
    row = await db.execute(
        text(
            "SELECT tenant_id, channel_token_hash FROM google_webhook_subscriptions"
            " WHERE channel_id = :cid"
        ),
        {"cid": channel_id},
    )
    record = row.first()
    if not record:
        return None
    tenant_id, token_hash = record[0], record[1]
    if not token_hash:
        return None
    given = hashlib.sha256((token or "").encode()).hexdigest()
    if not hmac.compare_digest(given, token_hash):
        return None
    return tenant_id


# ---------------------------------------------------------------------------
# Webhook 受信処理
# ---------------------------------------------------------------------------


async def sync_tenant_from_google(db: AsyncSession, tenant_id: int) -> dict:
    """Google の予定をこの会社のアプリへ取り込む（ADR-1059 便2）。

    sync_token があれば差分だけ、無い・410 のときは過去 30 日以降を全部読み直す。
    全部読みでは、現れなかった source='google' の行（30 日以内）を消す。
    同じ会社の同期は advisory lock で 1 本に絞る。
    """
    from googleapiclient.errors import HttpError

    from app.services import google_calendar as cal_svc
    from app.services.calendar_service import upsert_from_google

    got = (
        await db.execute(
            text("SELECT pg_try_advisory_lock(1059, :tid)"), {"tid": tenant_id}
        )
    ).scalar()
    if not got:
        return {"skipped": "locked"}

    try:
        await set_tenant_context(db, tenant_id)

        cfg = (
            await db.execute(
                text(
                    "SELECT connected_by_user_id, sync_mode"
                    " FROM tenant_google_calendar_config"
                )
            )
        ).first()
        if not cfg or cfg[1] not in ("bidirectional", "read_only"):
            return {"skipped": "off"}
        owner_user_id = cfg[0]
        if owner_user_id is None:
            logger.warning("接続の持ち主が空のため取り込みスキップ (tenant=%s)", tenant_id)
            return {"skipped": "no_owner"}

        try:
            service = await cal_svc._get_service(db, tenant_id)
        except RuntimeError as e:
            logger.info("Google Calendar 未接続のため取り込みスキップ (tenant=%s): %s", tenant_id, e)
            return {"skipped": "not_connected"}
        # _get_service は中で commit することがあるので文脈を張り直す
        await set_tenant_context(db, tenant_id)

        sub = (
            await db.execute(
                text(
                    "SELECT sync_token FROM google_webhook_subscriptions"
                    " WHERE tenant_id = :tid"
                ),
                {"tid": tenant_id},
            )
        ).first()
        sync_token = sub[0] if sub else None

        time_min_dt = datetime.now(timezone.utc) - timedelta(days=_FULL_SYNC_DAYS)
        time_min = time_min_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        async def _fetch(token: Optional[str]) -> tuple[list, Optional[str]]:
            items: list = []
            page_token: Optional[str] = None
            while True:
                kwargs: dict = {
                    "calendarId": "primary",
                    "singleEvents": True,
                    "maxResults": 250,
                }
                if token:
                    kwargs["syncToken"] = token
                else:
                    kwargs["timeMin"] = time_min
                if page_token:
                    kwargs["pageToken"] = page_token
                result = await asyncio.to_thread(
                    service.events().list(**kwargs).execute
                )
                items.extend(result.get("items", []))
                page_token = result.get("nextPageToken")
                if not page_token:
                    return items, result.get("nextSyncToken")

        full = not sync_token
        try:
            items, next_sync_token = await _fetch(sync_token)
        except HttpError as e:
            if sync_token and getattr(e.resp, "status", None) == 410:
                logger.info("syncToken 期限切れ(410)のため全部読み直し (tenant=%s)", tenant_id)
                full = True
                items, next_sync_token = await _fetch(None)
            else:
                raise

        upserted = 0
        deleted = 0
        seen: list[str] = []
        for item in items:
            outcome = await upsert_from_google(db, tenant_id, item, owner_user_id)
            if outcome == "upserted":
                upserted += 1
            elif outcome == "deleted":
                deleted += 1
            if full and item.get("status") != "cancelled" and item.get("id"):
                seen.append(item["id"])

        if full:
            res = await db.execute(
                text(
                    "DELETE FROM calendar_events"
                    " WHERE source = 'google' AND google_event_id IS NOT NULL"
                    " AND end_datetime >= :time_min"
                    " AND NOT (google_event_id::text = ANY(CAST(:seen AS text[])))"
                ),
                {"time_min": time_min_dt, "seen": seen},
            )
            deleted += max(res.rowcount or 0, 0)

        if next_sync_token:
            await db.execute(
                text(
                    "UPDATE google_webhook_subscriptions SET sync_token = :t"
                    " WHERE tenant_id = :tid"
                ),
                {"t": next_sync_token, "tid": tenant_id},
            )

        await db.commit()
        await reset_tenant_context(db, tenant_id)
        logger.info(
            "Google 取り込み完了 (tenant=%s, upserted=%d, deleted=%d, full=%s)",
            tenant_id, upserted, deleted, full,
        )
        return {"upserted": upserted, "deleted": deleted, "full": full}
    finally:
        try:
            await db.rollback()
            await db.execute(
                text("SELECT pg_advisory_unlock(1059, :tid)"), {"tid": tenant_id}
            )
        except Exception as e:  # pragma: no cover - 後始末の失敗は記録だけ
            logger.warning("advisory unlock 失敗 (tenant=%s): %s", tenant_id, e)


# ---------------------------------------------------------------------------
# 有効期限切れチャンネルの自動更新（定期実行用）
# ---------------------------------------------------------------------------


async def renew_expiring_webhooks(db: AsyncSession) -> int:
    """有効期限が 2 日以内のチャンネルを自動更新する。

    接続の表 tenant_google_calendar_config は RLS 強制のため、会社ごとに
    set_tenant_context してから register_webhook を呼ぶ。

    Returns:
        更新したチャンネル数
    """
    threshold = datetime.now(timezone.utc) + timedelta(hours=_RENEW_THRESHOLD_HOURS)
    row = await db.execute(
        text(
            "SELECT tenant_id FROM google_webhook_subscriptions WHERE expiration < :threshold"
        ),
        {"threshold": threshold},
    )
    tenant_ids = [r[0] for r in row.fetchall()]

    renewed = 0
    try:
        for tenant_id in tenant_ids:
            await set_tenant_context(db, tenant_id)
            result = await register_webhook(db, tenant_id)
            if result:
                renewed += 1
            else:
                logger.warning("Webhook 更新失敗 (tenant=%s)", tenant_id)
    finally:
        await clear_tenant_context(db)

    return renewed
