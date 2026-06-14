from __future__ import annotations

"""
リード（leads）テーブル用Pydanticスキーマ。

変更履歴:
  2026-04-16: 初版作成（Phase 1）
  2026-04-27: Phase 1-B-2 Step 5d — リード変換時の旧 customer_id を撤去し、
    company_id / contact_id を必須化（新 B2B モデル唯一の正）
  2026-05-07: ADR-015 §6 ステータス拡張（既存値は維持、新規 5 値を追加）。
    questions/Q01-B「既存 LeadStatus は置き換えではなく拡張」「移行スクリプト
    不要」の方針に従う。
  2026-06-14: ADR-108 Phase B-1 — sales_form 複数選択対応
    SalesFormSelectionCreate / SalesFormSelectionResponse / SalesFormOptionResponse 追加。
    LeadUpdate に sales_form_selections を追加（_UPDATABLE_COLUMNS 外・個別処理）。
    LeadResponse に sales_form_selections / sales_form_options を追加。
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import validate_email_loose, validate_phone


class LeadStatus(str, Enum):
    # ADR-109: 不変コード化（日本語 → immutable codes）
    lead = "lead"                                # アサイン前の新規リード
    negotiating = "negotiating"                  # アサイン済み・商談進行中
    existing_customer = "existing_customer"       # 成約済み・会社情報登録済み
    follow_up_short = "follow_up_short"           # 3 ヶ月以内に再アプローチ予定
    follow_up_long = "follow_up_long"             # 3 ヶ月以上先に再アプローチ予定
    lost = "lost"                                # 失注
    out_of_scope = "out_of_scope"                # スパム / 無関係


class LeadType(str, Enum):
    inbound = "Inbound"
    outbound = "Outbound"


class LeadTemperature(str, Enum):
    hot = "Hot"
    warm = "Warm"
    cold = "Cold"


class LeadScale(str, Enum):
    small = "Small"
    medium = "Medium"
    large = "Large"


class LeadCustomerType(str, Enum):
    trust = "信頼重視"
    price = "価格重視"


class LeadResponseSpeed(str, Enum):
    within_24h = "24h以内"
    within_3d = "3日以内"
    over_3d = "3日超"


# ---------------------------------------------------------------------------
# ADR-108 Phase B-1: sales_form 複数選択スキーマ
# ---------------------------------------------------------------------------

class SalesFormSelectionCreate(BaseModel):
    """PATCH /leads/{id} 用: 販売形態選択アイテム（1件分）"""
    option_id: int = Field(ge=1)
    other_text: str | None = Field(default=None, max_length=1000)


class SalesFormSelectionResponse(BaseModel):
    """GET /leads/{id} レスポンス用: 販売形態選択アイテム（1件分）"""
    option_id: int
    option_value: str
    option_label: str
    other_text: str | None = None


class SalesFormOptionResponse(BaseModel):
    """GET /leads/sales-form-options レスポンス用: テナント別選択肢マスタ"""
    id: int
    label: str
    value: str
    sort_order: int
    is_active: bool


# ---------------------------------------------------------------------------


class LeadCreate(BaseModel):
    """リード登録リクエスト"""
    customer_name: str = Field(min_length=1, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    channel_type: str | None = Field(default=None, max_length=30)
    initiative: str | None = Field(default=None, max_length=10)
    type: LeadType | None = None
    status: LeadStatus = Field(default=LeadStatus.lead)
    temperature: LeadTemperature | None = None
    estimated_scale: LeadScale | None = None
    customer_type: LeadCustomerType | None = None
    response_speed: LeadResponseSpeed | None = None
    monthly_forecast: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    assigned_to: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str | None) -> str | None:
        return validate_email_loose(v)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str | None) -> str | None:
        return validate_phone(v)


class LeadUpdate(BaseModel):
    """リード更新リクエスト（部分更新）"""
    customer_name: str | None = Field(default=None, min_length=1, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    channel_type: str | None = Field(default=None, max_length=30)
    initiative: str | None = Field(default=None, max_length=10)
    type: LeadType | None = None
    status: LeadStatus | None = None
    temperature: LeadTemperature | None = None
    estimated_scale: LeadScale | None = None
    customer_type: LeadCustomerType | None = None
    response_speed: LeadResponseSpeed | None = None
    monthly_forecast: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    assigned_to: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=5000)
    # ADR-015 商談カルテフィールド
    next_action: str | None = Field(default=None, max_length=1000)
    next_action_date: date | None = None
    challenge: str | None = Field(default=None, max_length=2000)
    meeting_memo: str | None = Field(default=None, max_length=2000)
    meeting_impression: str | None = Field(default=None, max_length=255)
    cs_memo: str | None = Field(default=None, max_length=2000)
    sales_form: str | None = Field(default=None, max_length=100)
    # ADR-108 Phase B-1: 複数選択（_UPDATABLE_COLUMNS 外・leads.py で個別処理）
    sales_form_selections: list[SalesFormSelectionCreate] | None = None
    competitor_check: bool | None = None
    per_order_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    monthly_frequency: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    nickname: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    target_titles: str | None = Field(default=None, max_length=500)
    messenger_link: str | None = Field(default=None, max_length=1000)
    discord_id: str | None = Field(default=None, max_length=255)
    instagram_link: str | None = Field(default=None, max_length=1000)
    whatsapp_link: str | None = Field(default=None, max_length=1000)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str | None) -> str | None:
        return validate_email_loose(v)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str | None) -> str | None:
        return validate_phone(v)


class LeadResponse(BaseModel):
    """リード情報レスポンス"""
    id: int
    lead_code: str | None
    customer_name: str
    company_name: str | None
    email: str | None
    phone: str | None
    channel_type: str | None = None
    initiative: str | None = None
    type: str | None
    status: str
    temperature: str | None
    estimated_scale: str | None
    customer_type: str | None
    response_speed: str | None
    monthly_forecast: Decimal | None
    prospect_rank: str | None
    assigned_to: int | None
    converted_deal_id: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    # ADR-015 商談カルテフィールド
    next_action: str | None = None
    next_action_date: date | None = None
    challenge: str | None = None
    meeting_memo: str | None = None
    meeting_impression: str | None = None
    cs_memo: str | None = None
    sales_form: str | None = None
    competitor_check: bool | None = None
    per_order_amount: Decimal | None = None
    monthly_frequency: Decimal | None = None
    nickname: str | None = None
    country: str | None = None
    target_titles: str | None = None
    messenger_link: str | None = None
    discord_id: str | None = None
    instagram_link: str | None = None
    whatsapp_link: str | None = None
    # Discord Gateway fields (read-only, set by dm_writer)
    discord_user_id: str | None = None
    discord_dm_channel_id: str | None = None
    # Discord role sync fields (read-only, set by discord_role_sync service)
    discord_role_sync_status: str | None = None
    discord_role_sync_at: datetime | None = None
    # ADR-107: 顧客優先度スコア（analytics.customer_priority.view 権限所持者のみ意味を持つ）
    priority_score: dict[str, Any] | None = None
    # ADR-108 Phase B-1: 複数選択データ（get_lead で JOIN 取得、list_leads では空リスト）
    sales_form_selections: list[SalesFormSelectionResponse] = Field(default_factory=list)
    # ADR-108 Phase B-1: テナント別選択肢マスタ（get_lead で取得、list_leads では空リスト）
    sales_form_options: list[SalesFormOptionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class LeadStatsResponse(BaseModel):
    """GET /leads/{lead_id}/stats レスポンス（ADR-136: v_company_stats 由来）"""
    total_deal_amount: Decimal
    paid_invoice_count: int
    last_paid_at: datetime | None
    conversation_count: int
    last_conversation_at: datetime | None


class LeadConvertRequest(BaseModel):
    """リード→案件変換リクエスト（Step 5d 以降は company_id + contact_id 必須）"""
    company_id: int = Field(ge=1, description="会社ID")
    contact_id: int = Field(ge=1, description="担当者ID")
    title: str = Field(min_length=1, max_length=255, description="案件タイトル")
    amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    assigned_to: int | None = Field(default=None, ge=1, description="担当者（省略時はリードの担当者を引き継ぐ）")
    notes: str | None = Field(default=None, max_length=5000)
