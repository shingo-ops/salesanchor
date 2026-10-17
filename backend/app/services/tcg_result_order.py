"""Shared read order for analysis results and distribution.

SQL aliases p/ar/ei/cr are fixed and supplied only by trusted service queries.
The state position comes from the condition master (public.conditions = view of
public.line_conditions): value_group / value_rank (ADR-1023). This module only
holds the group order and the Bulk special case. It changes no persisted data.
"""
from __future__ import annotations

# 群の順（カートン → ボックス → パック）。群の中は状態マスタの value_rank（1=価値が高い）。
VALUE_GROUP_ORDER = ("case", "box", "pack")
# 価値の順位が無い状態のうち、先頭に置くもの（ADR-1021）。残りは canonical の文字順。
UNRANKED_FIRST = "Bulk"
_GROUP_STRIDE = 1000
_UNRANKED_BASE = _GROUP_STRIDE * len(VALUE_GROUP_ORDER)


def result_order_sql() -> str:
    """Order whole result sets before pagination; unknown values stay visible."""
    group_case = " ".join(
        f"WHEN '{group}' THEN {index}" for index, group in enumerate(VALUE_GROUP_ORDER)
    )
    # canonical が重複しても行が増えないよう ORDER BY lc.id LIMIT 1（本番は重複なし）。
    condition_rank = (
        "COALESCE(("
        f"SELECT (CASE lc.value_group {group_case} END) * {_GROUP_STRIDE} + lc.value_rank "
        "FROM public.conditions lc "
        "WHERE lc.canonical = cr.canonical AND lc.value_group IS NOT NULL AND lc.value_rank IS NOT NULL "
        "ORDER BY lc.id LIMIT 1"
        f"), {_UNRANKED_BASE} + CASE WHEN cr.canonical = '{UNRANKED_FIRST}' THEN 0 ELSE 1 END)"
    )
    return (
        "p.release_date DESC NULLS LAST, "
        "p.id ASC NULLS LAST, "
        f"{condition_rank}, "
        'cr.canonical COLLATE "C" ASC NULLS LAST, '
        "ar.price_normalized ASC NULLS LAST, ei.id ASC"
    )
