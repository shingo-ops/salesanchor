from __future__ import annotations

"""
スタッフ自己登録（招待リンク）のスキーマ（ADR-1068・設計 §3-3）。

申込の入力は StaffCreate から 役割・状態・user_id・discord_user_id・is_employee・
ui_preferences・additional_emails を除いたもの（姓名・かな・英語名・主メール）。
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import validate_email_loose
from app.schemas.staff import _require_en_name


class StaffJoinInviteCreate(BaseModel):
    role_id: int


class StaffJoinInviteCreated(BaseModel):
    """作成・作り直しの返事。URL はこの1回だけ返す。"""
    id: int
    url: str
    expires_at: datetime


class StaffJoinInviteItem(BaseModel):
    id: int
    status: str
    role_id: int
    role_name: str | None = None
    expires_at: datetime
    created_at: datetime | None = None
    created_by: int
    created_by_name: str | None = None


class StaffJoinInfo(BaseModel):
    """ログイン不要の GET の返事。"""
    tenant_name: str
    role_name: str | None = None
    expires_at: datetime


class StaffJoinSubmit(BaseModel):
    surname_jp: str = Field(min_length=1, max_length=50)
    given_name_jp: str = Field(min_length=1, max_length=50)
    surname_kana: str | None = Field(default=None, max_length=100)
    given_name_kana: str | None = Field(default=None, max_length=100)
    surname_en: str = Field(min_length=1, max_length=100, description="英語名（姓）。必須（ADR-159）")
    given_name_en: str = Field(min_length=1, max_length=100, description="英語名（名）。必須（ADR-159）")
    primary_email: str = Field(max_length=255)

    @field_validator("primary_email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        checked = validate_email_loose(v)
        if not checked:
            raise ValueError("primary_email は必須")
        return checked

    @field_validator("surname_en", "given_name_en")
    @classmethod
    def _check_en_name(cls, v: str) -> str:
        return _require_en_name(v)


class StaffJoinSubmitted(BaseModel):
    """申込の返事。登録番号はこの1回だけ見せる。"""
    registration_code: str
    discord_invite_url: str | None = None
