"""ADR-1025 便2: 自動セッション用の口 3 つ（取得・出来事の記録・再解析）のスキーマ。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# 表 analysis_error_report_events.payload の CHECK（octet_length <= 8192）と同じ上限
PAYLOAD_MAX_BYTES = 8192


class OpsReportHeader(BaseModel):
    report_code: str
    extraction_item_id: str
    extraction_job_id: str
    status: str
    reported_at: datetime


class OpsReportField(BaseModel):
    field_name: str
    system_value: Any = None
    expected_value: Any = None
    expected_missing_product: bool = False


class OpsReportEvent(BaseModel):
    at: datetime
    actor: str
    kind: str
    payload: dict[str, Any]


class OpsReportDetail(BaseModel):
    report: OpsReportHeader
    fields: list[OpsReportField]
    current_values: dict[str, Any]
    prompt_version: str | None
    events: list[OpsReportEvent]


class OpsEventRequest(BaseModel):
    kind: Literal["cause", "action"]
    actor: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def _payload_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > PAYLOAD_MAX_BYTES:
            raise ValueError(f"payload must be at most {PAYLOAD_MAX_BYTES} bytes")
        return value


class OpsEventResponse(BaseModel):
    id: int


class OpsReanalyzeResponse(BaseModel):
    task_id: str
