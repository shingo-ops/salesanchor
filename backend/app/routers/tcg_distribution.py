"""
DIST-01: TCG 在庫配信 API ルーター。

設計書: ~/Documents/dist01_backup/DISTRIBUTION_DESIGN.md §G
担当: Session 3 (CC_TASK_DIST-02)

エンドポイント:
  配信先 CRUD:
    GET    /tcg/distribution/targets
    POST   /tcg/distribution/targets
    GET    /tcg/distribution/targets/{target_id}
    PUT    /tcg/distribution/targets/{target_id}
    DELETE /tcg/distribution/targets/{target_id}
  プレビュー・実行:
    GET    /tcg/distribution/preview
    POST   /tcg/distribution/run
    POST   /tcg/distribution/run/{target_id}
  設定:
    GET    /tcg/distribution/settings
    PUT    /tcg/distribution/settings/{key}

認証: require_super_admin（全エンドポイント共通）
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services import tcg_distribution_svc as svc

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class DistributionTargetCreate(BaseModel):
    name: str
    spreadsheet_id: str
    sheet_name: str
    is_active: bool = True
    sa_key_secret_name: str = "TCG_SHEETS_SA_KEY_FILE"


class DistributionTargetUpdate(BaseModel):
    name: str | None = None
    spreadsheet_id: str | None = None
    sheet_name: str | None = None
    is_active: bool | None = None
    sa_key_secret_name: str | None = None


class SettingUpdate(BaseModel):
    value: str


# ---------------------------------------------------------------------------
# アクセス確認（登録前・読み取りのみ）
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/distribution/verify-access",
    dependencies=[Depends(require_super_admin)],
)
async def verify_spreadsheet_access(spreadsheet_id: str):
    """
    指定のスプレッドシートIDへのアクセスを読み取りで確認する（書き込みなし）。
    登録フォームの保存前チェックに使用する。
    """
    return await svc.verify_spreadsheet_access(spreadsheet_id)


# ---------------------------------------------------------------------------
# 配信先 CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/distribution/targets",
    dependencies=[Depends(require_super_admin)],
)
async def list_distribution_targets(db: AsyncSession = Depends(get_db)):
    return await svc.list_targets(db)


@router.post(
    "/tcg/distribution/targets",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_super_admin)],
)
async def create_distribution_target(
    data: DistributionTargetCreate,
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_target(db, data.model_dump())


@router.get(
    "/tcg/distribution/targets/{target_id}",
    dependencies=[Depends(require_super_admin)],
)
async def get_distribution_target(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    row = await svc.get_target(db, str(target_id))
    if row is None:
        raise HTTPException(status_code=404, detail="配信先が見つかりません")
    return row


@router.put(
    "/tcg/distribution/targets/{target_id}",
    dependencies=[Depends(require_super_admin)],
)
async def update_distribution_target(
    target_id: UUID,
    data: DistributionTargetUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = await svc.update_target(db, str(target_id), data.model_dump(exclude_none=True))
    if row is None:
        raise HTTPException(status_code=404, detail="配信先が見つかりません")
    return row


@router.delete(
    "/tcg/distribution/targets/{target_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_super_admin)],
)
async def delete_distribution_target(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    ok = await svc.soft_delete_target(db, str(target_id))
    if not ok:
        raise HTTPException(status_code=404, detail="配信先が見つかりません")


# ---------------------------------------------------------------------------
# プレビュー・実行
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/distribution/preview",
    dependencies=[Depends(require_super_admin)],
)
async def distribution_preview(db: AsyncSession = Depends(get_db)):
    """配信候補件数・除外内訳・精度ゲート状態を返す（書き込みなし）。"""
    return await svc.fetch_preview_data(db)


@router.post(
    "/tcg/distribution/run",
    dependencies=[Depends(require_super_admin)],
)
async def run_distribution_all(db: AsyncSession = Depends(get_db)):
    """全アクティブ配信先へ配信を実行する。"""
    return await svc.run_distribution(db)


@router.post(
    "/tcg/distribution/run/{target_id}",
    dependencies=[Depends(require_super_admin)],
)
async def run_distribution_target(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """特定の配信先へ配信を実行する。"""
    return await svc.run_distribution(db, target_id=str(target_id))


# ---------------------------------------------------------------------------
# 設定管理
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/distribution/settings",
    dependencies=[Depends(require_super_admin)],
)
async def list_distribution_settings(db: AsyncSession = Depends(get_db)):
    return await svc.list_settings(db)


@router.put(
    "/tcg/distribution/settings/{key}",
    dependencies=[Depends(require_super_admin)],
)
async def update_distribution_setting(
    key: str,
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = await svc.update_setting(db, key, data.value)
    if row is None:
        raise HTTPException(status_code=404, detail=f"設定キー {key!r} が見つかりません")
    return row
