"""試作版 v102：商品照合の形G2（名前の候補を先に作り、型番は絞り込みと「型番だけでも」の作品だけに使う）の単体試験。

設計: docs/handoff/prototype-v102-product-first/design.md
原文は社外秘のため使わない。商品名・型番はすべて作り例。DB には触れない。
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services.extraction_judgement_svc import ProductEntry

NAME_ONLY = 1  # 名前だけ（match_by_code = FALSE）
CODE_OK = 2  # 型番だけでも決めてよい（既定）
NARROW_ONLY = 3  # 型番は絞り込みだけ（code_only_match = FALSE）


def _e(pid, work, code=None, mark=None, keywords=(), exclude=()):
    return ProductEntry(
        id=pid, product_code=code, mark=mark, work_id=work, search_keywords=tuple(keywords), exclude_keywords=tuple(exclude),
    )


def _index(entries, name_only=(NAME_ONLY,), code_only_off=(NARROW_ONLY,)):
    return pf.build_g2_index(tuple(entries), frozenset(name_only), frozenset(code_only_off))


def _run(text, entries, **kw):
    index = _index(entries, **kw)
    return pf.match_product_g2(text, index)


def _ids(result):
    return (result.status, result.candidates)


# --- N >= 2：型番が当たった商品に絞る ---------------------------------------------------------


def test_two_name_candidates_are_narrowed_by_code_hit():
    entries = [
        _e(10, CODE_OK, code="OP-14", keywords=("サンプル箱",)),
        _e(11, CODE_OK, code="OP-15", keywords=("サンプル箱",)),
    ]
    result = _run("サンプル箱 OP-14 未開封", entries)
    assert _ids(result) == ("matched", (10,))


def test_two_name_candidates_stay_when_no_code_hit():
    entries = [
        _e(10, CODE_OK, code="OP-14", keywords=("サンプル箱",)),
        _e(11, CODE_OK, code="OP-15", keywords=("サンプル箱",)),
    ]
    result = _run("サンプル箱 未開封", entries)
    assert _ids(result) == ("ambiguous", (10, 11))


def test_narrowing_applies_to_narrow_only_work_too():
    entries = [
        _e(30, NARROW_ONLY, code="BT-1", keywords=("別の箱",)),
        _e(31, NARROW_ONLY, code="BT-2", keywords=("別の箱",)),
    ]
    result = _run("別の箱 BT-2", entries)
    assert _ids(result) == ("matched", (31,))


def test_code_word_keyword_counts_as_code_hit_for_narrowing():
    # 検索ワード op16 は別商品の品番 OP-16 と同じ語＝型番語。名前の候補の数え方には使わず、絞り込みの当たりに使う。
    entries = [
        _e(10, CODE_OK, code="OP-16", keywords=("サンプル箱", "op16")),
        _e(11, CODE_OK, code="OP-17", keywords=("サンプル箱",)),
    ]
    result = _run("サンプル箱 OP16", entries)
    assert _ids(result) == ("matched", (10,))


# --- N == 1 ----------------------------------------------------------------------------------


def test_single_name_candidate_is_matched_without_code():
    entries = [_e(10, CODE_OK, code="OP-14", keywords=("サンプル箱",)), _e(11, CODE_OK, code="OP-15", keywords=("別名",))]
    assert _ids(_run("サンプル箱", entries)) == ("matched", (10,))


# --- N == 0：型番だけでも決めてよい作品だけ -----------------------------------------------------


def test_code_only_text_matches_when_work_allows_code_only():
    entries = [_e(10, CODE_OK, code="OP-14", keywords=("サンプル箱",))]
    assert _ids(_run("OP-14 未開封", entries)) == ("matched", (10,))


def test_code_only_text_has_no_candidate_for_narrow_only_work():
    entries = [_e(30, NARROW_ONLY, code="BT-1", keywords=("別の箱",))]
    assert _ids(_run("BT-1 未開封", entries)) == ("unmatched", ())


def test_code_only_text_has_no_candidate_for_name_only_work():
    entries = [_e(1, NAME_ONLY, code="SV-9A", mark="MA", keywords=("サンプル周年", "sv9a"))]
    assert _ids(_run("MA SV-9A PSA10", entries)) == ("unmatched", ())


def test_two_code_only_candidates_are_ambiguous():
    entries = [_e(10, CODE_OK, code="OP-14"), _e(11, CODE_OK, mark="OP-14")]
    assert _ids(_run("OP-14", entries)) == ("ambiguous", (10, 11))


# --- ポケモン（名前だけ）は型番で残らない -------------------------------------------------------


def test_name_only_work_candidate_is_dropped_when_other_candidate_has_code_hit():
    entries = [
        _e(1, NAME_ONLY, code="SV-9A", keywords=("共通名",)),
        _e(10, CODE_OK, code="OP-14", keywords=("共通名",)),
    ]
    result = _run("共通名 OP-14", entries)
    assert _ids(result) == ("matched", (10,))


def test_name_only_work_code_hit_is_not_used_for_narrowing():
    entries = [
        _e(1, NAME_ONLY, code="SV-9A", keywords=("共通名",)),
        _e(2, NAME_ONLY, code="SV-2A", keywords=("共通名",)),
    ]
    result = _run("共通名 SV-9A", entries)
    assert _ids(result) == ("ambiguous", (1, 2))


def test_name_only_work_matches_by_name_alone():
    entries = [_e(1, NAME_ONLY, code="SV-9A", keywords=("サンプル周年", "sv9a"))]
    assert _ids(_run("サンプル周年 PSA10", entries)) == ("matched", (1,))


# --- 除外ワード ------------------------------------------------------------------------------


def test_excluded_name_candidate_is_removed():
    entries = [
        _e(10, CODE_OK, code="OP-14", keywords=("サンプル箱",), exclude=("カートン",)),
        _e(11, CODE_OK, code="OP-15", keywords=("サンプル箱",)),
    ]
    assert _ids(_run("サンプル箱 カートン", entries)) == ("matched", (11,))


def test_excluded_code_only_candidate_is_removed():
    entries = [_e(10, CODE_OK, code="OP-14", exclude=("カートン",))]
    assert _ids(_run("OP-14 カートン", entries)) == ("unmatched", ())


# --- 結果の形（後段が読む欄） ------------------------------------------------------------------


def test_result_keeps_fields_read_by_later_steps():
    entries = [
        _e(10, CODE_OK, code="OP-14", keywords=("サンプル箱",)),
        _e(11, CODE_OK, code="OP-15", keywords=("サンプル箱",)),
    ]
    result = _run("サンプル箱 OP-14", entries)
    assert result.product_id == 10 and result.work_id == CODE_OK
    assert result.basis == "RAWCODE"
    assert 10 in result.code_hits and result.code_hit_values[10] == ("OP-14",)
    assert result.matched_keywords[10] == ("サンプル箱",)
    name_only = _run("サンプル箱", [entries[0]])
    assert name_only.basis == "SK:サンプル箱"


def test_without_marks_behaves_like_code_only_allowed_for_all_works():
    entries = [_e(1, None, code="OP-14")]
    index = pf.build_g2_index(tuple(entries), frozenset(), frozenset())
    assert _ids(pf.match_product_g2("OP-14", index)) == ("matched", (1,))


# --- 読み込み（DB は差し替え） -----------------------------------------------------------------


def test_loader_reads_code_only_off_marks(monkeypatch):
    entries = [
        _e(1, NAME_ONLY, code="SV-9A", keywords=("サンプル周年",)),
        _e(30, NARROW_ONLY, code="BT-1", keywords=("別の箱",)),
    ]
    monkeypatch.setattr(pf, "load_product_entries", lambda s: list(entries))
    monkeypatch.setattr(pf, "load_product_kubun_type_map", lambda s: {"1": "箱系"})
    queries = []

    def execute(stmt):
        sql = str(stmt)
        queries.append(sql)
        if "code_only_match = FALSE" in sql:
            rows = [(NARROW_ONLY,)]
        elif "match_by_code = FALSE" in sql:
            rows = [(NAME_ONLY,)]
        elif "line_conditions" in sql:
            rows = [("Sealed box", "Box")]
        else:
            rows = []
        return SimpleNamespace(fetchall=lambda: rows)

    session = MagicMock()
    session.execute.side_effect = execute
    masters = pf.load_product_first_masters(session)
    assert any("match_by_code = TRUE" in q and "code_only_match = FALSE" in q for q in queries)
    assert masters.g2_index.name_only_work_ids == frozenset({NAME_ONLY})
    assert masters.g2_index.code_only_off_work_ids == frozenset({NARROW_ONLY})
    # 既存の欄は変わらない（名前だけの商品の型番は product_entries から外れる）
    first = next(e for e in masters.product_entries if e.id == 1)
    assert (first.product_code, first.mark) == (None, None)
    # 型番を外す前の商品を g2_index が持つ
    assert next(e for e in masters.g2_index.entries if e.id == 1).product_code == "SV-9A"
