"""
MIG-04 Stage 2: Celery タスク — Gemini 抽出 + 照合。

1 つの source_message に対して:
  1. extraction_jobs から pending の job を取得
  2. status = 'running' に更新
  3. gemini_extraction_svc.extract_message(raw_text) を呼び出し
  4. items を extraction_items に INSERT
  5. extraction_jobs を 'done'/'empty'/'error' に更新
  6. TCG_AUTO_ANALYZE=1 の場合のみ analyze_extraction_job を呼び出して analysis_results を生成

注意:
  - Celery は Redis なしでは動作しない。タスクは「定義」のみ。
  - 検証時は extract_and_analyze_source_message() を直接呼び出すこと。
  - 同期 DB: psycopg2 (DATABASE_URL 環境変数)
  - 全 SQL は tenant_004 スキーマ修飾必須（ADR-154）
  - 解析発火: 環境変数 TCG_AUTO_ANALYZE=1 でのみ有効（既定 OFF）
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.gemini_extraction_svc import extract_message
from app.services.tcg_analyzer_svc import analyze_extraction_job

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# スキーマ定数（tenant_004 専用）
# ---------------------------------------------------------------------------

TCG_SCHEMA = "tenant_004"

# ---------------------------------------------------------------------------
# 同期 DB エンジン
# ---------------------------------------------------------------------------

_DB_URL_RAW = os.environ.get(
    "TCG_DB_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://myapp_user:password@localhost:5432/myapp_db",
    ),
)
# asyncpg → psycopg2 に置換（async URL が渡された場合の安全策）
_DB_URL = _DB_URL_RAW.replace("postgresql+asyncpg", "postgresql+psycopg2").replace(
    "asyncpg://", "psycopg2://"
)

_engine = create_engine(_DB_URL, echo=False)


def _get_sync_session() -> Session:
    return Session(_engine)


# ---------------------------------------------------------------------------
# コアロジック（Celery 非依存）
# ---------------------------------------------------------------------------


def extract_and_analyze_source_message(source_message_id: str) -> dict:
    """
    1 通の source_message に対して Gemini 抽出 + 照合を実行する。

    Celery タスクからも直接 Python スクリプトからも呼べる同期関数。

    Returns:
      {
        "extraction_job_id": str | None,
        "status": str,
        "items_count": int,
        "analysis_stats": dict | None,
        "error_message": str | None,
      }
    """
    session = _get_sync_session()
    try:
        return _run_extraction(session, source_message_id)
    except Exception as exc:
        logger.exception(
            "[tcg_extraction] unexpected error for sm=%s: %s", source_message_id, exc
        )
        return {
            "extraction_job_id": None,
            "status": "error",
            "items_count": 0,
            "analysis_stats": None,
            "error_message": str(exc),
        }
    finally:
        session.close()


def _run_extraction(session: Session, source_message_id: str) -> dict:
    """実際の抽出ロジック。source_message_id に対応する pending job を処理する。"""

    # --- 1. pending job を取得 ---
    row = session.execute(
        text(
            f"""
            SELECT ej.id, sm.raw_text
            FROM {TCG_SCHEMA}.extraction_jobs ej
            JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id
            WHERE ej.source_message_id = :smid
              AND ej.status = 'pending'
            ORDER BY ej.created_at DESC
            LIMIT 1
            """
        ),
        {"smid": source_message_id},
    ).fetchone()

    if row is None:
        logger.warning(
            "[tcg_extraction] no pending job for sm=%s", source_message_id
        )
        return {
            "extraction_job_id": None,
            "status": "no_pending_job",
            "items_count": 0,
            "analysis_stats": None,
            "error_message": "pending extraction_job が見つかりません",
        }

    extraction_job_id = str(row[0])
    raw_text = row[1] or ""

    # --- 2. status = 'running' に更新 ---
    session.execute(
        text(
            f"UPDATE {TCG_SCHEMA}.extraction_jobs SET status = 'running' WHERE id = :ej_id"
        ),
        {"ej_id": extraction_job_id},
    )
    session.commit()

    # --- 3. Gemini 抽出 ---
    logger.info(
        "[tcg_extraction] calling Gemini for ej=%s", extraction_job_id
    )
    result = extract_message(raw_text)

    items = result["items"]
    final_status = result["status"]  # done / empty / error
    prompt_version = result["prompt_version"]
    error_message = result["error_message"]

    # --- 4. items を extraction_items に INSERT ---
    items_inserted = 0
    if items:
        for item in items:
            item_id = str(uuid.uuid4())
            session.execute(
                text(
                    f"""
                    INSERT INTO {TCG_SCHEMA}.extraction_items (
                        id, extraction_job_id,
                        line_start, line_end,
                        raw_product_name, raw_quantity, raw_price,
                        raw_unit, raw_state, raw_memo,
                        created_at
                    )
                    VALUES (
                        :id, :ej_id,
                        :line_start, :line_end,
                        :raw_product_name, :raw_quantity, :raw_price,
                        :raw_unit, :raw_state, :raw_memo,
                        now()
                    )
                    """
                ),
                {
                    "id": item_id,
                    "ej_id": extraction_job_id,
                    "line_start": item["line_start"],
                    "line_end": item["line_end"],
                    "raw_product_name": item["raw_product_name"] or None,
                    "raw_quantity": item["raw_quantity"] or None,
                    "raw_price": item["raw_price"] or None,
                    "raw_unit": item["raw_unit"] or None,
                    "raw_state": item["raw_state"] or None,
                    "raw_memo": item["raw_memo"] or None,
                },
            )
            items_inserted += 1

    # --- 5. extraction_jobs を更新 ---
    now = datetime.now(timezone.utc)
    session.execute(
        text(
            f"""
            UPDATE {TCG_SCHEMA}.extraction_jobs
            SET status         = :status,
                extracted_at   = :extracted_at,
                prompt_version = :prompt_version,
                error_message  = :error_message
            WHERE id = :ej_id
            """
        ),
        {
            "status": final_status,
            "extracted_at": now if final_status != "error" else None,
            "prompt_version": prompt_version,
            "error_message": error_message,
            "ej_id": extraction_job_id,
        },
    )
    session.commit()

    # --- 6. TCG_AUTO_ANALYZE=1 のときのみ照合実行 ---
    analysis_stats = None
    auto_analyze = os.environ.get("TCG_AUTO_ANALYZE", "").strip() == "1"
    if final_status == "done":
        if auto_analyze:
            logger.info(
                "[tcg_extraction] starting analysis for ej=%s", extraction_job_id
            )
            analysis_stats = analyze_extraction_job(session, extraction_job_id)
        else:
            logger.info(
                "[tcg_extraction] 解析はスキップ（フラグ未設定）: ej=%s", extraction_job_id
            )

    return {
        "extraction_job_id": extraction_job_id,
        "status": final_status,
        "items_count": items_inserted,
        "analysis_stats": analysis_stats,
        "error_message": error_message,
    }


# ---------------------------------------------------------------------------
# Celery タスク定義 (Redis 未起動時は登録のみ)
# ---------------------------------------------------------------------------

try:
    from app.celery_app import celery_app

    @celery_app.task(
        name="tcg.extract_source_message",
        bind=True,
        max_retries=2,
        default_retry_delay=30,
        time_limit=120,
        soft_time_limit=100,
    )
    def extract_source_message_task(self, source_message_id: str) -> dict:
        """
        Celery タスク: 1 通の source_message を Gemini 抽出 + 照合する。

        Redis 起動時のみ .delay() で非同期実行可能。
        """
        try:
            return extract_and_analyze_source_message(source_message_id)
        except Exception as exc:
            logger.exception(
                "[tcg_extraction] task failed for sm=%s: %s", source_message_id, exc
            )
            raise self.retry(exc=exc) from exc

except Exception as _celery_init_err:  # noqa: BLE001
    # Redis 未起動 / Celery 初期化失敗時はタスクなしでモジュールのみ提供
    logger.warning(
        "[tcg_extraction] Celery task registration skipped: %s", _celery_init_err
    )
    extract_source_message_task = None  # type: ignore[assignment]


__all__ = [
    "extract_and_analyze_source_message",
    "extract_source_message_task",
]
