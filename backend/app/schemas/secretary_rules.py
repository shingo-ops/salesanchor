"""ADR-1077 便2b: 決まり帳の口の入れ物（design.md §3「大きさ」・§4・§5）。

決まりの文の検査（前後の空白を落とす・150 字まで・改行以外の制御文字を断る）は、このファイルの clean_rule_text だけに書く。
150 は表の CHECK（migrations/20261113_100000_create_secretary_rules.sql の ck_secretary_rules_rule_text_len）と同じ数。
"""

from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RULE_TEXT_MAX = 150

# 一覧の口で選べる状態（捨てた・外した物は一覧に出さない）
RuleStatus = Literal["candidate", "approved"]
# 元になった秘書の答えの種類（表の CHECK ck_secretary_rules_source_kind と同じ 5 つ）
SourceKind = Literal["invoice", "event", "unknown", "rule_proposal", "rule_list"]


def has_control_chars(value: str) -> bool:
    """改行以外の制御文字（Unicode の分類 Cc。タブ・復帰・NUL など）があれば True。"""
    return any(ch != "\n" and unicodedata.category(ch) == "Cc" for ch in value)


def clean_rule_text(value: str, *, allow_empty: bool) -> str:
    """前後の空白を落とし、空・151 字以上・制御文字入りを断る（ValueError。口は 422 を返す）。"""
    value = value.strip()
    if not value and not allow_empty:
        raise ValueError("rule_text is empty")
    if len(value) > RULE_TEXT_MAX:
        raise ValueError("rule_text is too long")
    if has_control_chars(value):
        raise ValueError("rule_text has control characters")
    return value


class RuleTextIn(BaseModel):
    """承認する決まりの文（POST /assistant/rules・POST /assistant/rules/{rule_id}/approve）。"""

    model_config = ConfigDict(extra="forbid")

    rule_text: str

    @field_validator("rule_text")
    @classmethod
    def _check_rule_text(cls, value: str) -> str:
        return clean_rule_text(value, allow_empty=False)


class RuleFeedbackIn(BaseModel):
    """「違う」の 1 往復（POST /assistant/rules/feedback。候補として入る。rule_text は空でよい）。"""

    model_config = ConfigDict(extra="forbid")

    source_text: str = Field(min_length=1, max_length=1000)
    source_kind: SourceKind
    source_reply: str | None = Field(default=None, max_length=200)
    rule_text: str = ""

    @field_validator("rule_text")
    @classmethod
    def _check_rule_text(cls, value: str) -> str:
        return clean_rule_text(value, allow_empty=True)

    @field_validator("source_text", "source_reply")
    @classmethod
    def _no_nul(cls, value: str | None) -> str | None:
        # PostgreSQL の text には NUL を入れられない（入れると 500 になる）ため、ここで断る
        if value is not None and "\x00" in value:
            raise ValueError("NUL is not allowed")
        return value


class RuleOut(BaseModel):
    id: int
    status: Literal["candidate", "approved", "rejected", "removed"]
    rule_text: str
    source_text: str | None
    source_kind: str | None
    source_reply: str | None
    created_at: datetime
    decided_at: datetime | None


class RuleListOut(BaseModel):
    rules: list[RuleOut]
