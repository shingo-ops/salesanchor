"""
ANALYSIS-RULE P5: 完売判断 worker (Celery タスク)。

設計書: docs/handoff/tcg-import-latest-only/sold-out-rules-design.md §14.1, §16.4
担当: CARD-ANALYSIS-RULE-P5-API-WORKER

機能:
  run_analysis_rule_task(run_id) → analysis_rule_runs の state を
    running → passed / failed / error に更新する。

  テスト実行 (purpose='test'):
    suite 内の全 case に対してルールマッチングを実行し、結果を
    analysis_rule_run_results に記録する。

  本番実行 (purpose='production'):
    C95: source_message の extraction_items（最新 job のみ）に対して実行。
    invalidated_at IS NULL の結果のみを配信クエリ対象とする（C93）。

注意:
  - Celery は Redis なしでは動作しない。タスクは「定義」のみ。
  - 同期 DB: psycopg2 (DATABASE_URL 環境変数)
  - 全 SQL は TCG_SCHEMA スキーマ修飾必須（ADR-154）
  - test-purpose の run から analysis_results / extraction_jobs / 在庫へ書き込まない
"""
from __future__ import annotations

import json
import logging
import os
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.tcg_config import TCG_SCHEMA

# ---------------------------------------------------------------------------
# 同期 DB エンジン（tcg_extraction.py と同パターン）
# ---------------------------------------------------------------------------

_DB_URL_RAW = os.environ.get(
    "TCG_DB_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://myapp_user:password@localhost:5432/myapp_db",
    ),
)
_DB_URL = _DB_URL_RAW.replace("postgresql+asyncpg", "postgresql+psycopg2").replace(
    "asyncpg://", "psycopg2://"
)

_engine = create_engine(_DB_URL, echo=False)


def _get_sync_session() -> Session:
    return Session(_engine)


# ---------------------------------------------------------------------------
# コアロジック（Celery 非依存）
# ---------------------------------------------------------------------------


def run_analysis_rule(run_id: str) -> dict:
    """
    analysis_rule_runs の state を更新する完売判断ワーカー本体。

    Celery タスクからも直接呼び出せる同期関数。

    Returns:
      {
        "run_id": str,
        "state": str,   # passed / failed / error
        "results_count": int,
        "error_message": str | None,
      }
    """
    session = _get_sync_session()
    try:
        return _execute_analysis_rule_run(session, run_id)
    except Exception as exc:
        logger.exception(
            "[tcg_analysis_rule] unexpected error for run_id=%s: %s", run_id, exc
        )
        # エラー状態を記録
        try:
            with _get_sync_session() as err_session:
                err_session.execute(
                    text(
                        f"""
                        UPDATE public.analysis_rule_runs
                        SET state        = 'error',
                            completed_at = NOW()
                        WHERE id = :run_id AND state IN ('pending', 'running')
                        """
                    ),
                    {"run_id": run_id},
                )
                err_session.commit()
        except Exception:  # noqa: BLE001
            pass
        return {
            "run_id": run_id,
            "state": "error",
            "results_count": 0,
            "error_message": str(exc),
        }
    finally:
        session.close()


def _execute_analysis_rule_run(session: Session, run_id: str) -> dict:
    """実際の完売判断ロジック。"""

    # --- 1. run レコードを取得 ---
    row = session.execute(
        text(
            f"""
            SELECT id, policy_id, revision_id, suite_revision_id,
                   source_message_id, purpose, engine_version, state
            FROM public.analysis_rule_runs
            WHERE id = :run_id
            """
        ),
        {"run_id": run_id},
    ).fetchone()

    if row is None:
        logger.warning("[tcg_analysis_rule] run_id=%s が見つかりません", run_id)
        return {
            "run_id": run_id,
            "state": "error",
            "results_count": 0,
            "error_message": f"run_id={run_id!r} が見つかりません",
        }

    if row.state not in ("pending",):
        logger.warning(
            "[tcg_analysis_rule] run_id=%s の state=%s は処理対象外", run_id, row.state
        )
        return {
            "run_id": run_id,
            "state": row.state,
            "results_count": 0,
            "error_message": None,
        }

    # --- 2. state を running に更新 ---
    session.execute(
        text(
            f"""
            UPDATE public.analysis_rule_runs
            SET state = 'running'
            WHERE id = :run_id AND state = 'pending'
            """
        ),
        {"run_id": run_id},
    )
    session.commit()

    # --- 3. active revision のルール・語句を取得 ---
    rules = _load_revision_rules(session, str(row.revision_id))

    # --- 4. 実行目的に応じて対象を取得 ---
    purpose = row.purpose
    results_count = 0
    final_state = "passed"

    if purpose == "test":
        # テスト実行: suite 内の全 case に対してマッチング
        results_count = _run_test_cases(session, run_id, str(row.suite_revision_id), rules)
    elif purpose == "production":
        # C95: 本番実行: 最新成功 job の items のみ対象
        results_count = _run_production_items(session, run_id, str(row.source_message_id), rules)
    else:
        final_state = "error"
        logger.error("[tcg_analysis_rule] 未知の purpose=%s run_id=%s", purpose, run_id)

    # --- 5. state を passed/failed に更新 ---
    session.execute(
        text(
            f"""
            UPDATE public.analysis_rule_runs
            SET state        = :state,
                completed_at = NOW()
            WHERE id = :run_id
            """
        ),
        {"run_id": run_id, "state": final_state},
    )
    session.commit()

    logger.info(
        "[tcg_analysis_rule] run_id=%s 完了: state=%s results=%d",
        run_id, final_state, results_count,
    )
    return {
        "run_id": run_id,
        "state": final_state,
        "results_count": results_count,
        "error_message": None,
    }


def _load_revision_rules(session: Session, revision_id: str) -> list[dict]:
    """指定 revision のルール・語句一覧をロードする。"""
    rows = session.execute(
        text(
            f"""
            SELECT
                ar.id           AS rule_id,
                arv.id          AS rule_version_id,
                arv.title,
                arv.context_instruction,
                arr.is_deleted,
                w.id            AS word_id,
                w.kind          AS word_kind,
                w.text          AS word_text,
                w.position
            FROM public.analysis_revision_rules arr
            JOIN public.analysis_rules ar ON ar.id = arr.rule_id
            JOIN public.analysis_rule_versions arv ON arv.id = arr.rule_version_id
            LEFT JOIN public.analysis_rule_words w ON w.rule_version_id = arv.id
            WHERE arr.revision_id = :revision_id
              AND arr.is_deleted = FALSE
            ORDER BY arv.id, w.position
            """
        ),
        {"revision_id": revision_id},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def _match_rules(text_input: str, rules: list[dict]) -> dict:
    """
    シンプルなルールマッチング。

    完売 (sold_out): search 語のいずれかが含まれ、exclude 語を含まない → is_sold_out=True
    日付 (date_format): format_template/apply_condition を使ったマッチング

    Returns:
      {
        "is_sold_out": bool | None,
        "matched_rule_version_refs": list[str],
        "source_spans": list[dict],
      }
    """
    search_words: list[str] = []
    exclude_words: list[str] = []
    matched_rule_version_refs: list[str] = []

    for rule in rules:
        if rule.get("word_kind") == "search":
            search_words.append(rule["word_text"])
        elif rule.get("word_kind") == "exclude":
            exclude_words.append(rule["word_text"])

    if not search_words:
        return {
            "is_sold_out": None,
            "matched_rule_version_refs": [],
            "source_spans": [],
        }

    # 除外語チェック
    for ex in exclude_words:
        if ex in text_input:
            return {
                "is_sold_out": False,
                "matched_rule_version_refs": [],
                "source_spans": [],
            }

    # 検索語マッチ
    for rule in rules:
        if rule.get("word_kind") == "search" and rule["word_text"] in text_input:
            matched_rule_version_refs.append(str(rule["rule_version_id"]))

    is_sold_out = len(matched_rule_version_refs) > 0

    return {
        "is_sold_out": is_sold_out,
        "matched_rule_version_refs": matched_rule_version_refs,
        "source_spans": [],
    }


def _run_test_cases(
    session: Session, run_id: str, suite_revision_id: str, rules: list[dict]
) -> int:
    """
    テスト実行: suite 内の全 case に対してルールマッチングを実行し結果を記録する。

    注意: test-purpose の run から analysis_results / 在庫へ書き込まない。
    """
    cases = session.execute(
        text(
            f"""
            SELECT sc.case_id, sc.case_version_id, cv.raw_text, cv.expected
            FROM public.analysis_suite_cases sc
            JOIN public.analysis_test_case_versions cv ON cv.id = sc.case_version_id
            WHERE sc.suite_id = :suite_id
            ORDER BY sc.case_id
            """
        ),
        {"suite_id": suite_revision_id},
    ).fetchall()

    results_count = 0
    for case in cases:
        raw_text = case.raw_text or ""
        expected = case.expected or {}

        match_result = _match_rules(raw_text, rules)

        # expected との比較
        validation_error = None
        expected_sold_out = expected.get("is_sold_out")
        if expected_sold_out is not None and match_result["is_sold_out"] != expected_sold_out:
            validation_error = (
                f"期待値不一致: expected={expected_sold_out} actual={match_result['is_sold_out']}"
            )

        result_id = str(uuid.uuid4())
        session.execute(
            text(
                f"""
                INSERT INTO public.analysis_rule_run_results
                    (id, run_id, case_version_id, decision, source_spans, rule_version_refs, validation_error)
                VALUES
                    (:id, :run_id, :case_version_id,
                     :decision::jsonb, :source_spans::jsonb, :rule_version_refs::jsonb,
                     :validation_error)
                """
            ),
            {
                "id": result_id,
                "run_id": run_id,
                "case_version_id": str(case.case_version_id),
                "decision": json.dumps({"is_sold_out": match_result["is_sold_out"]}, ensure_ascii=False),
                "source_spans": json.dumps(match_result["source_spans"], ensure_ascii=False),
                "rule_version_refs": json.dumps(match_result["matched_rule_version_refs"], ensure_ascii=False),
                "validation_error": validation_error,
            },
        )
        results_count += 1

    session.commit()
    return results_count


def _run_production_items(
    session: Session, run_id: str, source_message_id: str, rules: list[dict]
) -> int:
    """
    本番実行: C95 - 最新成功 job の extraction_items のみを対象にルールマッチングを実行する。

    invalidated_at IS NULL の結果のみが配信クエリ対象（C93 との連携）。
    """
    # C95: status='done' かつ created_at 最新の 1 job の items を取得
    items = session.execute(
        text(
            f"""
            WITH latest_job AS (
                SELECT id FROM {TCG_SCHEMA}.extraction_jobs
                WHERE source_message_id = :msg_id
                  AND status = 'done'
                ORDER BY created_at DESC
                LIMIT 1
            )
            SELECT ei.id, ei.line_start, ei.line_end,
                   ei.raw_product_name, ei.raw_memo,
                   sm.raw_text
            FROM {TCG_SCHEMA}.extraction_items ei
            JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id
            JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
            WHERE ei.extraction_job_id = (SELECT id FROM latest_job)
            ORDER BY ei.line_start
            """
        ),
        {"msg_id": source_message_id},
    ).fetchall()

    results_count = 0
    for item in items:
        # 明細行のテキスト範囲を使ってマッチング
        item_text = item.raw_product_name or ""
        if item.raw_memo:
            item_text = f"{item_text} {item.raw_memo}"

        match_result = _match_rules(item_text, rules)

        result_id = str(uuid.uuid4())
        session.execute(
            text(
                f"""
                INSERT INTO public.analysis_rule_run_results
                    (id, run_id, extraction_item_id, decision, source_spans, rule_version_refs)
                VALUES
                    (:id, :run_id, :extraction_item_id,
                     :decision::jsonb, :source_spans::jsonb, :rule_version_refs::jsonb)
                """
            ),
            {
                "id": result_id,
                "run_id": run_id,
                "extraction_item_id": str(item.id),
                "decision": json.dumps({"is_sold_out": match_result["is_sold_out"]}, ensure_ascii=False),
                "source_spans": json.dumps(match_result["source_spans"], ensure_ascii=False),
                "rule_version_refs": json.dumps(match_result["matched_rule_version_refs"], ensure_ascii=False),
            },
        )
        results_count += 1

    session.commit()
    return results_count


# ---------------------------------------------------------------------------
# Celery タスク定義（Redis 未起動時は登録のみ）
# ---------------------------------------------------------------------------

try:
    from app.celery_app import celery_app

    @celery_app.task(
        name="tcg.run_analysis_rule",
        bind=True,
        max_retries=2,
        default_retry_delay=30,
        time_limit=120,
        soft_time_limit=100,
    )
    def run_analysis_rule_task(self, run_id: str) -> dict:
        """
        Celery タスク: 完売判断 worker を実行する。

        Redis 起動時のみ .delay() で非同期実行可能。
        """
        try:
            return run_analysis_rule(run_id)
        except Exception as exc:
            logger.exception(
                "[tcg_analysis_rule] task failed for run_id=%s: %s", run_id, exc
            )
            raise self.retry(exc=exc) from exc

except Exception as _celery_init_err:  # noqa: BLE001
    logger.warning(
        "[tcg_analysis_rule] Celery task registration skipped: %s", _celery_init_err
    )
    run_analysis_rule_task = None  # type: ignore[assignment]


__all__ = [
    "run_analysis_rule",
    "run_analysis_rule_task",
]
