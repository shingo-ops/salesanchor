from __future__ import annotations

"""
顧客登録トークン用 Pydantic スキーマ（ADR-SA-03）。

担当者がリードに登録リンクを発行するリクエスト・レスポンスと、
顧客が公開フォームから送信する登録データのスキーマを定義する。
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.base import validate_email_loose, validate_phone

# AddressInput の Optional[str] フィールド一覧（空文字列 → None 正規化対象）
_ADDRESS_OPTIONAL_STR_FIELDS = frozenset({
    "branch_name", "name", "email", "telephone", "tax_id",
    "address_line_1", "address_line_2", "address_line_3",
    "city", "state", "zip", "country_code",
})


class TokenType(str, Enum):
    register = "register"
    add_address = "add_address"


# --- 担当者がトークン発行する際のスキーマ ---


class CreateTokenRequest(BaseModel):
    """担当者がリード向けに登録リンクを発行するリクエスト。"""
    lead_id: int = Field(..., description="リード ID")
    type: TokenType = Field(default=TokenType.register, description="トークン種別")


class CreateTokenResponse(BaseModel):
    """トークン発行レスポンス。registration_url を顧客に送付する。"""
    token: str = Field(..., description="raw token（URL に含める）")
    registration_url: str = Field(..., description="顧客に送付する登録 URL")
    expires_at: datetime = Field(..., description="有効期限")


# --- 公開エンドポイント: トークン検証レスポンス ---


class TokenVerifyResponse(BaseModel):
    """トークン検証結果。フォーム表示用のデータを返す。"""
    valid: bool
    company_name: Optional[str] = None
    lead_id: Optional[int] = None
    token_type: Optional[str] = None


# --- 公開エンドポイント: 顧客が登録データを送信するスキーマ ---


class AddressInput(BaseModel):
    """住所入力（billing / delivery 共通）。"""
    # DRIFT-C: 値制約を Literal で明示（DBの CHECK 制約に当てて 500 にしない）
    address_type: Literal["billing", "delivery"] = Field(..., description="billing or delivery")
    branch_name: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    telephone: Optional[str] = Field(None, max_length=30)
    tax_id: Optional[str] = Field(None, max_length=50)
    address_line_1: Optional[str] = Field(None, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    address_line_3: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    zip: Optional[str] = Field(None, max_length=20)
    # DRIFT-E: DB は CHAR(2)。3文字以上でDB例外になるため max_length=2 に制約
    country_code: Optional[str] = Field(None, max_length=2)
    is_default: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_empty_strings(cls, values: object) -> object:
        """全 Optional[str] フィールドの空文字列を None に正規化する（入力契約: 空欄 → null）。"""
        if isinstance(values, dict):
            for field in _ADDRESS_OPTIONAL_STR_FIELDS:
                if values.get(field) == "":
                    values[field] = None
        return values

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        return validate_email_loose(v)

    @field_validator("telephone")
    @classmethod
    def validate_tel(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        return validate_phone(v)

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        """ISO 3166-1 alpha-2: 2文字英大文字に正規化。空欄は None、3文字以上は 422。"""
        if not v:
            return None
        upper = v.strip().upper()
        if len(upper) != 2 or not upper.isalpha():
            raise ValueError("country_code は2文字のアルファベット（例: JP, US）で指定してください")
        return upper


class RegisterRequest(BaseModel):
    """顧客登録リクエスト（公開フォームから送信）。"""
    token: str = Field(..., description="raw token")
    addresses: list[AddressInput] = Field(default_factory=list, description="住所リスト")
    contact_name: Optional[str] = Field(None, max_length=200, description="担当者名")
    contact_email: Optional[str] = Field(None, max_length=255, description="担当者メール")
    contact_telephone: Optional[str] = Field(None, max_length=30, description="担当者電話")

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        return validate_email_loose(v)

    @field_validator("contact_telephone")
    @classmethod
    def validate_tel(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        return validate_phone(v)

    @model_validator(mode="after")
    def validate_contact_required(self) -> "RegisterRequest":
        """初回登録は担当者名 + (メール or 電話) が必須（スコープ: /public/register のみ）。"""
        if not self.contact_name or not self.contact_name.strip():
            raise ValueError("担当者名は必須です")
        if not self.contact_email and not self.contact_telephone:
            raise ValueError("担当者のメールアドレスまたは電話番号を入力してください")
        return self


class AddAddressRequest(BaseModel):
    """住所追加リクエスト（公開フォームから送信）。既存の住所を上書きしない。"""
    token: str = Field(..., description="raw token")
    address: AddressInput = Field(..., description="追加する住所")


class RegisterResponse(BaseModel):
    """登録完了レスポンス。"""
    success: bool
    message: str
