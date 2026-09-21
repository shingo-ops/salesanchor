"""Private, job-scoped extraction attempts. No external calls or automatic retries."""
from __future__ import annotations

import hashlib
import json
import logging
from uuid import uuid4

from celery.exceptions import SoftTimeLimitExceeded
from fastapi import HTTPException
from sqlalchemy import text

logger = logging.getLogger(__name__)
MAX_BYTES = 8_388_608


class RecordError(RuntimeError):
    """Fixed codes only: SQL exceptions can contain the entire private payload."""


def encoded(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def bounded(value: str, code: str) -> int:
    size = len(value.encode("utf-8"))
    if size > MAX_BYTES:
        raise RecordError(code)
    return size


def schema_ready(session) -> bool:
    return session.execute(text("SELECT to_regclass(:name) IS NOT NULL"),
                           {"name": "public.extraction_attempts"}).scalar_one()


def limits(session) -> None:
    session.execute(text("SET LOCAL lock_timeout = '1s'"))
    session.execute(text("SET LOCAL statement_timeout = '5s'"))


class AttemptRecorder:
    def __init__(self, session, job_id: str, source_id: str, reference: dict, prompt_version: str):
        self.session = session
        self.id = str(uuid4())
        self.job_id = job_id
        self.source_id = source_id
        self.reference = reference
        self.prompt_version = prompt_version
        self.response_saved = False
        self._oversized_parsed_bytes: int | None = None

    def before_send(self, payload: dict) -> None:
        """The payload is exactly the model/contents/config passed to the SDK."""
        body = encoded({**payload, "reference": self.reference})
        byte_count = len(body.encode("utf-8"))
        oversized = byte_count > MAX_BYTES
        s = self.session
        try:
            limits(s)
            claimed = s.execute(text("""
                UPDATE public.extraction_jobs SET status='running',
                    work_reference_snapshot=CAST(:reference AS JSONB),work_reference_sha256=:sha
                WHERE id=:job AND source_message_id=:source AND status='pending'
                RETURNING id
            """), {"job": self.job_id, "source": self.source_id,
                     "reference": encoded(self.reference), "sha": digest(encoded(self.reference))}).scalar_one_or_none()
            if claimed is None:
                raise RecordError("CLAIM_CONFLICT")
            parent = s.execute(text("""SELECT id FROM public.extraction_attempts
                WHERE extraction_job_id=:job ORDER BY started_at DESC,id DESC LIMIT 1
            """), {"job": self.job_id}).scalar_one_or_none()
            s.execute(text("""INSERT INTO public.extraction_attempts
                (id,extraction_job_id,source_message_id,parent_attempt_id,input_payload,input_sha256,
                 input_bytes,requested_model,prompt_version)
                VALUES (:id,:job,:source,:parent,CAST(:body AS JSONB),:sha,:size,:model,:version)
            """), {"id": self.id, "job": self.job_id, "source": self.source_id,
                     "parent": parent, "body": None if oversized else body, "sha": digest(body),
                     "size": byte_count, "model": payload["model"], "version": self.prompt_version})
            s.commit()
        except (RecordError, SoftTimeLimitExceeded):
            s.rollback()
            raise
        except Exception:
            s.rollback()
            raise RecordError("RECORD_WRITE_FAILED") from None
        if oversized:
            raise RecordError("INPUT_TOO_LARGE")

    def _owned(self, *, required: bool = True) -> bool:
        """Lock the job first, matching claim ordering. A newer child fences this attempt."""
        s = self.session
        limits(s)
        job = s.execute(text("""SELECT status FROM public.extraction_jobs
            WHERE id=:job AND source_message_id=:source FOR UPDATE
        """), {"job": self.job_id, "source": self.source_id}).scalar_one_or_none()
        row = s.execute(text("""SELECT phase FROM public.extraction_attempts a
            WHERE a.id=:id AND a.extraction_job_id=:job
            AND NOT EXISTS (SELECT 1 FROM public.extraction_attempts child
                WHERE child.parent_attempt_id=a.id)
        """), {"id": self.id, "job": self.job_id}).scalar_one_or_none()
        owned = job == "running" and row in ("started", "received")
        if required and not owned:
            raise RecordError("ATTEMPT_CONFLICT")
        return owned

    def on_response(self, response: str) -> None:
        s = self.session
        size = len(response.encode("utf-8"))
        oversized = size > MAX_BYTES
        try:
            self._owned()
            s.execute(text("""UPDATE public.extraction_attempts SET phase='received',
                response_text=:body,response_bytes=:size,response_sha256=:sha,
                response_received_at=clock_timestamp() WHERE id=:id AND phase='started'
                RETURNING id
            """), {"id": self.id, "body": None if oversized else response,
                     "size": size, "sha": digest(response)}).scalar_one()
            s.commit()
        except (RecordError, SoftTimeLimitExceeded):
            s.rollback()
            raise
        except Exception:
            s.rollback()
            raise RecordError("RECORD_WRITE_FAILED") from None
        if oversized:
            raise RecordError("RESPONSE_TOO_LARGE")
        self.response_saved = True

    def _parsed_size(self, body: str) -> int:
        size = len(body.encode("utf-8"))
        if size > MAX_BYTES:
            self._oversized_parsed_bytes = size
            raise RecordError("PARSED_TOO_LARGE")
        return size

    def prepare_items(self, items: list[dict]) -> list[dict]:
        if not self.response_saved:
            raise RecordError("RESPONSE_NOT_RECORDED")
        rows = [{**item, "extraction_item_id": str(uuid4()), "response_item_number": i}
                for i, item in enumerate(items, 1)]
        self._parsed_size(encoded(rows))
        self._owned()
        return rows

    def complete(self, items: list[dict]) -> None:
        """Do not commit here: caller commits items, job and this row together."""
        body = encoded(items)
        size = self._parsed_size(body)
        self.session.execute(text("""UPDATE public.extraction_attempts
            SET phase='completed',finished_at=clock_timestamp(),parsed_items=CAST(:items AS JSONB),
                parsed_bytes=:size,item_count=:count,validation_result='{"status":"passed"}'::jsonb
            WHERE id=:id AND phase='received' AND response_text IS NOT NULL
            RETURNING id
        """), {"id": self.id, "items": body, "size": size, "count": len(items)}).scalar_one()

    def fail(self, code: str) -> None:
        """One bounded, best-effort failure write. Terminal/foreign attempts stay unchanged."""
        s = self.session
        try:
            s.rollback()
            if self._owned(required=False):
                s.execute(text("""UPDATE public.extraction_attempts SET phase='failed',
                    finished_at=clock_timestamp(),error_code=:code,
                    parsed_bytes=COALESCE(:parsed_bytes,parsed_bytes),
                    validation_result=jsonb_build_object('status','failed','code',CAST(:code AS text))
                    WHERE id=:id
                """), {"id": self.id, "code": code,
                         "parsed_bytes": self._oversized_parsed_bytes if code == "PARSED_TOO_LARGE" else None})
                s.execute(text("""UPDATE public.extraction_jobs SET status='error',
                    error_message=:code,extracted_at=NULL,prompt_version=:version WHERE id=:job
                """), {"job": self.job_id, "code": code, "version": self.prompt_version})
                s.commit()
            else:
                s.rollback()
        except Exception:
            s.rollback()
            logger.error("extraction_attempt=%s code=RECORD_WRITE_FAILED", self.id)


async def read_attempts(db, job_id: str, *, attempt_id: str | None = None,
                        limit: int = 25, offset: int = 0) -> dict:
    """Only called by the super-admin router; schema never comes from a request."""
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(status_code=422, detail="Invalid pagination")
    job = (await db.execute(text("SELECT id FROM public.extraction_jobs WHERE id=:job"),
                            {"job": job_id})).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    fields = "*" if attempt_id else (
        "id,extraction_job_id,source_message_id,parent_attempt_id,started_at,response_received_at,"
        "finished_at,phase,error_code,input_bytes,response_bytes,parsed_bytes,item_count,prompt_version,requested_model"
    )
    rows = (await db.execute(text(f"""SELECT {fields} FROM public.extraction_attempts
        WHERE extraction_job_id=:job AND (CAST(:attempt AS uuid) IS NULL OR id=CAST(:attempt AS uuid))
        ORDER BY started_at DESC,id DESC LIMIT :limit OFFSET :offset
    """), {"job": job_id, "attempt": attempt_id, "limit": limit, "offset": offset})).mappings().all()
    if attempt_id and not rows:
        raise HTTPException(status_code=404, detail="Extraction attempt not found")
    result = [dict(row) for row in rows]
    for row in result:
        row["completion"] = "unconfirmed" if row["phase"] in ("started", "received") else row["phase"]
    return {"extraction_job_id": job_id, "attempts": result}
