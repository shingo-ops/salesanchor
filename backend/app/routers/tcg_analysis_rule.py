"""
ANALYSIS-RULE P5: 完売ルール・日付ルール共通 API ルーター。

設計書: docs/handoff/tcg-import-latest-only/sold-out-rules-design.md §6.1, §6.2
担当: CARD-ANALYSIS-RULE-P5-API-WORKER

ベースパス: /api/v1/super-admin/analysis-policies/{policy_type}
policy_type: URL は kebab-case (sold-out, date-format) → DB値は snake_case (sold_out, date_format)

エンドポイント:
  GET    {base}/current               ページ開始
  GET    {base}/revisions/{id}/rules  語句一覧
  POST   {base}/draft-revisions       指示/ルール変更
  POST   {base}/test-suites           正解例追加修正
  POST   {base}/test-runs             テスト実行（202）
  GET    {base}/test-runs/{id}        テスト結果
  POST   {base}/activate              本番適用
  GET    {base}/history               変更履歴
  GET    {base}/revisions/{id}        版の詳細

認証: require_super_admin（全エンドポイント共通）
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.models import User
from app.services import tcg_analysis_rule_csv_svc as csv_svc
from app.services import tcg_analysis_rule_svc as svc
from app.services.tcg_analysis_rule_svc import ConflictError

router = APIRouter()

# ---------------------------------------------------------------------------
# policy_type URL変換ヘルパー
# ---------------------------------------------------------------------------

_KEBAB_TO_SNAKE: dict[str, str] = {
    "sold-out": "sold_out",
    "date-format": "date_format",
}


def _resolve_policy_type(policy_type: str) -> str:
    """URL kebab-case → DB snake_case に変換。不正値は 422 を返す。"""
    if policy_type in _KEBAB_TO_SNAKE:
        return _KEBAB_TO_SNAKE[policy_type]
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"policy_type は 'sold-out' または 'date-format' である必要があります: {policy_type!r}",
    )


# ---------------------------------------------------------------------------
# Pydantic スキーマ
# ---------------------------------------------------------------------------


class DraftRevisionCreate(BaseModel):
    expected_draft_id: str | None = None
    expected_active_id: str | None = None
    lock_version: int
    changes: list[dict[str, Any]]
    request_key: UUID


class TestSuiteCreate(BaseModel):
    expected_suite_id: str | None = None
    cases: list[dict[str, Any]]
    request_key: UUID


class TestRunCreate(BaseModel):
    revision_id: str
    suite_revision_id: str
    request_key: UUID


class ActivateRevision(BaseModel):
    revision_id: str
    run_id: str
    expected_active_id: str | None = None
    lock_version: int
    request_key: UUID


# ---------------------------------------------------------------------------
# GET {base}/current
# ---------------------------------------------------------------------------


@router.get(
    "/super-admin/analysis-policies/{policy_type}/current",
    dependencies=[Depends(require_super_admin)],
)
async def get_current_state(
    policy_type: str,
    db: AsyncSession = Depends(get_db),
):
    """ページ開始: active/draft/suite のID、lock_version、activation_state を返す。"""
    pt = _resolve_policy_type(policy_type)
    result = await svc.get_current_state(db, pt)
    if result is None:
        raise HTTPException(status_code=404, detail=f"policy_type={policy_type!r} が見つかりません")
    return result


# ---------------------------------------------------------------------------
# GET {base}/revisions/{id}/rules
# ---------------------------------------------------------------------------


@router.get(
    "/super-admin/analysis-policies/{policy_type}/revisions/{revision_id}/rules",
    dependencies=[Depends(require_super_admin)],
)
async def get_revision_rules(
    policy_type: str,
    revision_id: str,
    q: str | None = Query(default=None, description="テキスト検索"),
    word_kind: str | None = Query(default=None, description="語句種別フィルター"),
    deleted: bool | None = Query(default=None, description="削除済み含む/のみ"),
    cursor: str | None = Query(default=None, description="ページネーション用カーソル"),
    db: AsyncSession = Depends(get_db),
):
    """語句一覧: 指定版から文字検索。word_kind フィルター対応。"""
    pt = _resolve_policy_type(policy_type)
    try:
        result = await svc.get_revision_rules(
            db, revision_id, pt,
            q=q, word_kind=word_kind, deleted=deleted, cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


# ---------------------------------------------------------------------------
# POST {base}/draft-revisions
# ---------------------------------------------------------------------------


@router.post(
    "/super-admin/analysis-policies/{policy_type}/draft-revisions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_super_admin)],
)
async def create_draft_revision(
    policy_type: str,
    data: DraftRevisionCreate,
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """指示/ルール変更: 新版を作って draft 参照のみ更新。"""
    pt = _resolve_policy_type(policy_type)
    try:
        result = await svc.create_draft_revision(
            db, pt,
            expected_draft_id=data.expected_draft_id,
            expected_active_id=data.expected_active_id,
            lock_version=data.lock_version,
            changes=data.changes,
            request_key=str(data.request_key),
            created_by=user.email,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


# ---------------------------------------------------------------------------
# POST {base}/test-suites
# ---------------------------------------------------------------------------


@router.post(
    "/super-admin/analysis-policies/{policy_type}/test-suites",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_super_admin)],
)
async def save_test_suite(
    policy_type: str,
    data: TestSuiteCreate,
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """正解例追加修正: 新しい suite を保存する。"""
    pt = _resolve_policy_type(policy_type)
    try:
        result = await svc.save_test_suite(
            db, pt,
            expected_suite_id=data.expected_suite_id,
            cases=data.cases,
            request_key=str(data.request_key),
            created_by=user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


# ---------------------------------------------------------------------------
# POST {base}/test-runs
# ---------------------------------------------------------------------------


@router.post(
    "/super-admin/analysis-policies/{policy_type}/test-runs",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_super_admin)],
)
async def start_test_run(
    policy_type: str,
    data: TestRunCreate,
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """テスト実行: 202 + run_id を返す。Celery タスクでバックグラウンド実行する。"""
    pt = _resolve_policy_type(policy_type)
    try:
        result = await svc.start_test_run(
            db, pt,
            revision_id=data.revision_id,
            suite_revision_id=data.suite_revision_id,
            request_key=str(data.request_key),
            started_by=user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Celery タスクへエンキュー（Redis 未起動時は登録のみ）
    run_id = result["run_id"]
    try:
        from app.tasks.tcg_analysis_rule import run_analysis_rule_task
        if run_analysis_rule_task is not None:
            run_analysis_rule_task.delay(run_id)
    except Exception as celery_err:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "[tcg_analysis_rule] Celery エンキューに失敗しました（run はキューに残る）: %s", celery_err
        )

    return result


# ---------------------------------------------------------------------------
# GET {base}/test-runs/{run_id}
# ---------------------------------------------------------------------------


@router.get(
    "/super-admin/analysis-policies/{policy_type}/test-runs/{run_id}",
    dependencies=[Depends(require_super_admin)],
)
async def get_test_run_result(
    policy_type: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """テスト結果: expected と actual を原文根拠と併記して返す。"""
    _resolve_policy_type(policy_type)  # バリデーションのみ
    result = await svc.get_test_run_result(db, run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"run_id={run_id!r} が見つかりません")
    return result


# ---------------------------------------------------------------------------
# POST {base}/activate
# ---------------------------------------------------------------------------


@router.post(
    "/super-admin/analysis-policies/{policy_type}/activate",
    dependencies=[Depends(require_super_admin)],
)
async def activate_revision(
    policy_type: str,
    data: ActivateRevision,
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """本番適用: 全検証後 active 参照を更新する。"""
    pt = _resolve_policy_type(policy_type)
    try:
        result = await svc.activate_revision(
            db, pt,
            revision_id=data.revision_id,
            run_id=data.run_id,
            expected_active_id=data.expected_active_id,
            lock_version=data.lock_version,
            request_key=str(data.request_key),
            activated_by=user.email,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


# ---------------------------------------------------------------------------
# GET {base}/history
# ---------------------------------------------------------------------------


@router.get(
    "/super-admin/analysis-policies/{policy_type}/history",
    dependencies=[Depends(require_super_admin)],
)
async def get_history(
    policy_type: str,
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """変更履歴: 変更前後を参照可能。"""
    pt = _resolve_policy_type(policy_type)
    return await svc.get_history(db, pt, cursor=cursor)


# ---------------------------------------------------------------------------
# GET {base}/revisions/{id}
# ---------------------------------------------------------------------------


@router.get(
    "/super-admin/analysis-policies/{policy_type}/revisions/{revision_id}",
    dependencies=[Depends(require_super_admin)],
)
async def get_revision_detail(
    policy_type: str,
    revision_id: str,
    db: AsyncSession = Depends(get_db),
):
    """版の詳細: 指定版の全内容（指示文、ルール、語句）を返す。"""
    _resolve_policy_type(policy_type)  # バリデーションのみ
    result = await svc.get_revision_detail(db, revision_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"revision_id={revision_id!r} が見つかりません")
    return result


# ---------------------------------------------------------------------------
# GET {base}/export — CSV エクスポート
# ---------------------------------------------------------------------------


_MAX_UPLOAD_BYTES = 2 * 1024 * 1024


@router.get(
    "/super-admin/analysis-policies/{policy_type}/export",
    summary="分析ルール語句 CSV エクスポート",
)
async def export_analysis_rule_csv(
    policy_type: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> Response:
    """アクティブ版の語句を BOM 付き UTF-8 CSV でダウンロードする。"""
    pt = _resolve_policy_type(policy_type)
    try:
        raw = await csv_svc.export_csv(db, pt)
    except csv_svc.AnalysisRuleCsvError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    filename = f"analysis-rules-{policy_type}.csv"
    return Response(
        raw,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


# ---------------------------------------------------------------------------
# POST {base}/import/preview — CSV インポートプレビュー
# ---------------------------------------------------------------------------


async def _read_csv_upload(file: UploadFile) -> bytes:
    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(status_code=422, detail="ANALYSIS_RULE_CSV_NOT_CSV")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="ANALYSIS_RULE_CSV_EMPTY_FILE")
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="ANALYSIS_RULE_CSV_FILE_TOO_LARGE")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="ANALYSIS_RULE_CSV_NOT_UTF8") from exc
    return raw


@router.post(
    "/super-admin/analysis-policies/{policy_type}/import/preview",
    summary="分析ルール語句 CSV インポートプレビュー",
)
async def preview_import_analysis_rule_csv(
    policy_type: str,
    file: UploadFile = File(..., description="4列 CSV ファイル（rule_id,title,word_kind,text）"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_super_admin),
) -> dict:
    """CSV をパースして差分（追加/更新/削除件数と詳細）を返す。書き込みなし。"""
    pt = _resolve_policy_type(policy_type)
    raw = await _read_csv_upload(file)
    try:
        return await csv_svc.preview_import(db, pt, raw)
    except csv_svc.AnalysisRuleCsvError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# POST {base}/import/commit — CSV インポートコミット
# ---------------------------------------------------------------------------


@router.post(
    "/super-admin/analysis-policies/{policy_type}/import/commit",
    status_code=status.HTTP_201_CREATED,
    summary="分析ルール語句 CSV インポートコミット",
)
async def commit_import_analysis_rule_csv(
    policy_type: str,
    file: UploadFile = File(..., description="4列 CSV ファイル"),
    lock_version: int = Form(..., description="楽観的ロック用バージョン"),
    draft_revision_id: str | None = Form(default=None),
    active_revision_id: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_super_admin),
) -> dict:
    """差分を changes 配列に変換して draft-revision として保存する。"""
    pt = _resolve_policy_type(policy_type)
    raw = await _read_csv_upload(file)
    try:
        return await csv_svc.commit_import(
            db,
            pt,
            raw,
            user_email=str(user.email or user.id or ""),
            lock_version=lock_version,
            draft_revision_id=draft_revision_id,
            active_revision_id=active_revision_id,
        )
    except csv_svc.AnalysisRuleCsvError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
