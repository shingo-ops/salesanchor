"""review_joins(fenced=...) の文字列検査（DB 不要）。docs/handoff/v102-sp2-perf/design.md P1・P2。"""
from __future__ import annotations

import re

from app.services.tcg_condition_review_svc import review_joins


def _c3(sql: str) -> str:
    """実験 perf/experiment.py の c1/c2/c3 と同じ変換（テスト内の独立実装）。"""
    sql = re.sub(r"\)\s*(cr_input|cr_hash|cr_valid|cr_reasons|cr)(?=\s*(?:CROSS|LEFT|JOIN|$))", r" OFFSET 0) \1", sql)
    sql = re.sub(r"to_jsonb\(ei\)->", "cr_ei.j->", sql)
    marker = "LEFT JOIN public.products cr_product"
    sql = sql.replace(marker, "CROSS JOIN LATERAL (SELECT to_jsonb(ei) AS j OFFSET 0) cr_ei\n    " + marker)
    for alias in ("cr_product", "cr_selected", "cr_ack_condition", "cr_empty", "cr_arc"):
        sql = re.sub(rf"to_jsonb\({alias}\)", f"cr_js.j_{alias}", sql)
    lines = sql.split("\n")
    i = [n for n, ln in enumerate(lines) if "public.conditions cr_arc" in ln][0]
    lines.insert(i + 1, (
        "    CROSS JOIN LATERAL (SELECT to_jsonb(cr_product) AS j_cr_product, to_jsonb(cr_selected) AS j_cr_selected, "
        "to_jsonb(cr_ack_condition) AS j_cr_ack_condition, to_jsonb(cr_empty) AS j_cr_empty, "
        "to_jsonb(cr_arc) AS j_cr_arc OFFSET 0) cr_js"))
    return "\n".join(lines)


def test_default_is_unfenced_and_unchanged():
    base = review_joins(schema="tcg")
    assert review_joins(schema="tcg", fenced=False) == base
    assert base.count("OFFSET 0") == 3  # コメント内1 + cr_data の1 + cr_shime の1
    assert "cr_ei" not in base and "cr_js" not in base
    assert "to_jsonb(ei)->" in base


def test_fenced_matches_experiment_c3():
    base = review_joins(schema="tcg")
    assert review_joins(schema="tcg", fenced=True) == _c3(base)


def test_fenced_structure():
    sql = review_joins(schema="tcg", fenced=True)
    assert sql.count("OFFSET 0") == 3 + 5 + 2  # 既存3 + 5本 + cr_ei + cr_js
    assert "to_jsonb(ei)->" not in sql
    assert sql.count("cr_js.j_") >= 5
    assert "cr_ei.j->" in sql
