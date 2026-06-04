"""
GET /api/v1/contacts/{contact_id}/channel-links

担当者のチャンネル情報に public.link_templates SSOT を組み合わせ、
クリック可能な URL を生成して返す。

返却形式:
  [
    {
      "channel": "whatsapp",
      "url": "https://wa.me/81901234567",
      "is_verified": true,
      "label": "whatsapp"
    },
    ...
  ]

is_verified=False のチャンネルは UI 側で「未検証」バッジを表示する。
テンプレートに必要な ID が揃っていない場合は url=null で返す。
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_tenant, require_permission
from app.database import get_db

router = APIRouter()


class ChannelLinkResponse(BaseModel):
    channel: str
    url: str | None
    is_verified: bool
    label: str
    notes: str | None = None


def _build_url(url_pattern: str, channel: str, channel_row: dict) -> str | None:
    """url_pattern の {placeholder} を channel_row のフィールドで埋める。

    contact_contact_channels の既存カラム:
      - channel (channel 名そのもの)
      - purpose
      - is_primary
      - guild_id  (SA-05 C-3 で追加)

    フロントエンド側で追加保存されるデータのマッピング:
      whatsapp   → purpose フィールドに電話番号を格納（既存運用）
      telegram   → purpose フィールドにユーザー名を格納（既存運用）
      discord    → guild_id + purpose (channel_id) を使用
      messenger  → purpose に psid, guild_id に page_id 相当
      instagram  → purpose に igsid

    Notes: contact_contact_channels.purpose は汎用フィールドのため、
    各チャンネルが格納する意味が異なる。URL 生成は best-effort とし、
    値が取得できない場合は None を返す。
    """
    purpose = channel_row.get("purpose") or ""
    guild_id = channel_row.get("guild_id") or ""

    replacements: dict[str, str] = {}

    if channel == "whatsapp":
        # purpose に電話番号を格納
        phone = re.sub(r"[^\d+]", "", purpose)
        if phone:
            replacements["phone"] = phone

    elif channel == "telegram":
        # purpose にユーザー名 or 電話番号を格納
        username = purpose.strip().lstrip("@") if purpose else ""
        if username:
            replacements["username"] = username
            replacements["phone"] = username  # どちらのプレースホルダにも対応

    elif channel == "discord":
        # guild_id カラム + purpose に channel_id
        if guild_id:
            replacements["guild_id"] = guild_id
        if purpose:
            replacements["channel_id"] = purpose

    elif channel == "messenger":
        # purpose に psid を格納（page_id/bm_id は テナント設定から取得するが
        # 現状 contact レベルでは psid のみ。URL は fixed base URL のため
        # required_ids を全て満たせなくてもベース URL を返す）
        replacements["psid"] = purpose
        replacements["page_id"] = ""
        replacements["bm_id"] = ""

    elif channel == "instagram":
        # purpose に igsid を格納
        replacements["igsid"] = purpose
        replacements["page_id"] = ""

    else:
        # 未知チャンネル: purpose をそのまま利用
        return purpose if purpose else None

    # プレースホルダを置換
    result = url_pattern
    for key, val in replacements.items():
        result = result.replace(f"{{{key}}}", val)

    # 未解決のプレースホルダが残っていれば None
    if re.search(r"\{[^}]+\}", result):
        return None

    return result


@router.get(
    "/contacts/{contact_id}/channel-links",
    response_model=list[ChannelLinkResponse],
    dependencies=[Depends(require_permission("customers.view"))],
    summary="担当者チャンネルのクリック可能リンク一覧",
    tags=["contacts"],
)
async def get_channel_links(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> list[ChannelLinkResponse]:
    """担当者の contact_contact_channels × public.link_templates でリンクを生成する。"""

    # 担当者の存在確認
    contact_check = await db.execute(
        text("SELECT id FROM contacts WHERE id = :cid"),
        {"cid": contact_id},
    )
    if not contact_check.mappings().first():
        raise HTTPException(status_code=404, detail="担当者が見つかりません")

    # チャンネル一覧取得（guild_id 列を含む）
    channels_res = await db.execute(
        text("""
            SELECT channel, purpose, is_primary, guild_id
            FROM contact_contact_channels
            WHERE contact_id = :cid
            ORDER BY is_primary DESC, id
        """),
        {"cid": contact_id},
    )
    channel_rows = [dict(row) for row in channels_res.mappings().all()]

    if not channel_rows:
        return []

    # テンプレート一括取得（public schema は search_path で必ず参照可能）
    channel_names = [r["channel"] for r in channel_rows]
    templates_res = await db.execute(
        text("""
            SELECT channel, url_pattern, is_verified, notes
            FROM public.link_templates
            WHERE channel = ANY(:channels)
        """),
        {"channels": channel_names},
    )
    templates = {row["channel"]: dict(row) for row in templates_res.mappings().all()}

    result: list[ChannelLinkResponse] = []
    for ch_row in channel_rows:
        ch_name = ch_row["channel"]
        tmpl = templates.get(ch_name)

        if tmpl:
            url = _build_url(tmpl["url_pattern"], ch_name, ch_row)
            result.append(
                ChannelLinkResponse(
                    channel=ch_name,
                    url=url,
                    is_verified=tmpl["is_verified"],
                    label=ch_name,
                    notes=tmpl.get("notes"),
                )
            )
        else:
            # テンプレート未登録チャンネル（Line 等）は purpose をそのまま返す
            result.append(
                ChannelLinkResponse(
                    channel=ch_name,
                    url=None,
                    is_verified=False,
                    label=ch_name,
                    notes=None,
                )
            )

    return result
