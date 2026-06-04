"""
ADR-107 (ADR-SA-14): 分析エージェント(A) 顧客優先度付け — Pydantic スキーマ。

出力契約 (§C):
  スコアは必ず「値 + 確信度 + 根拠（効いた信号）」の3点セットで返す。
  裸の断定（is_price_shopper: true 等）を返さない。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageLabelType(str, Enum):
    price_focus = "price_focus"
    substance_talk = "substance_talk"
    self_disclosure = "self_disclosure"
    early_purchase_signal = "early_purchase_signal"
    other = "other"


class ScoreTier(str, Enum):
    watching = "要観察"
    promising = "有望"
    top = "最有望"


class SignalSummary(BaseModel):
    """根拠シグナル。実際に数えた値のみ（作文なし）。"""
    total_messages: int = 0
    inbound_count: int = 0
    price_focus_count: int = 0
    substance_talk_count: int = 0
    self_disclosure_count: int = 0
    early_purchase_signal_count: int = 0
    other_count: int = 0
    won_deals_ref_count: int = 0   # テナント較正の参照母数（スコアの信頼性指標）


class CustomerScoreResponse(BaseModel):
    """
    顧客優先度スコアレスポンス。

    ADR-107 §C: 値 + 確信度 + 根拠の3点セット必須。
    is_cold_start=True の場合は「暫定・判断材料不足」として扱う。
    """
    lead_id: int
    score: float = Field(ge=0.0, le=1.0, description="優先度スコア（0〜1）")
    confidence: float = Field(ge=0.0, le=1.0, description="確信度（0〜1）")
    tier: ScoreTier
    signal_summary: SignalSummary
    sample_size: int = Field(ge=0, description="スコア算出に使ったメッセージ数")
    is_cold_start: bool = Field(description="True=データ不足・暫定値")
    override_score: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description="人手上書きスコア（存在時はこちらを表示優先）",
    )
    override_note: str | None = None
    scored_at: datetime


class ScoreOverrideRequest(BaseModel):
    override_score: float = Field(ge=0.0, le=1.0)
    override_note: str | None = Field(default=None, max_length=500)


class MessageLabelResponse(BaseModel):
    id: int
    message_id: int
    lead_id: int | None
    label: MessageLabelType
    confidence: float = Field(ge=0.0, le=1.0)
    direction: str
    source: str   # "rule" | "llm" | "human"
    override_by: int | None = None
    created_at: datetime


class LabelOverrideRequest(BaseModel):
    label: MessageLabelType
