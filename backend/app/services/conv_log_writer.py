"""SA-02 Stage 1: conversation_logs への書き込みヘルパ。

設計判断:
- 呼び出し前に set_tenant_context 済みのセッションを受け取る（search_path が確定している前提）。
  db.commit() 後は reset_tenant_context を呼んでから本関数を呼ぶこと。
- external_message_id の UNIQUE 制約で冪等を保証（ON CONFLICT DO NOTHING → None 返却）。
- company_id は deals テーブルから lead の最新案件を参照して補完する（案件なければ NULL）。
  v_company_stats VIEW が company_id で集計するため、案件紐づけ後は自動で集計される。
- contact_id は contacts テーブルから lead の primary contact を参照して補完する（なければ NULL）。
  呼び出し元が contact_id を明示した場合はそちらを優先する（渡せば確定）。
- conversation_logs の analysis / translated_text は Stage 3（翻訳発火配線）で埋まる。
  Stage 1 ではデータフロー（受信→保存）の確立のみ行う。

呼び出し元:
- backend/app/routers/webhook.py（Meta Messenger / Instagram）
- backend/app/discord_gateway/dm_writer.py（Discord DM）
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def write_conversation_log(
    db: AsyncSession,
    *,
    tenant_id: int,
    lead_id: int | None,
    contact_id: int | None = None,
    channel_type: str,
    channel_identity: str | None = None,
    direction: str,
    sender: str | None = None,
    content_text: str | None = None,
    external_message_id: str | None = None,
    raw_payload: dict[str, Any] | None = None,
    occurred_at: datetime,
) -> int | None:
    """conversation_logs に 1 件挿入する。

    Args:
        db: テナントコンテキスト設定済みの AsyncSession。
        tenant_id: テナント ID（RLS カラム用）。
        lead_id: リード ID。案件未紐づけの場合も受け付ける（company_id は deals から補完）。
        contact_id: コンタクト ID。省略時は contacts から lead の primary contact を自動補完。
        channel_type: チャネル種別（'messenger' / 'instagram' / 'discord' / 'phone' 等）。
        channel_identity: 送受信相手のチャネル固有 ID（PSID / Discord UID 等）。
        direction: 'inbound'（受信）または 'outbound'（エコー含む送信）。
        sender: 送信者識別子（PSID / 'staff' 等）。
        content_text: メッセージ本文。
        external_message_id: チャネル固有のメッセージ ID（重複排除キー）。
        raw_payload: 生の webhook ペイロード（JSONB）。
        occurred_at: メッセージの発生日時（タイムゾーン付き）。

    Returns:
        挿入された id。external_message_id 重複でスキップした場合は None。
    """
    company_id = await _get_company_id_for_lead(db, lead_id) if lead_id else None
    if contact_id is None and lead_id:
        contact_id = await _get_contact_id_for_lead(db, lead_id)
    raw_json = json.dumps(raw_payload) if raw_payload else None

    result = await db.execute(
        text("""
            INSERT INTO conversation_logs (
                tenant_id, lead_id, contact_id, company_id,
                channel_type, channel_identity, direction, sender,
                content_text, external_message_id, raw_payload, occurred_at
            ) VALUES (
                :tenant_id, :lead_id, :contact_id, :company_id,
                :channel_type, :channel_identity, :direction, :sender,
                :content_text, :external_message_id, :raw_payload::jsonb, :occurred_at
            )
            ON CONFLICT (external_message_id) WHERE external_message_id IS NOT NULL
            DO NOTHING
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "contact_id": contact_id,
            "company_id": company_id,
            "channel_type": channel_type,
            "channel_identity": channel_identity,
            "direction": direction,
            "sender": sender,
            "content_text": content_text,
            "external_message_id": external_message_id,
            "raw_payload": raw_json,
            "occurred_at": occurred_at,
        },
    )
    new_id = result.scalar_one_or_none()
    if new_id is None:
        logger.debug(
            "[conv_log_writer] duplicate skipped: channel=%s ext_id=%s",
            channel_type, external_message_id,
        )
    else:
        logger.info(
            "[conv_log_writer] wrote id=%d channel=%s direction=%s",
            new_id, channel_type, direction,
        )
    return new_id


async def _get_company_id_for_lead(db: AsyncSession, lead_id: int) -> int | None:
    """lead_id に紐づく最新案件の company_id を返す。案件がなければ None。"""
    result = await db.execute(
        text("""
            SELECT company_id
            FROM deals
            WHERE lead_id = :lead_id
              AND company_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"lead_id": lead_id},
    )
    row = result.first()
    return int(row[0]) if row else None


async def _get_contact_id_for_lead(db: AsyncSession, lead_id: int) -> int | None:
    """lead_id に紐づく primary contact の id を返す。なければ None。

    is_primary_contact=true を優先し、同 lead に複数 contact があるときは
    最初に登録された（id が小さい）ものを採用する。
    """
    result = await db.execute(
        text("""
            SELECT id
            FROM contacts
            WHERE lead_id = :lead_id
            ORDER BY is_primary_contact DESC, id ASC
            LIMIT 1
        """),
        {"lead_id": lead_id},
    )
    row = result.first()
    return int(row[0]) if row else None
