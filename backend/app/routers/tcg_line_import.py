"""
MIG-04 Phase 2: LINE エクスポートファイルのアップロード取り込み API。

エンドポイント:
  POST /api/v1/tcg/line-import
    multipart/form-data: file=UploadFile (.txt), window_start=str?,
                         window_end=str?, window_hours=int (default=24)
    認証: require_super_admin

  GET /api/v1/tcg/line-import/history
    認証: require_super_admin

  GET /api/v1/tcg/line-import/unresolved
    認証: require_super_admin
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_line_import_svc import TCG_SCHEMA, import_line_export

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ImportResultResponse(BaseModel):
    status: str                          # "imported" | "already_imported"
    message_count: int
    provider_count: int
    unresolved_count: int
    unresolved_display_names: list[str]
    skipped_message_count: int           # SQR-05: 最新以外で棄却されたメッセージ総数
    import_job_id: str


class ImportJobResponse(BaseModel):
    id: str
    filename: str
    raw_sha256: str
    message_count: int
    provider_count: int
    unresolved_count: int
    uploaded_by: Optional[str]
    status: str
    created_at: str


class UnresolvedResponse(BaseModel):
    import_job_id: Optional[str]
    unresolved_count: int
    unresolved_display_names: list[str]


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@router.post(
    "/tcg/line-import",
    response_model=ImportResultResponse,
    dependencies=[Depends(require_super_admin)],
    tags=["super-admin"],
    summary="LINE エクスポートファイルをアップロード・取り込む",
)
async def upload_line_export(
    file: UploadFile = File(..., description=".txt 形式の LINE エクスポートファイル"),
    window_start: Optional[str] = Form(
        default=None,
        description="取り込み開始 timestamp (YYYY-MM-DD HH:MM:00 以上)。省略時は window_hours で自動計算",
    ),
    window_end: Optional[str] = Form(
        default=None,
        description="取り込み終了 timestamp (YYYY-MM-DD HH:MM:00 未満)",
    ),
    window_hours: int = Form(
        default=24,
        description="自動ウィンドウ幅（時間単位）。0 を指定するとフィルタなし（ファイル全体取り込み）",
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_super_admin),
):
    """
    LINE グループチャットのエクスポートテキストファイルをアップロードして取り込む。

    - ファイル全体の SHA-256 で二重取り込みを防ぐ（冪等化）
    - システムイベント（参加・招待・取り消し）を自動除外
    - window_start 未指定かつ window_hours > 0 の場合、直近 window_hours 時間のメッセージのみ取り込む
    - window_hours=0 を指定するとウィンドウフィルタなしでファイル全体を取り込む
    - 同一仕入元の既存メッセージを supersede（is_active=false）に変更
    - 未解決送信者は unresolved_display_names に列挙して取り込みは継続
    """
    # ファイルタイプ簡易チェック
    if file.content_type and "text" not in file.content_type and file.content_type != "application/octet-stream":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="テキスト (.txt) ファイルをアップロードしてください",
        )

    raw_bytes = await file.read()
    try:
        export_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # BOM 付き UTF-8 にも対応
        try:
            export_text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ファイルのエンコーディングが UTF-8 ではありません",
            )

    uploaded_by = getattr(current_user, "email", None) or getattr(current_user, "id", None)
    if uploaded_by is not None:
        uploaded_by = str(uploaded_by)

    result = await import_line_export(
        db=db,
        filename=file.filename or "unknown.txt",
        export_text=export_text,
        uploaded_by=uploaded_by,
        window_start=window_start,
        window_end=window_end,
        window_hours=window_hours,
    )
    return result


@router.get(
    "/tcg/line-import/history",
    response_model=list[ImportJobResponse],
    dependencies=[Depends(require_super_admin)],
    tags=["super-admin"],
    summary="LINE インポート履歴一覧を返す",
)
async def list_import_history(
    db: AsyncSession = Depends(get_db),
):
    """import_jobs を created_at 降順で最大 200 件返す。"""
    rows = await db.execute(
        text(
            f"""
            SELECT id, filename, raw_sha256, message_count, provider_count,
                   unresolved_count, uploaded_by, status,
                   created_at AT TIME ZONE 'UTC' AS created_at
            FROM {TCG_SCHEMA}.import_jobs
            ORDER BY created_at DESC
            LIMIT 200
            """
        )
    )
    result = []
    for r in rows.fetchall():
        result.append(
            ImportJobResponse(
                id=str(r[0]),
                filename=r[1],
                raw_sha256=r[2],
                message_count=r[3],
                provider_count=r[4],
                unresolved_count=r[5],
                uploaded_by=r[6],
                status=r[7],
                created_at=r[8].isoformat() if hasattr(r[8], "isoformat") else str(r[8]),
            )
        )
    return result


@router.get(
    "/tcg/line-import/unresolved",
    response_model=UnresolvedResponse,
    dependencies=[Depends(require_super_admin)],
    tags=["super-admin"],
    summary="最新インポートジョブの未解決送信者情報を返す",
)
async def get_latest_unresolved(
    db: AsyncSession = Depends(get_db),
):
    """
    最新の import_job の unresolved_count と unresolved_display_names を返す。

    注意: unresolved_display_names は import_jobs テーブルには保存されていないため、
    この実装では未解決数のみを返す。詳細名が必要な場合は import 時の API レスポンスを参照。
    """
    row = await db.execute(
        text(
            f"""
            SELECT id, unresolved_count
            FROM {TCG_SCHEMA}.import_jobs
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
    )
    rec = row.fetchone()
    if rec is None:
        return UnresolvedResponse(
            import_job_id=None,
            unresolved_count=0,
            unresolved_display_names=[],
        )
    return UnresolvedResponse(
        import_job_id=str(rec[0]),
        unresolved_count=rec[1],
        unresolved_display_names=[],
    )
