from __future__ import annotations

"""
スタッフ（staff）スキーマ。Phase 1 再設計版。

テナントスキーマの staff / staff_emails / staff_ui_preferences に対応。
UI設定は読み取り時にネストで返す。
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import validate_email_loose, validate_phone


def _require_en_name(v: str | None) -> str:
    """英語名（名・姓）は必須。空白のみ・null は拒否し、前後の空白は除去する（ADR-159）。

    DB は NOT NULL にしない（既存データ保護）。入力検証でのみ必須化する。
    """
    stripped = (v or "").strip()
    if not stripped:
        raise ValueError("英語名は必須です")
    return stripped


class StaffStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    pending = "pending"


class StaffUIPreferences(BaseModel):
    """UI表示設定（本人の好み）"""
    dark_mode: bool = False
    show_chat_menu: bool = True
    show_sales_menu: bool = True
    show_settings_menu: bool = True
    show_admin_menu: bool = False
    show_sidebar: bool = True


class StaffEmailInput(BaseModel):
    """副メールアドレス（primary_email は staff 本体、これは追加分）"""
    email: str = Field(max_length=255)
    purpose: str | None = Field(default=None, max_length=50, description="main/notification/discord_link/secondary等")

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        checked = validate_email_loose(v)
        if not checked:
            raise ValueError("email は必須")
        return checked


class StaffCreate(BaseModel):
    staff_code: str | None = Field(default=None, max_length=20, description="EMP-00001 形式。空欄なら自動採番")
    surname_jp: str = Field(min_length=1, max_length=50)
    given_name_jp: str = Field(min_length=1, max_length=50)
    surname_kana: str | None = Field(default=None, max_length=100)
    given_name_kana: str | None = Field(default=None, max_length=100)
    surname_en: str = Field(min_length=1, max_length=100, description="英語名（姓）。必須（ADR-159）")
    given_name_en: str = Field(min_length=1, max_length=100, description="英語名（名）。必須・Discord 表示名（ADR-159）")
    primary_email: str = Field(max_length=255)
    discord_user_id: str | None = Field(default=None, max_length=50)
    role_id: int
    status: StaffStatus = StaffStatus.active
    firebase_uid: str | None = Field(default=None, max_length=128)
    user_id: int | None = None
    is_employee: bool = Field(
        default=False,
        description="社員/役員フラグ。True の場合は ADR-021 Phase 5 報酬計算で全ロール 0 円扱い。",
    )
    ui_preferences: StaffUIPreferences | None = None
    additional_emails: list[StaffEmailInput] = Field(default_factory=list, description="副メール（EMP-00005問題対応）")

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


class StaffUpdate(BaseModel):
    surname_jp: str | None = Field(default=None, min_length=1, max_length=50)
    given_name_jp: str | None = Field(default=None, min_length=1, max_length=50)
    surname_kana: str | None = Field(default=None, max_length=100)
    given_name_kana: str | None = Field(default=None, max_length=100)
    surname_en: str | None = Field(default=None, max_length=100)
    given_name_en: str | None = Field(default=None, max_length=100)
    primary_email: str | None = Field(default=None, max_length=255)
    discord_user_id: str | None = Field(default=None, max_length=50)
    role_id: int | None = None
    status: StaffStatus | None = None
    firebase_uid: str | None = Field(default=None, max_length=128)
    user_id: int | None = None
    is_employee: bool | None = Field(
        default=None,
        description="社員/役員フラグ。True の場合は ADR-021 Phase 5 報酬計算で全ロール 0 円扱い。",
    )
    ui_preferences: StaffUIPreferences | None = None
    # None=触らない、[]=全削除、[...]=置換
    additional_emails: list[StaffEmailInput] | None = None

    @field_validator("primary_email")
    @classmethod
    def _check_email(cls, v: str | None) -> str | None:
        return validate_email_loose(v)

    @field_validator("surname_en", "given_name_en")
    @classmethod
    def _check_en_name(cls, v: str | None) -> str:
        # 未指定（=触らない）はバリデータを通らない。指定された場合は空・null を拒否する
        return _require_en_name(v)


class StaffProfileUpdate(BaseModel):
    """本人専用プロフィール更新スキーマ（氏名・電話番号）。権限不要。英語名は指定する場合は必須（空不可）。"""
    surname_jp: str | None = Field(default=None, min_length=1, max_length=50)
    given_name_jp: str | None = Field(default=None, min_length=1, max_length=50)
    surname_kana: str | None = Field(default=None, max_length=100)
    given_name_kana: str | None = Field(default=None, max_length=100)
    surname_en: str | None = Field(default=None, max_length=100)
    given_name_en: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str | None) -> str | None:
        return validate_phone(v)

    @field_validator("surname_en", "given_name_en")
    @classmethod
    def _check_en_name(cls, v: str | None) -> str:
        return _require_en_name(v)


class StaffResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: int | None
    staff_code: str
    surname_jp: str
    given_name_jp: str
    surname_kana: str | None
    given_name_kana: str | None
    surname_en: str | None
    given_name_en: str | None
    primary_email: str
    discord_user_id: str | None
    role_id: int
    role_name: str | None = None
    status: str
    firebase_uid: str | None
    is_employee: bool = Field(
        default=False,
        description="社員/役員フラグ。True の場合は ADR-021 Phase 5 報酬計算で全ロール 0 円扱い。",
    )
    phone: str | None = None
    avatar_url: str | None = Field(
        default=None,
        description="担当者アイコンの公開 URL（絶対 URL）。未登録は null（ADR-159）。",
    )
    emails: list[str] = Field(default_factory=list)
    ui_preferences: StaffUIPreferences | None = None
    locale: str = "ja"
    theme: str = "light"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
