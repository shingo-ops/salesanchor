"""試作版 v102：型番で決めない中分類（type_master.match_by_code = FALSE）の変換の単体試験。

設計: docs/handoff/prototype-v102-product-first/design.md
原文は社外秘のため使わない。商品名・型番はすべて作り例。DB には触れない。
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services.extraction_judgement_svc import ProductEntry, match_product

NAME_ONLY_WORK = 1
OTHER_WORK = 2


def _entry(pid, work, code=None, mark=None, keywords=(), exclude=()):
    return ProductEntry(
        id=pid, product_code=code, mark=mark, work_id=work, search_keywords=tuple(keywords), exclude_keywords=tuple(exclude),
    )


def _entries():
    return (
        _entry(1, NAME_ONLY_WORK, code="SV-9A", mark="MA", keywords=("サンプル周年", "sv9a", "MA")),
        _entry(2, NAME_ONLY_WORK, code=None, mark=None, keywords=("サンプルカード151", "sv2a")),
        _entry(3, OTHER_WORK, code="OP-14", mark=None, keywords=("別作品の箱", "OP14", "sv2a")),
    )


def test_no_name_only_work_returns_identical_entries():
    entries = _entries()
    assert pf.apply_name_only_works(entries, frozenset()) == entries


def test_name_only_work_drops_code_mark_and_code_like_keywords():
    result = {e.id: e for e in pf.apply_name_only_works(_entries(), frozenset({NAME_ONLY_WORK}))}
    assert (result[1].product_code, result[1].mark) == (None, None)
    assert result[1].search_keywords == ("サンプル周年",)  # sv9a は自分の品番、MA は自分のマーク
    assert result[2].search_keywords == ("サンプルカード151", "sv2a")  # sv2a はどの商品の品番・マークとも一致しないので残る


def test_keyword_equal_to_other_works_code_is_dropped():
    entries = (
        _entry(1, NAME_ONLY_WORK, keywords=("サンプル周年", "op14")),  # op14 は別作品（3）の品番 OP-14 と正規化で一致
        _entry(3, OTHER_WORK, code="OP-14", keywords=("別作品の箱",)),
    )
    result = {e.id: e for e in pf.apply_name_only_works(entries, frozenset({NAME_ONLY_WORK}))}
    assert result[1].search_keywords == ("サンプル周年",)


def test_other_work_entries_are_unchanged():
    entries = _entries()
    result = {e.id: e for e in pf.apply_name_only_works(entries, frozenset({NAME_ONLY_WORK}))}
    assert result[3] == entries[2]


def test_input_entries_are_not_mutated():
    entries = _entries()
    before = tuple(entries)
    pf.apply_name_only_works(entries, frozenset({NAME_ONLY_WORK}))
    assert entries == before and entries[0].product_code == "SV-9A"


def test_name_only_work_is_not_matched_by_code_only_text_but_is_by_name():
    entries = pf.apply_name_only_works(_entries(), frozenset({NAME_ONLY_WORK}))
    code_only = match_product("★ MA PSA10 ランダム SV-9A sv9a", entries, strict_codes=True)
    assert code_only.status == "unmatched"
    by_name = match_product("サンプル周年 PSA10", entries, strict_codes=True)
    assert (by_name.status, by_name.product_id) == ("matched", 1)


def test_other_work_still_matched_by_code():
    entries = pf.apply_name_only_works(_entries(), frozenset({NAME_ONLY_WORK}))
    result = match_product("OP-14 未開封", entries, strict_codes=True)
    assert (result.status, result.product_id) == ("matched", 3)


def test_without_conversion_code_only_text_would_match():
    result = match_product("★ MA PSA10 ランダム SV-9A", _entries(), strict_codes=True)
    assert result.status == "matched" and result.product_id == 1


def test_loader_applies_name_only_works(monkeypatch):
    monkeypatch.setattr(pf, "load_product_entries", lambda s: list(_entries()))
    monkeypatch.setattr(pf, "load_product_kubun_type_map", lambda s: {"1": "箱系"})

    def execute(stmt):
        sql = str(stmt)
        if "code_only_match" in sql:
            rows = []
        elif "type_master" in sql:
            assert "match_by_code = FALSE" in sql
            rows = [(NAME_ONLY_WORK,)]
        elif "line_conditions" in sql:
            rows = [("Sealed box", "Box")]
        else:
            rows = []
        return SimpleNamespace(fetchall=lambda: rows)

    session = MagicMock()
    session.execute.side_effect = execute
    masters = pf.load_product_first_masters(session)
    first = next(e for e in masters.product_entries if e.id == 1)
    assert (first.product_code, first.mark) == (None, None)
