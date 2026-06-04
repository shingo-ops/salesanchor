"""
ADR-107 (ADR-SA-14): 分析エージェント(A) 顧客優先度付け — APIルーター。

守るべき原則:
  - 社内ロールのみアクセス（tenant_admin / tenant_staff）: require_permission で強制
  - スコアは助言。低スコアで客を自動切りする処理なし
  - write 後は必ず reset_tenant_context()（ADR-072）
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.schemas.customer_priority import (
    CustomerScoreResponse,
    LabelOverrideRequest,
    MessageLabelResponse,
    ScoreOverrideRequest,
)
from app.services import priority_scoring
from app.services.discord_notifier import notify_priority_score_sudden_change

router = APIRouter()


@router.get(
    "/leads/{lead_id}/priority-score",
    response_model=CustomerScoreResponse,
    dependencies=[Depends(require_permission("analytics.customer_priority.view"))],
    summary="顧客優先度スコア取得（ADR-107 §C）",
)
async def get_priority_score(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> CustomerScoreResponse:
    """
    顧客スコアを返す。キャッシュがない場合は計算して保存する。
    スコアは「値 + 確信度 + 根拠シグナル」の3点セット。裸の断定なし。
    """
    _assert_lead_belongs_to_tenant(lead_id)
    return await priority_scoring.get_or_compute_score(db, tenant_id, lead_id)


@router.post(
    "/leads/{lead_id}/priority-score/override",
    response_model=CustomerScoreResponse,
    dependencies=[Depends(require_permission("analytics.customer_priority.override"))],
    summary="顧客優先度スコア人手上書き（ADR-107 §C）",
)
async def override_priority_score(
    lead_id: int,
    body: ScoreOverrideRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> CustomerScoreResponse:
    """
    人手によるスコア上書き。v1 = 保存のみ（較正への反映は次段）。
    ADR-072: db.commit() 直後に reset_tenant_context() 必須。
    """
    existing = await db.execute(
        text(
            "SELECT score, tier FROM customer_scores WHERE lead_id = :lid"
        ),
        {"lid": lead_id},
    )
    row = existing.fetchone()
    if row is None:
        # スコア未計算の場合は先に計算
        await priority_scoring.get_or_compute_score(db, tenant_id, lead_id)
        existing = await db.execute(
            text("SELECT score, tier FROM customer_scores WHERE lead_id = :lid"),
            {"lid": lead_id},
        )
        row = existing.fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="リードが見つかりません")

    old_tier = row.tier

    await db.execute(
        text(
            """
            UPDATE customer_scores
               SET override_score = :oscore,
                   override_note  = :onote,
                   override_by    = :uid,
                   override_at    = :now
             WHERE lead_id = :lid
            """
        ),
        {
            "oscore": body.override_score,
            "onote": body.override_note,
            "uid": current_user.id,
            "now": datetime.utcnow(),
            "lid": lead_id,
        },
    )
    await db.commit()
    # ADR-072: commit 直後にテナントコンテキスト再設定
    await reset_tenant_context(db, tenant_id)

    result = await priority_scoring.get_or_compute_score(db, tenant_id, lead_id)

    # スコアがティアを跨いで急変した場合は Discord 通知
    new_tier = result.tier.value
    if old_tier != new_tier:
        await notify_priority_score_sudden_change(
            tenant_id, lead_id,
            old_tier=old_tier,
            new_tier=new_tier,
        )

    return result


@router.get(
    "/leads/{lead_id}/message-labels",
    response_model=list[MessageLabelResponse],
    dependencies=[Depends(require_permission("analytics.customer_priority.view"))],
    summary="メッセージラベル一覧取得",
)
async def get_message_labels(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> list[MessageLabelResponse]:
    """
    per-message ラベル一覧を返す。ラベルが未計算の場合は計算して保存する。
    inbound=顧客/outbound=営業の両方向を含む。
    """
    count_result = await db.execute(
        text("SELECT COUNT(*) FROM message_labels WHERE lead_id = :lid"),
        {"lid": lead_id},
    )
    if count_result.scalar() == 0:
        await priority_scoring.label_lead_messages(db, lead_id, tenant_id)

    rows = await db.execute(
        text(
            """
            SELECT id, message_id, lead_id, label, confidence,
                   direction, source, override_by, created_at
            FROM message_labels
            WHERE lead_id = :lid
            ORDER BY created_at
            """
        ),
        {"lid": lead_id},
    )
    return [
        MessageLabelResponse(
            id=r.id,
            message_id=r.message_id,
            lead_id=r.lead_id,
            label=r.label,
            confidence=float(r.confidence),
            direction=r.direction,
            source=r.source,
            override_by=r.override_by,
            created_at=r.created_at,
        )
        for r in rows.fetchall()
    ]


@router.patch(
    "/leads/{lead_id}/message-labels/{label_id}/override",
    response_model=MessageLabelResponse,
    dependencies=[Depends(require_permission("analytics.customer_priority.override"))],
    summary="メッセージラベル人手訂正",
)
async def override_message_label(
    lead_id: int,
    label_id: int,
    body: LabelOverrideRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> MessageLabelResponse:
    """
    人手によるラベル訂正。v1 = 保存のみ（較正への反映は次段）。
    ADR-072: db.commit() 直後に reset_tenant_context() 必須。
    """
    result = await db.execute(
        text(
            """
            UPDATE message_labels
               SET label       = :label,
                   source      = 'human',
                   confidence  = 1.0,
                   override_by = :uid,
                   override_at = :now
             WHERE id = :lid AND lead_id = :flid
            RETURNING id, message_id, lead_id, label, confidence,
                      direction, source, override_by, created_at
            """
        ),
        {
            "label": body.label.value,
            "uid": current_user.id,
            "now": datetime.utcnow(),
            "lid": label_id,
            "flid": lead_id,
        },
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="ラベルが見つかりません")

    await db.commit()
    # ADR-072: commit 直後にテナントコンテキスト再設定
    await reset_tenant_context(db, tenant_id)

    return MessageLabelResponse(
        id=row.id,
        message_id=row.message_id,
        lead_id=row.lead_id,
        label=row.label,
        confidence=float(row.confidence),
        direction=row.direction,
        source=row.source,
        override_by=row.override_by,
        created_at=row.created_at,
    )


@router.post(
    "/leads/{lead_id}/priority-score/recalculate",
    response_model=CustomerScoreResponse,
    dependencies=[Depends(require_permission("analytics.customer_priority.override"))],
    summary="顧客優先度スコア強制再計算",
)
async def recalculate_priority_score(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> CustomerScoreResponse:
    """キャッシュを無効化してスコアを強制再計算する。"""
    return await priority_scoring.recompute_score(db, tenant_id, lead_id)


def _assert_lead_belongs_to_tenant(lead_id: int) -> None:
    """
    lead_id の整数型検証のみ。テナント帰属はRLS + search_pathが保証する。
    URLパラメータからtenant_idを受け取ることは絶対にしない（IDOR防止）。
    """
    if not isinstance(lead_id, int) or lead_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid lead_id")
