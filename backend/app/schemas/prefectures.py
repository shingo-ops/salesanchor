from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PrefectureResponse(BaseModel):
    code: str = Field(min_length=2, max_length=2)
    name_ja: str
    name_en: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)
