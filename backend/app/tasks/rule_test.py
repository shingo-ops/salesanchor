"""
Rule Test Celery Task — ルールテスト実行

tcg_status_master の enabled ルールに対してテストケースを実行し、
期待値と実際の結果を比較する。

resolve_status_v2 を直接インポートして本番と同一ロジックで判定（SSOT）。
"""
import logging
import os
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import create_engine, text

from app.services.tcg_analyzer_svc import resolve_status_v2, load_status_master

logger = logging.getLogger(__name__)

_DB_URL = os.environ.get("TCG_DB_URL") or os.environ.get("DATABASE_URL", "")


def _get_sync_engine():
    url = _DB_URL
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
    elif url.startswith("postgresql://"):
        pass  # already sync
    return create_engine(url)


def execute_rule_test(run_id: str) -> dict:
    """Synchronous rule test execution."""
    engine = _get_sync_engine()
    with engine.connect() as conn:
        # Update state to running
        conn.execute(
            text("UPDATE public.rule_test_runs SET state = 'running' WHERE id = :id"),
            {"id": run_id},
        )
        conn.commit()

        try:
            # Load enabled rules from tcg_status_master (SSOT)
            from sqlalchemy.orm import Session
            with Session(engine) as session:
                status_entries = load_status_master(session)

            # Load test cases
            cases = conn.execute(
                text("SELECT id, input_text, expected_canonical, expected_effect FROM public.rule_test_cases ORDER BY id")
            ).mappings().all()

            passed = 0
            failed = 0
            results = []

            for case in cases:
                # Run resolve_status_v2 with the same logic as production
                actual_canonical, actual_effect = resolve_status_v2(
                    case["input_text"], status_entries
                )

                # Compare: canonical must match AND effect must match
                is_match = (
                    actual_canonical == case["expected_canonical"]
                    and (actual_effect or None) == (case["expected_effect"] or None)
                )

                if is_match:
                    passed += 1
                else:
                    failed += 1

                results.append({
                    "run_id": run_id,
                    "case_id": case["id"],
                    "input_text": case["input_text"],
                    "expected_canonical": case["expected_canonical"],
                    "expected_effect": case["expected_effect"],
                    "actual_canonical": actual_canonical,
                    "actual_effect": actual_effect,
                    "is_match": is_match,
                })

            # Save results
            for r in results:
                conn.execute(
                    text("""
                        INSERT INTO public.rule_test_run_results
                        (run_id, case_id, input_text, expected_canonical, expected_effect,
                         actual_canonical, actual_effect, is_match)
                        VALUES (:run_id, :case_id, :input_text, :expected_canonical, :expected_effect,
                                :actual_canonical, :actual_effect, :is_match)
                    """),
                    r,
                )

            # Update run state
            state = "passed" if failed == 0 else "failed"
            conn.execute(
                text("""
                    UPDATE public.rule_test_runs
                    SET state = :state, completed_at = :completed_at,
                        total_cases = :total, passed_cases = :passed, failed_cases = :failed
                    WHERE id = :id
                """),
                {
                    "id": run_id,
                    "state": state,
                    "completed_at": datetime.now(timezone.utc),
                    "total": len(cases),
                    "passed": passed,
                    "failed": failed,
                },
            )
            conn.commit()

            return {"run_id": run_id, "state": state, "total": len(cases), "passed": passed, "failed": failed}

        except Exception as exc:
            logger.exception("Rule test run %s failed", run_id)
            conn.execute(
                text("""
                    UPDATE public.rule_test_runs
                    SET state = 'error', completed_at = :completed_at, error_message = :msg
                    WHERE id = :id
                """),
                {
                    "id": run_id,
                    "completed_at": datetime.now(timezone.utc),
                    "msg": str(exc)[:500],
                },
            )
            conn.commit()
            return {"run_id": run_id, "state": "error", "error": str(exc)}


@shared_task(name="rule_test.execute", bind=True, max_retries=1, time_limit=60)
def run_rule_test_task(self, run_id: str):
    return execute_rule_test(run_id)
