"""TenantProfile Pydantic schemas (Sprint 8 / F8)

印鑑画像 URL と既定の言語を管理する。会社名・住所・電話・メール・サイトは
issuer_profiles へ移した (ADR-1061 便2-2c2b)。古い欄が送られてきても無視する。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_VALID_LANGUAGES = {"ja", "en", "ko", "zh"}


class TenantProfileResponse(BaseModel):
    id: int
    seal_image_url: str | None = None
    default_language: str = "ja"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantProfileUpdate(BaseModel):
    seal_image_url: str | None = Field(default=None, max_length=5000)
    default_language: str | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("default_language")
    @classmethod
    def _validate_language(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in _VALID_LANGUAGES:
            raise ValueError(
                f"default_language must be one of {sorted(_VALID_LANGUAGES)}"
            )
        return v
