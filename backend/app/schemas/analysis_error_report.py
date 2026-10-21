"""ADR-1025 便1: 解析の誤り報告 API のスキーマ。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ReportFieldName = Literal["product_id", "quantity", "price", "unit", "condition", "status", "note"]


class ErrorReportField(BaseModel):
    field_name: ReportFieldName
    expected_value: Any = None
    expected_missing_product: bool = False


class ErrorReportRequest(BaseModel):
    fields: list[ErrorReportField] = Field(min_length=1)

    @model_validator(mode="after")
    def _no_duplicate_fields(self) -> "ErrorReportRequest":
        names = [f.field_name for f in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("field_name must not be duplicated")
        return self


class ErrorReportResponse(BaseModel):
    report_code: str
    notified: bool
