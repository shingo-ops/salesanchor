"""Shared read order for analysis results and distribution.

SQL aliases p/ar/ei/cr are fixed and supplied only by trusted service queries.
The state position comes from the condition master (public.conditions = view of
public.line_conditions): value_group / value_rank (ADR-1023). This module only
holds the group order and the Bulk special case. It changes no persisted data.
"""
from __future__ import annotations

# 群の順（カートン → ボックス → パック → プロモパック → シングル → ブックレット → サプライ）。群の中は状態マスタの value_rank（1=価値が高い）。
VALUE_GROUP_ORDER = ("case", "box", "pack", "promo_pack", "single", "booklet", "supply")
# 価値の順位が無い状態のうち、先頭に置くもの（ADR-1021）。残りは canonical の文字順。
UNRANKED_FIRST = "Bulk"
_GROUP_STRIDE = 1000
_UNRANKED_BASE = _GROUP_STRIDE * len(VALUE_GROUP_ORDER)


def result_order_sql() -> str:
    """Order whole result sets before pagination; unknown values stay visible."""
    group_case = " ".join(
        f"WHEN '{group}' THEN {index}" for index, group in enumerate(VALUE_GROUP_ORDER)
    )
    # 状態マスタ全体を 1 つの jsonb（canonical -> 位置）にまとめる。cr を参照しない副問い合わせなので
    # PostgreSQL が 1 回だけ評価し（InitPlan）、行ごとに public.conditions を引かない（行ごとに引くと
    # 4,097 行の一覧で処理時間が約 2 倍になった）。canonical が重複したら id が小さい方が勝つ
    # （jsonb_object_agg は後の値が勝つので ORDER BY lc.id DESC。本番は重複なし）。
    condition_rank = (
        "COALESCE(((SELECT jsonb_object_agg("
        f"lc.canonical, (CASE lc.value_group {group_case} END) * {_GROUP_STRIDE} + lc.value_rank "
        "ORDER BY lc.id DESC) "
        "FROM public.conditions lc "
        "WHERE lc.canonical IS NOT NULL AND lc.value_group IS NOT NULL AND lc.value_rank IS NOT NULL"
        ") ->> cr.canonical)::integer, "
        f"{_UNRANKED_BASE} + CASE WHEN cr.canonical = '{UNRANKED_FIRST}' THEN 0 ELSE 1 END)"
    )
    return (
        "p.release_date DESC NULLS LAST, "
        "p.id ASC NULLS LAST, "
        f"{condition_rank}, "
        'cr.canonical COLLATE "C" ASC NULLS LAST, '
        "ar.price_normalized ASC NULLS LAST, ei.id ASC"
    )
