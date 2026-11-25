"""ADR-1056 段2: チャット秘書の入出力。

容器 secretary-agent の答え（AgentEnvelope / Intent）と、画面へ返す形（AssistantMessageOut）。
余分な欄は拒む（extra="forbid"）。kind と値を持つ欄の食い違いは Intent の検査で落とす。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

# ADR-1078: 予定のカルテで聞く欄（聞く順は app/services/secretary_karte.py の ASK_ORDER）
AskField = Literal["title", "start", "end", "add_meet"]


class KarteIn(BaseModel):
    """ADR-1078: 画面が会話の間だけ持つ予定のカルテ（保存しない）。字数・型・回数の上限をここで守る。"""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, max_length=1000)
    start: str | None = Field(None, max_length=40)
    end: str | None = Field(None, max_length=40)
    is_all_day: bool = False
    location: str | None = Field(None, max_length=1000)
    description: str | None = Field(None, max_length=1000)
    is_meeting: bool = False
    add_meet: bool | None = None
    asked: AskField | None = None
    asked_count: int = Field(0, ge=0, le=2)
    # 便W: 真なら「入れますか？」の確かめ待ちの下書きを声で直す頼み（AI が値を返した欄だけ替える）
    edit: bool = False

    @field_validator("start", "end")
    @classmethod
    def _iso_or_none(cls, value: str | None) -> str | None:
        # 読めない時刻は 422（parse_iso が ValueError を出す）
        if value is not None:
            parse_iso(value)
        return value


class AssistantMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    # ADR-1078: 新しい画面は 1 通目から必ずこの鍵を送る（1 通目は null）。鍵の有無は model_fields_set で見る
    karte: KarteIn | None = None


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

    # ADR-1078: AI は分からない欄を null で返す。is_meeting・add_meet は初期値があるので古い容器の答えも通る
    title: str | None = Field(None, max_length=1000)
    start: str | None = None
    end: str | None = None
    is_all_day: bool = False
    location: str | None = Field(None, max_length=1000)
    description: str | None = Field(None, max_length=1000)
    is_meeting: bool = False
    add_meet: bool | None = None


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


class AgentUsage(BaseModel):
    """ADR-1058 段3: secretary-codex が返す使用量（turn.completed の4つ。どれも 0 以上の整数か None。design.md §5-1）。"""

    model_config = ConfigDict(extra="forbid")

    input_tokens: StrictInt | None = Field(default=None, ge=0)
    cached_input_tokens: StrictInt | None = Field(default=None, ge=0)
    output_tokens: StrictInt | None = Field(default=None, ge=0)
    reasoning_output_tokens: StrictInt | None = Field(default=None, ge=0)


class AgentEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    total_cost_usd: float | None = None
    # ADR-1058 段3: secretary-codex だけが返す2欄（secretary-agent は返さないので None のまま。design.md §5-3）
    usage: AgentUsage | None = None
    error_events: StrictInt | None = Field(default=None, ge=0)


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
    # ADR-1078: 新しい画面の道では空いた欄を null で返し、ask で次に聞く欄を知らせる
    title: str | None
    start: str | None
    end: str | None
    is_all_day: bool = False
    location: str | None = None
    description: str | None = None
    calendar_type: Literal["personal"] = "personal"
    is_meeting: bool = False
    add_meet: bool | None = None
    meet_available: bool = False
    ask: AskField | None = None
    ask_count: int = 0
    # 便W: 直す頼みの答えのときだけ真偽（直せたか）。ほかは null
    edited: bool | None = None
    # 便W2: 直す頼みの答えのとき、Meet を付けてと言われたが付けられない人だったか（ほかは null）
    meet_refused: bool | None = None
    # 便W3: 直す頼みで、AI は直しを返したが日時を失って前のままに戻したか。ほかは null
    edit_dropped: bool | None = None


class UnknownDraft(BaseModel):
    reply: str


class AssistantMessageOut(BaseModel):
    kind: Literal["invoice", "event", "unknown"]
    draft: InvoiceDraft | EventDraft | UnknownDraft
    candidates: Candidates = Field(default_factory=Candidates)


class VoiceOut(BaseModel):
    """ADR-1080: 秘書の声の一覧・既定・本人の選び（design.md §4-3）。"""

    voices: list[str]
    default: str
    selected: str


class VoiceIn(BaseModel):
    voice: str  # 一覧に無い値は router で 422（型の中に声の一覧を写さない）


class SpeechIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank")
        return v
