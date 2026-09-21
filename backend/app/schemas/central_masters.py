"""
中央 admin（マーケットプレイス Jarvis 運用 admin）マスタ用 Pydantic スキーマ。

spec.md v1.1 F2 (Sprint 2):
  - public.knowledge_rules
  - public.supplier_aliases
  - public.tcg_series_master
  - public.pokemon_dex, public.trainer_dex
  - public.suppliers (拡張)
  - public.supplier_discord_routing

すべて require_super_admin 経由で書込される public schema のマスタ。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# knowledge_rules
# ============================================================================

# パーサ実装 + DB CHECK 制約(knowledge_rules_pattern_type_check) と一致させる。
# regex / prefix / substring / exact のみが inventory_parser で実装されている。
# （旧値 suffix / contains は未実装かつ DB 制約違反になるため廃止。部分一致 = substring）
_VALID_PATTERN_TYPES = {"regex", "exact", "prefix", "substring"}


class KnowledgeRuleBase(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    pattern_type: str = Field(min_length=1, max_length=20)
    pattern: str = Field(min_length=1, max_length=500)
    normalized_to: str = Field(min_length=1, max_length=500)
    priority: int = Field(default=100, ge=0, le=10000)
    language: str = Field(default="ja", min_length=2, max_length=2)
    is_active: bool = True

    @field_validator("pattern_type")
    @classmethod
    def _validate_pattern_type(cls, v: str) -> str:
        if v not in _VALID_PATTERN_TYPES:
            raise ValueError(
                f"pattern_type must be one of {sorted(_VALID_PATTERN_TYPES)}"
            )
        return v


class KnowledgeRuleCreate(KnowledgeRuleBase):
    pass


class KnowledgeRuleUpdate(BaseModel):
    category: Optional[str] = Field(default=None, max_length=50)
    pattern_type: Optional[str] = Field(default=None, max_length=20)
    pattern: Optional[str] = Field(default=None, max_length=500)
    normalized_to: Optional[str] = Field(default=None, max_length=500)
    priority: Optional[int] = Field(default=None, ge=0, le=10000)
    language: Optional[str] = Field(default=None, max_length=2)
    is_active: Optional[bool] = None


class KnowledgeRuleResponse(KnowledgeRuleBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# supplier_aliases
# ============================================================================


class SupplierAliasBase(BaseModel):
    supplier_id: int
    alias_text: str = Field(min_length=1, max_length=500)
    language: str = Field(default="ja", min_length=2, max_length=2)
    product_id: Optional[int] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source: Optional[str] = Field(default=None, max_length=50)


class SupplierAliasCreate(SupplierAliasBase):
    pass


class SupplierAliasUpdate(BaseModel):
    supplier_id: Optional[int] = None
    alias_text: Optional[str] = Field(default=None, min_length=1, max_length=500)
    language: Optional[str] = Field(default=None, max_length=2)
    product_id: Optional[int] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source: Optional[str] = Field(default=None, max_length=50)


class SupplierAliasResponse(SupplierAliasBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# tcg_series_master
# ============================================================================

# ADR-083: TCG 種別は public.type_master で管理（固定リスト廃止）。
# tcg_type の値検証は DB 側（type_master）に委ねる。code は安定キーのため不変。


class TcgTypeBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name_ja: str = Field(min_length=1, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)
    sort_order: int = Field(default=100, ge=0)
    is_active: bool = True


class TcgTypeCreate(TcgTypeBase):
    # QA 2026-05-31: code はユーザー入力させず内部で自動採番する。
    # 未指定なら backend が 'tcgtype_<連番>' を生成する。
    code: Optional[str] = Field(default=None, max_length=50)


class TcgTypeUpdate(BaseModel):
    # code は不変（既存シリーズが参照するため）。名称・並び順・有効フラグ・大分類のみ更新可。
    name_ja: Optional[str] = Field(default=None, min_length=1, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)
    sort_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    kind_id: Optional[int] = None


class TcgTypeResponse(TcgTypeBase):
    id: int
    kind_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TcgSeriesBase(BaseModel):
    tcg_type: str = Field(min_length=1, max_length=50)
    series_code: str = Field(min_length=1, max_length=50)
    name_ja: str = Field(min_length=1, max_length=255)
    name_en: Optional[str] = Field(default=None, max_length=255)
    release_date: Optional[date] = None
    category: Optional[str] = Field(default=None, max_length=50)


class TcgSeriesCreate(TcgSeriesBase):
    pass


class TcgSeriesUpdate(BaseModel):
    tcg_type: Optional[str] = None
    series_code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name_ja: Optional[str] = Field(default=None, min_length=1, max_length=255)
    name_en: Optional[str] = Field(default=None, max_length=255)
    release_date: Optional[date] = None
    category: Optional[str] = Field(default=None, max_length=50)


class TcgSeriesResponse(TcgSeriesBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# pokemon_dex / trainer_dex
# ============================================================================


class DexEntryBase(BaseModel):
    dex_number: int = Field(ge=1)
    name_ja: str = Field(min_length=1, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)


class PokemonDexCreate(DexEntryBase):
    generation: Optional[int] = Field(default=None, ge=1, le=20)
    region: Optional[str] = Field(default=None, max_length=50)


class PokemonDexUpdate(BaseModel):
    dex_number: Optional[int] = Field(default=None, ge=1)
    name_ja: Optional[str] = Field(default=None, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)
    generation: Optional[int] = Field(default=None, ge=1, le=20)
    region: Optional[str] = Field(default=None, max_length=50)


class PokemonDexResponse(PokemonDexCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TrainerDexCreate(DexEntryBase):
    era: Optional[str] = Field(default=None, max_length=50)


class TrainerDexUpdate(BaseModel):
    dex_number: Optional[int] = Field(default=None, ge=1)
    name_ja: Optional[str] = Field(default=None, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)
    era: Optional[str] = Field(default=None, max_length=50)


class TrainerDexResponse(TrainerDexCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PokeAPI 取込 (ADR-084) — ポケモン図鑑のみ
# ============================================================================


class DexImportEntry(BaseModel):
    dex_number: int = Field(ge=1)
    name_ja: str = Field(min_length=1, max_length=100)
    name_en: Optional[str] = Field(default=None, max_length=100)
    generation: Optional[int] = Field(default=None, ge=1, le=20)


class DexImportPreviewResponse(BaseModel):
    source: str = "pokeapi"
    source_count: int  # PokeAPI 側の総数
    db_count: int  # 既存 pokemon_dex 件数
    added: list[DexImportEntry]  # DB に無い新規分
    added_count: int
    truncated: bool = False  # 新規が上限を超えて打ち切ったか


class DexImportApplyRequest(BaseModel):
    entries: list[DexImportEntry] = Field(default_factory=list)


class DexImportApplyResponse(BaseModel):
    inserted_count: int


# ============================================================================
# public.suppliers (拡張: supplier_type / default_language)
# ============================================================================

_VALID_SUPPLIER_TYPES = {"individual", "corporate"}
_VALID_DEFAULT_LANGUAGES = {"ja", "en", "ko", "zh"}


class CentralSupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    supplier_type: str = Field(default="corporate")
    default_language: str = Field(default="ja", min_length=2, max_length=2)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, max_length=5000)
    notes: Optional[str] = Field(default=None, max_length=5000)
    is_active: bool = True
    # ADR-093: LINE名 + 構造化住所
    line_name: Optional[str] = Field(default=None, max_length=255)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    prefecture: Optional[str] = Field(default=None, max_length=50)
    city: Optional[str] = Field(default=None, max_length=100)
    address1: Optional[str] = Field(default=None, max_length=255)
    address2: Optional[str] = Field(default=None, max_length=255)

    @field_validator("supplier_type")
    @classmethod
    def _validate_supplier_type(cls, v: str) -> str:
        if v not in _VALID_SUPPLIER_TYPES:
            raise ValueError(
                f"supplier_type must be one of {sorted(_VALID_SUPPLIER_TYPES)}"
            )
        return v

    @field_validator("default_language")
    @classmethod
    def _validate_default_language(cls, v: str) -> str:
        if v not in _VALID_DEFAULT_LANGUAGES:
            raise ValueError(
                f"default_language must be one of {sorted(_VALID_DEFAULT_LANGUAGES)}"
            )
        return v


class CentralSupplierCreate(CentralSupplierBase):
    pass


class CentralSupplierUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    supplier_type: Optional[str] = None
    default_language: Optional[str] = Field(default=None, max_length=2)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, max_length=5000)
    notes: Optional[str] = Field(default=None, max_length=5000)
    is_active: Optional[bool] = None
    # ADR-093: LINE名 + 構造化住所
    line_name: Optional[str] = Field(default=None, max_length=255)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    prefecture: Optional[str] = Field(default=None, max_length=50)
    city: Optional[str] = Field(default=None, max_length=100)
    address1: Optional[str] = Field(default=None, max_length=255)
    address2: Optional[str] = Field(default=None, max_length=255)


class CentralSupplierResponse(CentralSupplierBase):
    id: int
    supplier_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # 一覧表示用: 紐付け済み Discord チャンネル ID（list_suppliers のサブクエリで付与）
    discord_channel_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# supplier_discord_routing
# ============================================================================


class SupplierDiscordRoutingBase(BaseModel):
    supplier_id: int
    discord_guild_id: str = Field(min_length=1, max_length=64)
    discord_channel_id: str = Field(min_length=1, max_length=64)
    is_active: bool = True


class SupplierDiscordRoutingCreate(SupplierDiscordRoutingBase):
    pass


class SupplierDiscordRoutingUpdate(BaseModel):
    supplier_id: Optional[int] = None
    discord_guild_id: Optional[str] = Field(default=None, max_length=64)
    discord_channel_id: Optional[str] = Field(default=None, max_length=64)
    is_active: Optional[bool] = None


class SupplierDiscordRoutingResponse(SupplierDiscordRoutingBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# tenant_admin: inventory.visibility.* マトリクス UI
# ============================================================================


class RoleVisibilityPermission(BaseModel):
    """1 ロール × inventory.visibility.* 1 キーの割当状態。"""

    role_id: int
    role_name: str
    permission_key: str
    is_granted: bool


class RoleVisibilityMatrixResponse(BaseModel):
    """テナント admin の在庫表示権限マトリクス全体。"""

    visibility_keys: list[str]
    rows: list[RoleVisibilityPermission]


class RoleVisibilityAssign(BaseModel):
    """1 ロールに対する inventory.visibility.* キー集合の上書き。"""

    role_id: int
    visibility_keys: list[str]


# ============================================================================
# ADR-085: 仕入先別 Gemini プロンプト (public.supplier_prompts)
# ============================================================================


class SupplierPromptResponse(BaseModel):
    supplier_id: int
    prompt: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SupplierPromptUpdate(BaseModel):
    prompt: str = Field(default="", max_length=50000)
    is_active: bool = True


# ============================================================================
# conditions_master: 状態マスタ (public.conditions)
# ============================================================================


class CentralConditionBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    canonical: str = Field(min_length=1, max_length=100)
    app_kubun: Optional[str] = None
    is_active: bool = True
    priority: Optional[int] = None
    search_kw: str = ""
    exclude_kw: str = ""


class CentralConditionCreate(CentralConditionBase):
    pass


class CentralConditionUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    canonical: Optional[str] = Field(default=None, min_length=1, max_length=100)
    app_kubun: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    search_kw: Optional[str] = None
    exclude_kw: Optional[str] = None


class CentralConditionResponse(CentralConditionBase):
    id: int
    tenant_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# public.units / public.unit_aliases
# ============================================================================


class UnitBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    canonical: str = Field(min_length=1, max_length=100)
    kubun: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = True


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    canonical: Optional[str] = Field(default=None, min_length=1, max_length=100)
    kubun: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None


class UnitResponse(UnitBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnitAliasBase(BaseModel):
    unit_id: int
    alias_text: str = Field(min_length=1, max_length=500)
    lang: str = Field(default="ja", min_length=2, max_length=5)


class UnitAliasCreate(UnitAliasBase):
    pass


class UnitAliasResponse(UnitAliasBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# tcg_status_master
# ============================================================================

_VALID_MATCH_TYPES = {"REGEX", "LITERAL", "DEFAULT"}
_VALID_EFFECTS = {"OUTPUT", "EXCLUDE"}


class TcgStatusMasterBase(BaseModel):
    status_id: str = Field(min_length=1, max_length=50)
    canonical: str = Field(min_length=1, max_length=255)
    search_pattern: str = Field(default="", max_length=1000)
    exclude_pattern: str = Field(default="", max_length=1000)
    priority: int = Field(ge=0, le=10000)
    enabled: bool = True
    note: str = Field(default="", max_length=1000)
    match_type: str = Field(min_length=1, max_length=20)
    effect: str = Field(min_length=1, max_length=20)

    @field_validator("match_type")
    @classmethod
    def _validate_match_type(cls, v: str) -> str:
        if v not in _VALID_MATCH_TYPES:
            raise ValueError(f"match_type must be one of {sorted(_VALID_MATCH_TYPES)}")
        return v

    @field_validator("effect")
    @classmethod
    def _validate_effect(cls, v: str) -> str:
        if v not in _VALID_EFFECTS:
            raise ValueError(f"effect must be one of {sorted(_VALID_EFFECTS)}")
        return v


class TcgStatusMasterCreate(TcgStatusMasterBase):
    pass


class TcgStatusMasterUpdate(BaseModel):
    status_id: Optional[str] = Field(default=None, min_length=1, max_length=50)
    canonical: Optional[str] = Field(default=None, min_length=1, max_length=255)
    search_pattern: Optional[str] = Field(default=None, max_length=1000)
    exclude_pattern: Optional[str] = Field(default=None, max_length=1000)
    priority: Optional[int] = Field(default=None, ge=0, le=10000)
    enabled: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=1000)
    match_type: Optional[str] = Field(default=None, min_length=1, max_length=20)
    effect: Optional[str] = Field(default=None, min_length=1, max_length=20)


class TcgStatusMasterResponse(TcgStatusMasterBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# tcg_note_master
# ============================================================================


class TcgNoteMasterBase(BaseModel):
    label_ja: str
    label_en: str
    enabled: bool = True
    search_keywords: str = ""
    exclude_keywords: str = ""
    category: str = ""
    priority: int
    match_type: str = "LITERAL"
    search_pattern: Optional[str] = None
    label_template: Optional[str] = None

    @field_validator("match_type")
    @classmethod
    def validate_match_type(cls, v: str) -> str:
        if v not in ("LITERAL", "REGEX", "DEFAULT"):
            raise ValueError("match_type must be LITERAL, REGEX, or DEFAULT")
        return v


class TcgNoteMasterCreate(TcgNoteMasterBase):
    pass


class TcgNoteMasterUpdate(BaseModel):
    label_ja: Optional[str] = None
    label_en: Optional[str] = None
    enabled: Optional[bool] = None
    search_keywords: Optional[str] = None
    exclude_keywords: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    match_type: Optional[str] = None
    search_pattern: Optional[str] = None
    label_template: Optional[str] = None

    @field_validator("match_type")
    @classmethod
    def validate_match_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("LITERAL", "REGEX", "DEFAULT"):
            raise ValueError("match_type must be LITERAL, REGEX, or DEFAULT")
        return v


class TcgNoteMasterResponse(TcgNoteMasterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
