"""
決済手数料設定（public.payment_fee_settings）用 Pydantic スキーマ。

§D01: PO承認2026-10-02
パターン: public + NULLパターン（public.unitsと同一方式）
  tenant_id IS NULL = 共用デフォルト（運営者管理）
  tenant_id = X    = テナント独自設定

手数料計算式: 対象金額 × rate_pct / 100 + fixed_amount
閾値条件: threshold + threshold_rule (above/below) で適用条件を決定
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PaymentFeeSettingBase(BaseModel):
    service: str = Field(
        min_length=1, max_length=30,
        description="決済サービス名（例: paypal, wise, stripe）",
    )
    fee_type: str = Field(
        min_length=1, max_length=50,
        description="手数料種別（例: receiving_domestic=国内受取, withdrawal=出金, fx_receiving=為替受取時）",
    )
    rate_pct: Decimal = Field(
        default=Decimal(0), ge=0, max_digits=8, decimal_places=4,
        description="料率（%）。手数料 = 対象金額 × rate_pct / 100 + fixed_amount",
    )
    fixed_amount: Decimal = Field(
        default=Decimal(0), ge=0, max_digits=14, decimal_places=2,
        description="固定手数料額（通貨単位）。rate_pctと併用",
    )
    threshold: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=14, decimal_places=2,
        description="閾値金額。threshold_ruleと組み合わせて適用条件を決定。NULLは無条件適用",
    )
    threshold_rule: Optional[str] = Field(
        default=None, max_length=10,
        description="閾値ルール。above=閾値以上で適用, below=閾値未満で適用",
    )
    currency: str = Field(
        default="JPY", min_length=3, max_length=3,
        description="通貨コード（ISO 4217）",
    )
    effective_from: date = Field(
        description="適用開始日。料金改定時は新行を追加",
    )
    effective_to: Optional[date] = Field(
        default=None,
        description="適用終了日。NULLは現在有効",
    )
    source_url: Optional[str] = Field(
        default=None,
        description="料率の出典URL（公式料金ページ等）",
    )
    note: Optional[str] = Field(
        default=None,
        description="補足説明（日本語）。管理画面表示・運用メモ用",
    )


class PaymentFeeSettingCreate(PaymentFeeSettingBase):
    pass


class PaymentFeeSettingUpdate(BaseModel):
    service: Optional[str] = Field(
        default=None, min_length=1, max_length=30,
        description="決済サービス名",
    )
    fee_type: Optional[str] = Field(
        default=None, min_length=1, max_length=50,
        description="手数料種別",
    )
    rate_pct: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=8, decimal_places=4,
        description="料率（%）",
    )
    fixed_amount: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=14, decimal_places=2,
        description="固定手数料額",
    )
    threshold: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=14, decimal_places=2,
        description="閾値金額",
    )
    threshold_rule: Optional[str] = Field(
        default=None, max_length=10,
        description="閾値ルール（above/below）",
    )
    currency: Optional[str] = Field(
        default=None, min_length=3, max_length=3,
        description="通貨コード",
    )
    effective_from: Optional[date] = Field(
        default=None,
        description="適用開始日",
    )
    effective_to: Optional[date] = Field(
        default=None,
        description="適用終了日",
    )
    source_url: Optional[str] = Field(
        default=None,
        description="出典URL",
    )
    note: Optional[str] = Field(
        default=None,
        description="補足説明",
    )


class PaymentFeeSettingResponse(PaymentFeeSettingBase):
    id: int = Field(description="主キー")
    tenant_id: Optional[int] = Field(
        default=None,
        description="テナントID。NULLは共用デフォルト",
    )
    created_at: datetime = Field(description="作成日時")
    updated_at: datetime = Field(description="最終更新日時")

    model_config = ConfigDict(from_attributes=True)
