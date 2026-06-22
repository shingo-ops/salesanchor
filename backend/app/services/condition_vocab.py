from __future__ import annotations

from typing import Any, Literal

UNIT_VALUES = ("piece", "pack", "box", "case", "set")

# 多軸の正典値
SEAL_VALUES = ("shrink", "no_shrink", "sealed", "opened")
SEARCH_COND_VALUES = ("unsearched", "searched")
# bulk は売り方/形態であり、grade 軸には入れない。
GRADE_VALUES = ("s", "a", "b", "c", "d", "normal", "graded", "junk")
DAMAGE_VALUES = (True, False)

# いまの 1 列 condition の正典値
CONDITION_VALUES = (
    "shrink",
    "no_shrink",
    "sealed",
    "damage",
    "unsearched",
    "searched",
    "graded",
    "grade_s",
    "grade_a",
    "grade_b",
    "grade_c",
    "grade_d",
    "junk",
    "bulk",
    "normal",
    "unknown",
)

ConditionValue = Literal[*CONDITION_VALUES]
UnitValue = Literal[*UNIT_VALUES]
SealValue = Literal[*SEAL_VALUES]
SearchCondValue = Literal[*SEARCH_COND_VALUES]
GradeValue = Literal[*GRADE_VALUES]

# 既存の表記ゆれ / レガシー値を current condition に寄せる。
LEGACY_CONDITION_TO_CURRENT: dict[str, str] = {
    "shrink_yes": "shrink",
    "shrink_no": "no_shrink",
    "damaged": "damage",
    "state_a_minus": "grade_a",
    "state_a": "grade_a",
    "state_b": "grade_b",
    "new": "unknown",
    "used": "unknown",
    "opened": "unknown",
}

# ver4.1 の実挙動 -> current condition
VER41_TO_CONDITION: dict[str, str | None] = {
    "Sealed box": "shrink",
    "No shrink box": "no_shrink",
    "Damaged sealed box": "damage",
    "Case": "sealed",
    "Unsearched pack": "unsearched",
    "FLAG_SINGLE": None,
}

# current condition -> 多軸の推定値
CONDITION_TO_AXES: dict[str, dict[str, Any]] = {
    "shrink": {"seal": "shrink", "damage": False},
    "no_shrink": {"seal": "no_shrink", "damage": False},
    "sealed": {"seal": "sealed", "damage": False},
    "damage": {"seal": "sealed", "damage": True},
    "unsearched": {"search_cond": "unsearched", "damage": False},
    "searched": {"search_cond": "searched", "damage": False},
    "graded": {"grade": "graded", "damage": False},
    "grade_s": {"grade": "s", "damage": False},
    "grade_a": {"grade": "a", "damage": False},
    "grade_b": {"grade": "b", "damage": False},
    "grade_c": {"grade": "c", "damage": False},
    "grade_d": {"grade": "d", "damage": False},
    "junk": {"grade": "junk", "damage": False},
    # bulk は集計対象外。grade には落とさず、空軸として扱う。
    "bulk": {},
    "normal": {"grade": "normal", "damage": False},
    "unknown": {},
}

# 梱包(unit) 由来の既定 search_cond。box / case は未サーチ扱いで自動補完する。
UNIT_DEFAULT_SEARCH_COND: dict[str, str] = {
    "box": "unsearched",
    "case": "unsearched",
}


def normalize_condition(value: str | None) -> str | None:
    """旧 condition 値を current condition 正典に寄せる。"""

    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return LEGACY_CONDITION_TO_CURRENT.get(normalized, normalized)


def condition_axes(value: str | None) -> dict[str, Any]:
    """current condition から推定できる多軸値を返す。

    bulk のような集計対象外の値は空 dict を返す。
    """

    normalized = normalize_condition(value)
    if normalized is None:
        return {}
    return dict(CONDITION_TO_AXES.get(normalized, {}))


def unit_default_search_cond(unit: str | None) -> str | None:
    """梱包(unit) 由来の既定 search_cond を返す。"""

    if unit is None:
        return None
    normalized = str(unit).strip().lower()
    if not normalized:
        return None
    return UNIT_DEFAULT_SEARCH_COND.get(normalized)


def condition_is_canonical(value: str | None) -> bool:
    normalized = normalize_condition(value)
    return normalized in CONDITION_VALUES if normalized is not None else False


def condition_vocab_as_text() -> str:
    return ", ".join(CONDITION_VALUES)


__all__ = [
    "CONDITION_VALUES",
    "CONDITION_TO_AXES",
    "ConditionValue",
    "DAMAGE_VALUES",
    "GRADE_VALUES",
    "LEGACY_CONDITION_TO_CURRENT",
    "SEARCH_COND_VALUES",
    "SealValue",
    "SEAL_VALUES",
    "SearchCondValue",
    "UnitValue",
    "UNIT_VALUES",
    "VER41_TO_CONDITION",
    "condition_axes",
    "condition_is_canonical",
    "condition_vocab_as_text",
    "normalize_condition",
    "unit_default_search_cond",
]
