"""Shared read order for analysis results and distribution.

SQL aliases p/ar/ei/cr are fixed and supplied only by trusted service queries.
This changes no persisted data or condition-master priorities.
"""
from __future__ import annotations

RESULT_CONDITION_ORDER = (
    "Case",
    "Damaged case",
    "Sealed box",
    "Damaged sealed box",
    "No shrink box",
    "Opened box",
    "Unsearched pack",
    "Searched pack",
)


def result_order_sql() -> str:
    """Order whole result sets before pagination; unknown values stay visible."""
    condition_rank = "CASE cr.canonical " + " ".join(
        f"WHEN '{condition}' THEN {rank}"
        for rank, condition in enumerate(RESULT_CONDITION_ORDER)
    ) + f" ELSE {len(RESULT_CONDITION_ORDER)} END"
    return (
        "p.release_date DESC NULLS LAST, "
        "p.id ASC NULLS LAST, "
        f"{condition_rank}, "
        'cr.canonical COLLATE "C" ASC NULLS LAST, '
        "ar.price_normalized ASC NULLS LAST, ei.id ASC"
    )
