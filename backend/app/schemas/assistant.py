"""ADR-1056 段2: チャット秘書の入出力。

容器 secretary-agent の答え（AgentEnvelope / Intent）と、画面へ返す形（AssistantMessageOut）。
余分な欄は拒む（extra="forbid"）。kind と値を持つ欄の食い違いは Intent の検査で落とす。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssistantMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


# ---- 容器の答え -------------------------------------------------------------


class IntentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_name: str = Field(min_length=1)
    quantity: int = Field(ge=1)
    unit_price: float | None = None


class IntentInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = None
    contact_name: str | None = None
    items: list[IntentItem]
    due_date: str | None = None
    notes: str | None = None


class IntentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    start: str
    end: str | None = None
    is_all_day: bool = False
    location: str | None = None
    description: str | None = None


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["invoice", "event", "unknown"]
    invoice: IntentInvoice | None = None
    event: IntentEvent | None = None
    reply: str | None = None

    @model_validator(mode="after")
    def _kind_matches_fields(self) -> "Intent":
        # kind に合う欄だけが値を持ち、ほかは null
        expected = {
            "invoice": (self.invoice is not None, self.event is None, self.reply is None),
            "event": (self.event is not None, self.invoice is None, self.reply is None),
            "unknown": (self.reply is not None, self.invoice is None, self.event is None),
        }[self.kind]
        if not all(expected):
            raise ValueError("kind と値を持つ欄が合いません")
        return self


class AgentEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    total_cost_usd: float | None = None


def parse_iso(value: str) -> datetime:
    """ISO 8601 を datetime に読む（末尾 Z も許す）。読めなければ ValueError。"""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ---- 画面へ返す形 -----------------------------------------------------------


class Candidate(BaseModel):
    id: int
    name: str


class Candidates(BaseModel):
    companies: list[Candidate] = Field(default_factory=list)
    contacts: list[Candidate] = Field(default_factory=list)


class DraftItem(BaseModel):
    product_name: str
    quantity: int
    unit_price: float | None = None


class InvoiceDraft(BaseModel):
    company_name: str | None = None
    contact_name: str | None = None
    items: list[DraftItem]
    due_date: str | None = None
    notes: str | None = None
    currency: Literal["JPY"] = "JPY"


class EventDraft(BaseModel):
    title: str
    start: str
    end: str
    is_all_day: bool = False
    location: str | None = None
    description: str | None = None
    calendar_type: Literal["personal"] = "personal"


class UnknownDraft(BaseModel):
    reply: str


class AssistantMessageOut(BaseModel):
    kind: Literal["invoice", "event", "unknown"]
    draft: InvoiceDraft | EventDraft | UnknownDraft
    candidates: Candidates = Field(default_factory=Candidates)
