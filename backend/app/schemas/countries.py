from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CountryResponse(BaseModel):
    code: str = Field(min_length=2, max_length=2)
    name: str = Field(min_length=1, max_length=255)
    dial_code: str = Field(min_length=1, max_length=10)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)
