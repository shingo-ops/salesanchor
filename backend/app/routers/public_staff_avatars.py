"""
担当者アイコン画像の公開配信（認証不要・ADR-159 便A）。

Discord が avatar_url として取得するためログイン不要。URL は推測不能な token のみ。
DB は参照しない（テナント情報を露出しない）。token 形式を厳格に検証し、
パストラバーサルを不可能にする。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.services.staff_avatar import avatar_path

public_router = APIRouter()

_CACHE_CONTROL = "public, max-age=86400"


@public_router.get("/public/staff-avatars/{token}.webp")
async def get_staff_avatar(token: str):
    path = avatar_path(token)
    if path is None or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return FileResponse(
        path=str(path),
        media_type="image/webp",
        headers={"Cache-Control": _CACHE_CONTROL},
    )
