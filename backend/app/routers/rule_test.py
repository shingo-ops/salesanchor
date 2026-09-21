"""
Rule Test System — ルールテスト API
tcg_status_master (SSOT) のルール検証用テスト実行

ADR-027 準拠: エラーメッセージは i18n キー or 英語定型文
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.celery_app import celery_app

router = APIRouter(tags=["rule-test"])


# --- Pydantic Models ---

class TestCaseCreate(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=2000)
    expected_canonical: str = Field(..., min_length=1, max_length=200)
    expected_effect: str | None = None  # "excluded" or None
    note: str = ""

class TestCaseResponse(BaseModel):
    id: int
    input_text: str
    expected_canonical: str
    expected_effect: str | None
    note: str
    created_at: datetime

class TestRunResponse(BaseModel):
    id: str
    state: str
    started_by: str
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    total_cases: int
    passed_cases: int
    failed_cases: int

class TestRunResultItem(BaseModel):
    case_id: int
    input_text: str
    expected_canonical: str
    expected_effect: str | None
    actual_canonical: str | None
    actual_effect: str | None
    is_match: bool

class TestRunDetailResponse(TestRunResponse):
    results: list[TestRunResultItem]

class TestRunStartResponse(BaseModel):
    run_id: str
    state: str


# --- Endpoints ---

@router.get(
    "/super-admin/rule-tests/cases",
    response_model=list[TestCaseResponse],
    dependencies=[Depends(require_super_admin)],
)
async def list_test_cases(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        text("SELECT id, input_text, expected_canonical, expected_effect, note, created_at FROM public.rule_test_cases ORDER BY id")
    )).mappings().all()
    return [dict(r) for r in rows]


@router.post(
    "/super-admin/rule-tests/cases",
    response_model=TestCaseResponse,
    status_code=201,
    dependencies=[Depends(require_super_admin)],
)
async def create_test_case(data: TestCaseCreate, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        text("""
            INSERT INTO public.rule_test_cases (input_text, expected_canonical, expected_effect, note)
            VALUES (:input_text, :expected_canonical, :expected_effect, :note)
            RETURNING id, input_text, expected_canonical, expected_effect, note, created_at
        """),
        {
            "input_text": data.input_text,
            "expected_canonical": data.expected_canonical,
            "expected_effect": data.expected_effect,
            "note": data.note,
        },
    )).mappings().one()
    await db.commit()
    return dict(row)


@router.delete(
    "/super-admin/rule-tests/cases/{case_id}",
    status_code=204,
    dependencies=[Depends(require_super_admin)],
)
async def delete_test_case(case_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("DELETE FROM public.rule_test_cases WHERE id = :id"),
        {"id": case_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Test case not found")
    await db.commit()


@router.post(
    "/super-admin/rule-tests/run",
    response_model=TestRunStartResponse,
    status_code=202,
    dependencies=[Depends(require_super_admin)],
)
async def start_test_run(db: AsyncSession = Depends(get_db)):
    # Check test cases exist
    count = (await db.execute(text("SELECT COUNT(*) FROM public.rule_test_cases"))).scalar()
    if count == 0:
        raise HTTPException(status_code=400, detail="No test cases registered")

    # Create run record
    row = (await db.execute(
        text("""
            INSERT INTO public.rule_test_runs (state, started_by, total_cases)
            VALUES ('pending', '', :total)
            RETURNING id, state
        """),
        {"total": count},
    )).mappings().one()
    await db.commit()

    run_id = str(row["id"])

    # Enqueue Celery task
    celery_app.send_task("rule_test.execute", args=[run_id])

    return {"run_id": run_id, "state": "pending"}


@router.get(
    "/super-admin/rule-tests/runs/latest",
    response_model=TestRunDetailResponse | None,
    dependencies=[Depends(require_super_admin)],
)
async def get_latest_run(db: AsyncSession = Depends(get_db)):
    run_row = (await db.execute(
        text("""
            SELECT id, state, started_by, started_at, completed_at, error_message,
                   total_cases, passed_cases, failed_cases
            FROM public.rule_test_runs
            ORDER BY started_at DESC LIMIT 1
        """)
    )).mappings().first()

    if not run_row:
        return None

    results = (await db.execute(
        text("""
            SELECT case_id, input_text, expected_canonical, expected_effect,
                   actual_canonical, actual_effect, is_match
            FROM public.rule_test_run_results
            WHERE run_id = :run_id ORDER BY id
        """),
        {"run_id": run_row["id"]},
    )).mappings().all()

    return {
        **dict(run_row),
        "id": str(run_row["id"]),
        "results": [dict(r) for r in results],
    }


@router.get(
    "/super-admin/rule-tests/gate",
    dependencies=[Depends(require_super_admin)],
)
async def check_gate(db: AsyncSession = Depends(get_db)):
    """Check if rule enable gate is open (latest test run passed)."""
    state = (await db.execute(
        text("SELECT state FROM public.rule_test_runs ORDER BY started_at DESC LIMIT 1")
    )).scalar()
    return {"gate_open": state == "passed", "latest_state": state}
