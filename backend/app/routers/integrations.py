"""API連携（外部サービス連携）ルーター。

現状は Googleドライブ連携の動作確認用エンドポイントのみ:
  GET  /integrations/google-drive/status       設定状況 + 招待先 SA メール
  POST /integrations/google-drive/test-upload  テスト PDF を共有ドライブに保存

いずれも erp.view 権限が必要（管理センター > データ管理 と同じ権限）。

変更履歴:
  2026-06-06: 初版（API連携 Googleドライブ 保存テスト）
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.auth.dependencies import require_permission
from app.services import google_drive
from app.services.test_pdf import render_test_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])

_TEST_PDF_FILENAME = "salesanchor-test.pdf"


class GoogleDriveStatus(BaseModel):
    configured: bool
    service_account_email: str | None = None


class TestUploadRequest(BaseModel):
    drive_url: str


class TestUploadResponse(BaseModel):
    file_id: str
    file_name: str
    web_view_link: str | None = None


@router.get(
    "/google-drive/status",
    response_model=GoogleDriveStatus,
    dependencies=[Depends(require_permission("erp.view"))],
)
async def google_drive_status() -> GoogleDriveStatus:
    """連携設定の状況（鍵の有無・招待先メール）を返す。"""
    return GoogleDriveStatus(
        configured=google_drive.is_configured(),
        service_account_email=google_drive.get_service_account_email(),
    )


@router.post(
    "/google-drive/test-upload",
    response_model=TestUploadResponse,
    dependencies=[Depends(require_permission("erp.view"))],
)
async def google_drive_test_upload(payload: TestUploadRequest) -> TestUploadResponse:
    """「テスト」PDF を生成し、指定された共有ドライブに保存する。"""
    if not google_drive.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="サーバーに連携用の鍵が未設定です（管理者に連絡してください）。",
        )
    folder_id = google_drive.extract_folder_id(payload.drive_url)
    if not folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="共有ドライブの URL が正しくありません。フォルダの URL を貼り付けてください。",
        )

    pdf_bytes = render_test_pdf("テスト")
    try:
        result = await run_in_threadpool(google_drive.upload_pdf, pdf_bytes, _TEST_PDF_FILENAME, folder_id)
    except Exception as exc:  # noqa: BLE001 — google API の各種例外をまとめて握る
        logger.exception("[integrations] Google Drive へのアップロードに失敗")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "ドライブへの保存に失敗しました。サービスアカウントが共有ドライブに"
                f"招待されているか確認してください。詳細: {exc}"
            ),
        ) from exc

    return TestUploadResponse(
        file_id=result["id"],
        file_name=result["name"],
        web_view_link=result.get("web_view_link"),
    )
