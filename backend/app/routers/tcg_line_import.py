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

【確認工程（review stage）エンドポイント】
  GET  /api/v1/tcg/line-import/pending
    pending_review のジョブ一覧

  GET  /api/v1/tcg/line-import/{import_job_id}
    保留中ジョブの詳細（unresolved_names, 件数, 窓）

  POST /api/v1/tcg/line-import/{import_job_id}/resolve
    仕入元の登録・差し替え

  POST /api/v1/tcg/line-import/{import_job_id}/commit
    確認完了後に source_messages を書き込む
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.services.tcg_line_import_svc import (
    TCG_SCHEMA,
    _enqueue_extraction,
    _write_source_messages,
    build_provider_entries,
    import_line_export,
    resolve_suppliers,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ImportResultResponse(BaseModel):
    status: str                          # "imported" | "already_imported"
    review_status: str                   # "ok" | "pending_review"
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
    review_status: str
    created_at: str


class UnresolvedResponse(BaseModel):
    import_job_id: Optional[str]
    unresolved_count: int
    unresolved_display_names: list[str]


class PendingJobDetail(BaseModel):
    """保留中ジョブの詳細（pending_messages の本文は返さない）。"""
    id: str
    filename: str
    message_count: int
    unresolved_count: int
    unresolved_names: list[str]
    window_start: Optional[str]
    window_end: Optional[str]
    review_status: str
    created_at: str


class ResolveRequest(BaseModel):
    display_name: str
    action: str            # "assign" | "create"
    supplier_code: str     # assign: 既存仕入元コード / create: 任意（採番で上書き）


class ResolveResponse(BaseModel):
    success: bool
    remaining_unresolved: list[str]


class CommitResponse(BaseModel):
    status: str            # "committed"
    provider_count: int
    enqueued_count: int


# ---------------------------------------------------------------------------
# エンドポイント: アップロード取り込み
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
    - 窓は JST 基準で計算（旧実装の UTC 基準による 33h 問題を是正）
    - 未解決の仕入元が 0 件なら即時書き込み・エンキュー（review_status='ok'）
    - 未解決の仕入元が 1 件以上なら source_messages を書かず保留（review_status='pending_review'）
    """
    if file.content_type and "text" not in file.content_type and file.content_type != "application/octet-stream":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="テキスト (.txt) ファイルをアップロードしてください",
        )

    raw_bytes = await file.read()
    try:
        export_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
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


# ---------------------------------------------------------------------------
# エンドポイント: 一覧 / 詳細 / 保留一覧
#
# 【重要】固定パス（/history, /pending, /unresolved）は可変パス（/{import_job_id}）
# より前に定義する。FastAPI はルートを定義順に評価するため、可変パスが先にあると
# 固定パス文字列が UUID パラメータとして誤評価される（IMP-39 で本番障害として発覚）。
# ---------------------------------------------------------------------------


@router.get(
    "/tcg/line-import/pending",
    response_model=list[PendingJobDetail],
    dependencies=[Depends(require_super_admin)],
    tags=["super-admin"],
    summary="確認待ち（pending_review）のジョブ一覧を返す",
)
async def list_pending_jobs(
    db: AsyncSession = Depends(get_db),
):
    """review_status='pending_review' のジョブを created_at 降順で最大 100 件返す。"""
    rows = await db.execute(
        text(
            f"""
            SELECT id, filename, message_count, unresolved_count,
                   unresolved_names,
                   window_start AT TIME ZONE 'UTC' AS window_start,
                   window_end   AT TIME ZONE 'UTC' AS window_end,
                   review_status,
                   created_at   AT TIME ZONE 'UTC' AS created_at
            FROM {TCG_SCHEMA}.import_jobs
            WHERE review_status = 'pending_review'
            ORDER BY created_at DESC
            LIMIT 100
            """
        )
    )
    result = []
    for r in rows.fetchall():
        names = r[4] if r[4] is not None else []
        if isinstance(names, str):
            names = json.loads(names)
        result.append(
            PendingJobDetail(
                id=str(r[0]),
                filename=r[1],
                message_count=r[2],
                unresolved_count=r[3],
                unresolved_names=names,
                window_start=r[5].isoformat() if r[5] and hasattr(r[5], "isoformat") else (str(r[5]) if r[5] else None),
                window_end=r[6].isoformat() if r[6] and hasattr(r[6], "isoformat") else (str(r[6]) if r[6] else None),
                review_status=r[7],
                created_at=r[8].isoformat() if hasattr(r[8], "isoformat") else str(r[8]),
            )
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
                   unresolved_count, uploaded_by, status, review_status,
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
                review_status=r[8] if r[8] is not None else "ok",
                created_at=r[9].isoformat() if hasattr(r[9], "isoformat") else str(r[9]),
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
    最新の import_job の unresolved_count と unresolved_names を返す。
    """
    row = await db.execute(
        text(
            f"""
            SELECT id, unresolved_count, unresolved_names
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
    names = rec[2] if rec[2] is not None else []
    if isinstance(names, str):
        names = json.loads(names)
    return UnresolvedResponse(
        import_job_id=str(rec[0]),
        unresolved_count=rec[1],
        unresolved_display_names=names,
    )


@router.get(
    "/tcg/line-import/{import_job_id}",
    response_model=PendingJobDetail,
    dependencies=[Depends(require_super_admin)],
    tags=["super-admin"],
    summary="保留中ジョブの詳細を返す",
)
async def get_pending_job(
    import_job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    指定 import_job_id の保留中ジョブの詳細を返す。
    pending_messages の本文は返さない（サイズが大きいため）。
    """
    row = await db.execute(
        text(
            f"""
            SELECT id, filename, message_count, unresolved_count,
                   unresolved_names,
                   window_start AT TIME ZONE 'UTC' AS window_start,
                   window_end   AT TIME ZONE 'UTC' AS window_end,
                   review_status,
                   created_at   AT TIME ZONE 'UTC' AS created_at
            FROM {TCG_SCHEMA}.import_jobs
            WHERE id = :job_id
            """
        ),
        {"job_id": import_job_id},
    )
    rec = row.fetchone()
    if rec is None:
        raise HTTPException(status_code=404, detail="import_job が見つかりません")

    names = rec[4] if rec[4] is not None else []
    if isinstance(names, str):
        names = json.loads(names)

    return PendingJobDetail(
        id=str(rec[0]),
        filename=rec[1],
        message_count=rec[2],
        unresolved_count=rec[3],
        unresolved_names=names,
        window_start=rec[5].isoformat() if rec[5] and hasattr(rec[5], "isoformat") else (str(rec[5]) if rec[5] else None),
        window_end=rec[6].isoformat() if rec[6] and hasattr(rec[6], "isoformat") else (str(rec[6]) if rec[6] else None),
        review_status=rec[7],
        created_at=rec[8].isoformat() if hasattr(rec[8], "isoformat") else str(rec[8]),
    )


# ---------------------------------------------------------------------------
# エンドポイント: 確認工程
# ---------------------------------------------------------------------------


@router.post(
    "/tcg/line-import/{import_job_id}/resolve",
    response_model=ResolveResponse,
    dependencies=[Depends(require_super_admin)],
    tags=["super-admin"],
    summary="未解決仕入元を登録・差し替えする",
)
async def resolve_supplier(
    import_job_id: str,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    保留中ジョブの未解決仕入元を解決する。

    action='assign': 指定した仕入元の name を display_name に差し替える。
                     別の既存仕入元と name が重複する場合は 409。
    action='create': tcg_suppliers に新規登録 + supplier_channels を1件作成。
                     code は既存の最大値+1 を採番。

    どちらも import_jobs.unresolved_names から該当名を除く。
    """
    # ジョブ取得
    job_row = await db.execute(
        text(
            f"""
            SELECT review_status, unresolved_names
            FROM {TCG_SCHEMA}.import_jobs
            WHERE id = :job_id
            """
        ),
        {"job_id": import_job_id},
    )
    job = job_row.fetchone()
    if job is None:
        raise HTTPException(status_code=404, detail="import_job が見つかりません")
    if job[0] != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"review_status={job[0]} のジョブは変更できません",
        )

    current_names: list[str] = job[1] if job[1] is not None else []
    if isinstance(current_names, str):
        current_names = json.loads(current_names)

    if body.display_name not in current_names:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{body.display_name}' は unresolved_names に含まれていません",
        )

    if body.action == "assign":
        # 対象仕入元の name を display_name に差し替え
        sup_row = await db.execute(
            text(
                f"SELECT id, name FROM {TCG_SCHEMA}.tcg_suppliers WHERE code = :code AND is_active = TRUE"
            ),
            {"code": body.supplier_code},
        )
        sup = sup_row.fetchone()
        if sup is None:
            raise HTTPException(
                status_code=404,
                detail=f"supplier_code={body.supplier_code} が見つかりません",
            )

        # 重複チェック: 差し替え後の name が他の仕入元と衝突しないか
        dup_row = await db.execute(
            text(
                f"""
                SELECT id FROM {TCG_SCHEMA}.tcg_suppliers
                WHERE name = :name AND id != :self_id AND is_active = TRUE
                """
            ),
            {"name": body.display_name, "self_id": str(sup[0])},
        )
        if dup_row.fetchone() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{body.display_name}' は別の仕入元に既に使われています（重複名は照合が壊れます）",
            )

        # name を差し替え
        await db.execute(
            text(
                f"UPDATE {TCG_SCHEMA}.tcg_suppliers SET name = :name WHERE id = :id"
            ),
            {"name": body.display_name, "id": str(sup[0])},
        )

    elif body.action == "create":
        # 新規仕入元: code は最大値+1 を採番（SP プレフィックスは既存に合わせる）
        max_code_row = await db.execute(
            text(f"SELECT MAX(code) FROM {TCG_SCHEMA}.tcg_suppliers")
        )
        max_code = max_code_row.scalar()
        # code は "SP0001" 形式を想定。数値部分を+1
        if max_code:
            prefix = "".join(c for c in max_code if c.isalpha())
            num = int("".join(c for c in max_code if c.isdigit()) or "0") + 1
            new_code = f"{prefix}{num:04d}"
        else:
            new_code = "SP0001"

        new_supplier_id = uuid.uuid4()
        await db.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.tcg_suppliers
                  (id, code, name, is_active, created_at)
                VALUES
                  (:id, :code, :name, TRUE, now())
                """
            ),
            {"id": str(new_supplier_id), "code": new_code, "name": body.display_name},
        )

        # supplier_channels を1件作成（channel='line'）
        new_sc_id = uuid.uuid4()
        await db.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.supplier_channels
                  (id, supplier_id, channel, is_active, created_at)
                VALUES
                  (:id, :supplier_id, 'line', TRUE, now())
                """
            ),
            {"id": str(new_sc_id), "supplier_id": str(new_supplier_id)},
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action は 'assign' または 'create' を指定してください",
        )

    # unresolved_names から該当名を除く
    remaining = [n for n in current_names if n != body.display_name]
    await db.execute(
        text(
            f"""
            UPDATE {TCG_SCHEMA}.import_jobs
            SET unresolved_names = :names, unresolved_count = :cnt
            WHERE id = :job_id
            """
        ),
        {
            "names": json.dumps(remaining, ensure_ascii=False),
            "cnt": len(remaining),
            "job_id": import_job_id,
        },
    )

    await db.commit()

    return ResolveResponse(success=True, remaining_unresolved=remaining)


@router.post(
    "/tcg/line-import/{import_job_id}/commit",
    response_model=CommitResponse,
    dependencies=[Depends(require_super_admin)],
    tags=["super-admin"],
    summary="確認完了後に source_messages を書き込む",
)
async def commit_pending_job(
    import_job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    保留中ジョブの pending_messages を使って source_messages を書き込む。

    - review_status が 'pending_review' でなければ 409
    - pending_messages と保存済みの窓を使い、仕入元を再解決
    - まだ未解決が残っていれば 409 と残りの名前を返す（進めない）
    - 全件解決していれば supersede + INSERT + commit 後にエンキュー
    - review_status = 'ok' に更新
    """
    # ジョブ取得
    job_row = await db.execute(
        text(
            f"""
            SELECT review_status, pending_messages, window_start, window_end
            FROM {TCG_SCHEMA}.import_jobs
            WHERE id = :job_id
            """
        ),
        {"job_id": import_job_id},
    )
    job = job_row.fetchone()
    if job is None:
        raise HTTPException(status_code=404, detail="import_job が見つかりません")
    if job[0] != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"review_status={job[0]} のジョブはコミットできません",
        )

    pending_messages_raw = job[1]
    if pending_messages_raw is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="pending_messages が空です",
        )
    if isinstance(pending_messages_raw, str):
        messages = json.loads(pending_messages_raw)
    else:
        messages = pending_messages_raw

    # 最新の仕入元マスタで再解決
    suppliers_rows = await db.execute(
        text(f"SELECT code, name FROM {TCG_SCHEMA}.tcg_suppliers WHERE is_active = TRUE")
    )
    db_suppliers = [{"code": r[0], "name": r[1]} for r in suppliers_rows.fetchall()]

    resolved_msgs, still_unresolved = resolve_suppliers(messages, db_suppliers)
    if still_unresolved:
        remaining_names = [u["display_name"] for u in still_unresolved]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "まだ未解決の仕入元があります。resolve してから commit してください",
                "unresolved_names": remaining_names,
            },
        )

    # 全件解決済み: 書き込み
    provider_entries = build_provider_entries(resolved_msgs)
    provider_count = len(provider_entries)

    enqueued_ids = await _write_source_messages(db, provider_entries)

    # import_jobs を更新
    await db.execute(
        text(
            f"""
            UPDATE {TCG_SCHEMA}.import_jobs
            SET review_status = 'ok',
                provider_count = :prov_count,
                unresolved_count = 0,
                pending_messages = NULL
            WHERE id = :job_id
            """
        ),
        {"prov_count": provider_count, "job_id": import_job_id},
    )

    await db.commit()

    for sm_id in enqueued_ids:
        _enqueue_extraction(sm_id)

    return CommitResponse(
        status="committed",
        provider_count=provider_count,
        enqueued_count=len(enqueued_ids),
    )
