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
from datetime import datetime, timezone

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.gemini_extraction_svc import extract_message
from app.services.tcg_analyzer_svc import analyze_extraction_job, resolve_work_evidence
from app.services.tcg_extraction_record_svc import AttemptRecorder, RecordError, schema_ready
from app.services.tcg_work_reference import (
    WORK_ID_PROMPT_VERSION,
    WORK_ID_PROMPT_VERSIONS,
    load_work_reference,
    reference_digest,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# スキーマ定数（tenant_004 専用）
# ---------------------------------------------------------------------------

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
    except Exception:
        logger.exception("[tcg_extraction] unexpected error for sm=%s", source_message_id)
        return {
            "extraction_job_id": None,
            "status": "error",
            "items_count": 0,
            "analysis_stats": None,
            "error_message": "EXTRACTION_FAILED",
        }
    finally:
        session.close()


def work_schema_ready(session: Session) -> bool:
    count = session.execute(text(f"""
        SELECT count(*) FROM pg_attribute
        WHERE NOT attisdropped AND (
            (attrelid = 'public.extraction_items'::regclass AND attname IN ('resolved_work_id', 'resolved_product_code'))
            OR (attrelid = 'public.extraction_jobs'::regclass
                AND attname IN ('work_reference_snapshot', 'work_reference_sha256')))
    """)).scalar_one()
    return count == 4


def _run_extraction(session: Session, source_message_id: str) -> dict:
    """実際の抽出ロジック。source_message_id に対応する pending job を処理する。"""

    # --- 1. pending job を取得 ---
    row = session.execute(
        text(
            f"""
            SELECT ej.id, sm.raw_text
            FROM public.extraction_jobs ej
            JOIN public.source_messages sm ON sm.id = ej.source_message_id
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

    if not work_schema_ready(session) or not schema_ready(session):
        return {"extraction_job_id": str(row[0]), "status": "pending", "items_count": 0,
                "analysis_stats": None, "error_message": "Extraction record / Work-ID schema migration is not ready"}
    reference = load_work_reference(session, "public")
    extraction_job_id = str(row[0])
    raw_text = row[1] or ""

    # C94: 空テキストチェック — strip後0文字なら Gemini スキップ
    # 設計根拠: sold-out-rules-design.md §14.1.2
    if len(raw_text.strip()) == 0:
        session.execute(
            text(
                f"UPDATE public.extraction_jobs "
                "SET status = 'empty', extracted_at = NOW(), error_message = NULL "
                "WHERE id = :ej_id"
            ),
            {"ej_id": extraction_job_id},
        )
        session.commit()
        return {
            "extraction_job_id": extraction_job_id,
            "status": "empty",
            "items_count": 0,
            "analysis_stats": None,
            "error_message": None,
        }

    recorder = AttemptRecorder(session, extraction_job_id, source_message_id, reference, WORK_ID_PROMPT_VERSION)
    try:
        return _run_recorded_extraction(session, extraction_job_id, raw_text, reference, recorder)
    except SoftTimeLimitExceeded:
        code = "SOFT_TIME_LIMIT"
    except RecordError as exc:
        code = str(exc)
    except Exception:
        logger.exception("[tcg_extraction] record write failed for ej=%s", extraction_job_id)
        code = "RECORD_WRITE_FAILED"
    recorder.fail(code)
    message = "Work ID contradicts explicit source evidence" if code == "WORK_ID_CONFLICT" else code
    return {"extraction_job_id": extraction_job_id, "status": "error", "items_count": 0,
            "analysis_stats": None, "error_message": message}


def _run_recorded_extraction(session, extraction_job_id, raw_text, reference, recorder):
    result = extract_message(raw_text, work_reference=reference, recorder=recorder)
    if result["status"] == "error":
        raise RecordError(result.get("error_code", "INVALID_RESPONSE"))
    digest = reference_digest(reference)
    # Never retain a DB transaction across the external call.
    if result["status"] in ("done", "empty"):
        try:
            current = load_work_reference(session, "public")
            if reference_digest(current) != digest:
                raise RecordError("REFERENCE_CHANGED")
            if result["prompt_version"] in WORK_ID_PROMPT_VERSIONS:
                for item in result["items"]:
                    explicit = resolve_work_evidence(
                        item["raw_product_name"], raw_text, item["line_start"], item["line_end"],
                        None, None, reference["works"],
                    )
                    if explicit and item.get("resolved_work_id") not in (None, int(explicit)):
                        logger.warning(
                            "[tcg_extraction] WORK_ID_CONFLICT for ej=%s: gemini=%s evidence=%s, setting to None",
                            extraction_job_id, item.get("resolved_work_id"), explicit,
                        )
                        item["resolved_work_id"] = None
        except SoftTimeLimitExceeded:
            raise
        except Exception as exc:
            session.rollback()
            result = {**result, "status": "error", "items": [],
                      "error_message": str(exc) if isinstance(exc, RecordError) else "INVALID_RESPONSE"}

    if result["status"] == "error":
        raise RecordError(result["error_message"])
    items = recorder.prepare_items(result["items"])
    final_status = result["status"]  # done / empty / error
    prompt_version = result["prompt_version"]
    error_message = result["error_message"]

    # --- 4. items を extraction_items に INSERT ---
    items_inserted = 0
    if items:
        for item in items:
            item_id = item["extraction_item_id"]
            session.execute(
                text(
                    f"""
                    INSERT INTO public.extraction_items (
                        id, extraction_job_id,
                        line_start, line_end,
                        raw_product_name, raw_quantity, raw_price,
                        raw_unit, raw_state, raw_memo,
                        raw_work_name, raw_work_source_line_span, resolved_work_id,
                        resolved_product_code,
                        created_at
                    )
                    VALUES (
                        :id, :ej_id,
                        :line_start, :line_end,
                        :raw_product_name, :raw_quantity, :raw_price,
                        :raw_unit, :raw_state, :raw_memo,
                        :raw_work_name, :raw_work_source_line_span, :resolved_work_id,
                        :resolved_product_code,
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
                    "resolved_work_id": item.get("resolved_work_id"),
                    "raw_work_name": item.get("raw_work_name"),
                    "raw_work_source_line_span": item.get("raw_work_source_line_span"),
                    "resolved_product_code": item.get("resolved_product_code"),
                },
            )
            items_inserted += 1

    recorder.complete(items)

    # --- 5. extraction_jobs を更新 ---
    now = datetime.now(timezone.utc)
    session.execute(
        text(
            f"""
            UPDATE public.extraction_jobs
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
            try:
                analysis_stats = analyze_extraction_job(session, extraction_job_id)
            except Exception:
                session.rollback()
                logger.error("extraction_attempt=%s code=ANALYSIS_FAILED", recorder.id)
                analysis_stats = {"status": "error", "error_code": "ANALYSIS_FAILED"}

            # 解析完了後に自動配信をトリガー（TCG_AUTO_DISTRIBUTE=1 のときのみ）
            auto_distribute = os.environ.get("TCG_AUTO_DISTRIBUTE", "").strip() == "1"
            if auto_distribute and (analysis_stats is None or analysis_stats.get("status") != "error"):
                _enqueue_auto_distribute()
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
# 自動配信エンキュー（Redis 未起動時は no-op）
# ---------------------------------------------------------------------------


def _enqueue_auto_distribute() -> None:
    """
    auto_distribute_after_analysis_task を非同期でエンキューする。

    Redis が起動していない場合は握りつぶしてスキップする。
    """
    try:
        if auto_distribute_after_analysis_task is not None:
            auto_distribute_after_analysis_task.delay()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[tcg_extraction] auto_distribute enqueue skipped: %s", exc)


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
        time_limit=330,
        soft_time_limit=300,
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

    @celery_app.task(
        name="tcg.auto_distribute_after_analysis",
        bind=True,
        max_retries=1,
        default_retry_delay=60,
        time_limit=600,
        soft_time_limit=540,
    )
    def auto_distribute_after_analysis_task(self) -> dict:
        """
        Celery タスク: 解析完了後の自動配信。

        run_distribution() の安全装置（#8/#8b/#8c）が pending job の残存を検知した場合は
        スキップ扱いとなり、次の extraction 完了時に再トリガーされる。
        Redis 起動時のみ .delay() で非同期実行可能。
        """
        import asyncio  # noqa: PLC0415

        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: PLC0415

        from app.database import DATABASE_URL  # noqa: PLC0415
        from app.services.tcg_distribution_svc import run_distribution  # noqa: PLC0415

        async def _run() -> dict:
            # asyncio.run() は新規イベントループを作成するため、
            # モジュールレベルの AsyncSessionLocal（エンジンが旧ループに紐付き）を
            # そのまま使うと RuntimeError: attached to a different loop が発生する。
            # 回避策: ワンショット用エンジン＋セッションをここで生成し、finally で確実に破棄する。
            _connect_args: dict = {
                "prepared_statement_cache_size": 0,
                "server_settings": {"application_name": "salesanchor_celery_distribute"},
            }
            _engine = create_async_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                pool_size=2,
                max_overflow=0,
                connect_args=_connect_args,
            )
            _Session = async_sessionmaker(_engine, expire_on_commit=False)
            try:
                async with _Session() as db:
                    return await run_distribution(db)
            finally:
                await _engine.dispose()

        try:
            result = asyncio.run(_run())
            logger.info("[tcg_extraction] auto_distribute result: %s", result)
            return result
        except Exception as exc:
            logger.exception("[tcg_extraction] auto_distribute failed: %s", exc)
            raise self.retry(exc=exc) from exc

except Exception as _celery_init_err:  # noqa: BLE001
    # Redis 未起動 / Celery 初期化失敗時はタスクなしでモジュールのみ提供
    logger.warning(
        "[tcg_extraction] Celery task registration skipped: %s", _celery_init_err
    )
    extract_source_message_task = None  # type: ignore[assignment]
    auto_distribute_after_analysis_task = None  # type: ignore[assignment]


__all__ = [
    "extract_and_analyze_source_message",
    "extract_source_message_task",
    "auto_distribute_after_analysis_task",
]
