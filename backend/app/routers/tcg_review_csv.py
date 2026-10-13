"""要確認を CSV で直してアプリに戻す API（出力 → 内容確認 → 反映）。

エンドポイント:
  GET  /api/v1/tcg/review/csv/export    要確認の一覧を CSV で出す
  POST /api/v1/tcg/review/csv/preview   検査だけ。書き込まない
  POST /api/v1/tcg/review/csv/commit    検査をやり直し、confirmed_digest が一致したときだけ反映する

認証: require_super_admin。前例: tcg_product_import.py（同じ形・同じ上限）。
設計: docs/handoff/review-csv-roundtrip/design.md §4
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.services import tcg_review_csv_svc as review_csv
from app.services.tcg_product_roundtrip_svc import RoundtripError

router = APIRouter()

ERR_NOT_CSV = "REVIEW_CSV_NOT_CSV"
ERR_EMPTY = "REVIEW_CSV_EMPTY_FILE"


async def _read_csv(file: UploadFile) -> bytes:
    """アップロードされた CSV を読む。拡張子と空をここで弾く（大きさと UTF-8 はサービスが検査する）。"""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail=ERR_NOT_CSV)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail=ERR_EMPTY)
    return raw


@router.get("/tcg/review/csv/export", summary="要確認の一覧を CSV で出す")
async def export_review_csv(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> Response:
    raw = await review_csv.export_csv(db)
    return Response(raw, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": 'attachment; filename="tcg-needs-review.csv"',
        "Cache-Control": "no-store",
    })


@router.post("/tcg/review/csv/preview", summary="要確認 CSV の内容確認（書き込まない）")
async def preview_review_csv(
    file: UploadFile = File(..., description="要確認の CSV ファイル"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> dict:
    raw = await _read_csv(file)
    try:
        return await review_csv.preview(db, raw)
    except RoundtripError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@router.post("/tcg/review/csv/commit", summary="要確認 CSV の反映")
async def commit_review_csv(
    file: UploadFile = File(..., description="要確認の CSV ファイル"),
    confirmed_digest: str = Form(..., description="内容確認で受け取った指紋"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_super_admin),
) -> dict:
    raw = await _read_csv(file)
    try:
        return await review_csv.commit(db, raw, confirmed_digest, str(user.email or user.id or ""))
    except RoundtripError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
