from __future__ import annotations

"""
請求書（invoices / invoice_items）用Pydanticスキーマ。

変更履歴:
  2026-04-17: 初版作成（Phase 2）
  2026-04-27: Phase 1-B-2 Step 5d — 旧 customer_id を撤去し、
    company_id / contact_id を必須化（新 B2B モデル唯一の正）
"""

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InvoiceStatus(str, Enum):
    draft = "draft"
    issued = "issued"
    paid = "paid"
    overdue = "overdue"
    voided = "voided"


class InvoiceItemInput(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    product_name: str = Field(min_length=1, max_length=255)
    # 海外顧客向け明細: name_en=英語タイトル / condition=状態 / unit=形態
    name_en: str | None = Field(default=None, max_length=255)
    condition: str | None = Field(default=None, max_length=50)
    unit: str | None = Field(default=None, max_length=20)
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    weight: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=3)


class PaymentMethodRef(BaseModel):
    """支払方法の選び方（design.md §3-4）。bank・wise は版の id、paypal は id なし。"""
    model_config = ConfigDict(extra="forbid")
    method_type: Literal["bank", "wise", "paypal"]
    id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _id_matches_type(self):
        if self.method_type == "paypal" and self.id is not None:
            raise ValueError("paypal_takes_no_id")
        if self.method_type != "paypal" and self.id is None:
            raise ValueError("id_required")
        return self


class ShippingInput(BaseModel):
    """送料の選び方（design.md §3-4 の送料の規則）。calculate=/shipping/calculate の結果の1つ、none=送料を請求しない。"""
    model_config = ConfigDict(extra="forbid")
    mode: Literal["calculate", "none"]
    carrier: str | None = Field(default=None, max_length=50)
    service_type: str | None = Field(default=None, max_length=100)
    fee: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @model_validator(mode="after")
    def _fields_match_mode(self):
        if self.mode == "calculate":
            if not (self.carrier and self.carrier.strip()) or self.fee is None or not self.currency:
                raise ValueError("calculate_needs_carrier_fee_currency")
        elif any(v is not None for v in (self.carrier, self.service_type, self.fee, self.currency)):
            raise ValueError("none_takes_no_fields")
        return self


class InvoiceCreate(BaseModel):
    """請求書登録リクエスト。額（送料・消費税・為替）は受けず、サーバーが計算する（invoice-create-portfolio 便C）。"""
    model_config = ConfigDict(extra="forbid")
    company_id: int = Field(ge=1, description="会社ID")
    contact_id: int = Field(ge=1, description="担当者ID")
    currency: str = Field(default="JPY", min_length=3, max_length=3)
    shipping: ShippingInput | None = None
    payment_method_ref: PaymentMethodRef | None = None
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    items: list[InvoiceItemInput] = Field(min_length=1)


class InvoicePreviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


class InvoicePreviewRequest(BaseModel):
    """試算（書かない）。作る道と同じ材料で額だけを返す。"""
    model_config = ConfigDict(extra="forbid")
    company_id: int = Field(ge=1)
    currency: str = Field(min_length=3, max_length=3)
    items: list[InvoicePreviewItem] = Field(default_factory=list)
    shipping: ShippingInput | None = None


class InvoicePreviewResponse(BaseModel):
    currency: str
    subtotal: Decimal
    shipping_fee: Decimal | None
    tax_amount: Decimal | None
    tax_rate_percent: Decimal | None
    duty_amount: Decimal | None
    duty_label: str | None
    duty_components: list[dict]
    total_amount: Decimal | None
    uncomputed: list[str]
    incoterms: str


class DraftContextAddress(BaseModel):
    company_name: str | None = None
    billing_display_name: str | None = None
    label: str | None = None
    postal_code: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    phone: str | None = None
    # invoice-create-portfolio R1（design-v2 §3-2）
    recipient_name: str | None = None
    email: str | None = None
    tax_id: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    address_line_3: str | None = None
    country_name: str | None = None


class DraftContextFx(BaseModel):
    currency: str
    rate: float
    fetched_at: str | None


class DraftContextPayment(BaseModel):
    id: int | None
    method_type: str
    display_name: str | None
    wise_currency: str | None


class DraftContextResponse(BaseModel):
    company_id: int
    ship_to: DraftContextAddress | None
    bill_to: DraftContextAddress | None
    contact_name: str | None
    contact_email: str | None
    issuer_region: str | None
    origin_country_code: str | None
    destination_country_code: str | None
    destination_postal_code: str | None
    currencies: list[str]
    fx_rates: list[DraftContextFx]
    default_currency: str | None
    currency: str | None
    payment_methods: list[DraftContextPayment]
    tax_rate_percent: Decimal | None
    incoterms: str


class InvoiceUpdate(BaseModel):
    """下書きの直し（design.md §3-4 の PATCH）。為替と支払方法の文字は受けない。"""
    model_config = ConfigDict(extra="forbid")
    payment_method_ref: PaymentMethodRef | None = None
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)


class VoidRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class InvoiceItemResponse(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    # 海外顧客向け明細: name_en=英語タイトル / condition=状態 / unit=形態
    name_en: str | None = None
    condition: str | None = None
    unit: str | None = None
    quantity: int
    unit_price: Decimal
    weight: Decimal | None
    subtotal: Decimal
    sort_order: int
    # C-6: HS コード（輸出用）
    hs_code: str | None = None

    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    """請求書情報レスポンス。

    Note: PR γ (Step 5d) で `contact_id` を必須化したが、対象は tenant_004 のみ
    (migration 035 の precondition で 0 件保証)。`invoices.contact_id` は migration 032 で
    nullable に追加され NOT NULL 化されておらず、後発作成テナント (例: tenant_006) には
    demo/seed で contact_id IS NULL の行が存在しうる。一覧/詳細レスポンスがそれで 500 に
    ならないよう `int | None` で許容する (作成リクエスト InvoiceCreate は引き続き必須)。
    """
    id: int
    invoice_number: str | None
    quote_id: int | None
    company_id: int
    contact_id: int | None
    currency: str
    subtotal: Decimal | None
    shipping_fee: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    exchange_rate_jpy: Decimal | None
    exchange_rate_usd: Decimal | None
    amount_jpy: Decimal | None
    amount_usd: Decimal | None
    payment_method: str | None
    status: str
    branch_number: int | None
    pdf_url: str | None
    erp_key: str | None
    issued_at: datetime | None
    due_date: date | None
    paid_at: datetime | None
    voided_at: datetime | None
    void_reason: str | None
    notes: str | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime
    # C-6: スナップショット列（migration で追加、古いレコードは NULL）
    ship_to_snapshot: dict | None = None
    bill_to_snapshot: dict | None = None
    issue_mode: str | None = None
    duty_amount: Decimal | None = None
    duty_policy_snapshot: dict | None = None
    fx_rate_snapshot: dict | None = None
    # ADR-101 PayPal mode1: 決済リンク（リンク発行で order_id/approval_url、capture で fee 記録）
    paypal_order_id: str | None = None
    paypal_approval_url: str | None = None
    payment_fee: Decimal | None = None
    # ADR-101改訂(2) Inc1: 発行者ビュー URL（原本ワンクリック）。写しPDF blob は Response に含めない
    paypal_invoicer_view_url: str | None = None
    paypal_copy_pdf_at: datetime | None = None
    # ADR-1061 便2-2c2a: 発行元の地域（domestic / overseas。作成時に請求先の国で決める。古い請求書は NULL）
    issuer_region: str | None = None
    # invoice-create-portfolio 便A・便C: 案内した振込先の版・使った税率・送料の会社とサービス・送料の写し
    payment_method_id: int | None = None
    tax_rate_percent: Decimal | None = None
    shipping_carrier: str | None = None
    shipping_service: str | None = None
    shipping_snapshot: dict | None = None

    model_config = {"from_attributes": True}

    # ADR-1061 便2-2c2a（D13）: 写しの列は本番（PostgreSQL の JSONB）では dict で返るが、
    # 試験の SQLite では TEXT に JSON の文字で入っているため、文字なら dict に読み直す。
    # 先例: routers/tenant_commission_settings.py の commission_rates の読み方。
    @field_validator(
        "ship_to_snapshot", "bill_to_snapshot", "duty_policy_snapshot", "fx_rate_snapshot", "shipping_snapshot",
        mode="before",
    )
    @classmethod
    def _parse_json_snapshot(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class InvoiceDetailResponse(InvoiceResponse):
    items: list[InvoiceItemResponse] = []
    # 便C: payment_method_id の版の表示（口座番号は返さない。design.md §3-4）
    payment_method_display_name: str | None = None
    payment_method_type: str | None = None


# invoice-create-portfolio R3（design-v2 §3-5）: 請求書の送料の一覧の入力。届け先・発送元はサーバーが決める。
class DraftShippingQuotesRequest(BaseModel):
    company_id: int = Field(ge=1)
    weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
