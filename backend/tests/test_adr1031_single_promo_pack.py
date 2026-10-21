"""ADR-1031：シングル系の状態5つ と プロモパック系（v102）。例文は作り文だけ。DB は使わない。"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services import gemini_raw_copy_v101 as v101
from app.services import line_analysis_v102_svc as svc
from app.services.extraction_judgement_svc import ProductEntry
from app.services.gemini_raw_copy_v102_product_first import ProductFirstMasters
from app.services.tcg_analyzer_svc import load_condition_entries, resolve_condition_v2


def _psa(n: str) -> str:
    return rf"(?i)[pｐＰ][sｓＳ][aａＡ][\s　\-－:：]?{n}(?![0-9０-９])"


def _row(code, canonical, group, rank, kubun, match_type="REGEX", search_kw="", priority=2, exclude_kw=""):
    return {
        "cond_id": f"{900 + int(code[-2:])}", "code": code, "canonical": canonical, "priority": priority,
        "app_kubun": kubun, "search_kw": search_kw, "exclude_kw": exclude_kw, "match_type": match_type,
        "effect": "OUTPUT", "value_group": group, "value_rank": rank,
    }


S, P = "シングル系", "プロモパック系"
_SINGLE = (
    _row("CN0015", "PSA10", "single", 1, S, search_kw=_psa("(10|１０)")),
    _row("CN0016", "PSA9", "single", 2, S, search_kw=_psa("(9|９)")),
    _row("CN0017", "PSA8", "single", 3, S, search_kw=_psa("(8|８)")),
    _row("CN0018", "PSA7以下", "single", 4, S, search_kw=_psa("[1-7１-７]")),
    _row("CN0019", "Single", "single", 5, S, match_type="KEYWORD", priority=10),
)
_PROMO = (
    _row("CN0020", "未開封", "promo_pack", 1, P, match_type="KEYWORD", priority=10),
    _row("CN0021", "開封済み", "promo_pack", 2, P, search_kw=r"(?<!未)開封(?!前|していない|なし|不可)"),
    _row("CN0022", "PSA10", "promo_pack", 3, P, search_kw=_psa("(10|１０)")),
)
_SCOPED = {"single": _SINGLE, "promo_pack": _PROMO}


def _cond(code, canonical, priority, app_kubun, search_kw):
    return {
        "cond_id": str(int(code[-4:])), "code": code, "canonical": canonical, "priority": priority, "app_kubun": app_kubun,
        "search_kw": search_kw, "exclude_kw": "", "match_type": "KEYWORD", "effect": "OUTPUT",
        "value_group": None, "value_rank": None,
    }


_COND = [
    _cond("CN0008", "FLAG_SINGLE", 1, "枚系,単位不明", "PSA,SR"),
    _cond("CN0004", "Damaged sealed box", 2, "箱系", "難あり"),
    _cond("CN0003", "Sealed box", 4, "箱系", "シュリンク付き"),
]
_STATUS = [
    {"canonical": "active", "search_pattern": "", "exclude_pattern": "", "priority": 99,
     "match_type": "DEFAULT", "effect": "OUTPUT"},
]
_PRODUCTS = (
    ProductEntry(id=1, product_code=None, mark=None, work_id=1, search_keywords=("作り箱",), exclude_keywords=()),
    ProductEntry(id=3, product_code=None, mark=None, work_id=1, search_keywords=("作りカード",), exclude_keywords=()),
    ProductEntry(id=5, product_code=None, mark=None, work_id=1, search_keywords=("作りパック",), exclude_keywords=()),
)
_KUBUN = {"1": "箱系", "3": S, "5": P}
_UNITS = {"Box": ("Box", "箱系"), "piece": ("Piece", "単品系")}


def _masters(scoped=_SCOPED):
    return ProductFirstMasters(
        product_entries=_PRODUCTS, product_kubun=_KUBUN, condition_unit={"Sealed box": "Box"}, ignore_phrases=(),
        scoped_cond_entries=scoped,
    )


def _one(text: str, scoped=_SCOPED):
    raw = f"{text}\n3@500円"
    parsed, errors = v101.parse_v101_response(
        json.dumps({"items": [{"lines": [1, 2], "price": "500円", "quantity": "3"}]}, ensure_ascii=False),
        raw, status_entries=_STATUS,
    )
    assert errors == []
    (row,), _f = v101.extract_v101_items(
        parsed, raw, order=None, reassign=True, v102_fixes=True, product_first=_masters(scoped),
        cond_entries=_COND, cond_canonical_to_uuid={}, unit_alias_to_info=_UNITS, status_entries=_STATUS,
    )
    return row


def _single(word: str):
    return _one(f"作りカード {word}".strip())


def _promo(word: str):
    return _one(f"作りパック {word}".strip())


# T1・T2
@pytest.mark.parametrize("word", ["PSA10", "psa10ar", "ＰＳＡ１０", "PSA 10", "PSA-10"])
def test_t1_single_psa10(word):
    assert _single(word)["condition"] == "PSA10"


@pytest.mark.parametrize("word,expected", [
    ("PSA9", "PSA9"), ("PSA8", "PSA8"), ("PSA7", "PSA7以下"), ("PSA1", "PSA7以下"),
])
def test_t2_single_other_grades(word, expected):
    assert _single(word)["condition"] == expected


def test_t2_psa100_is_not_a_graded_state():
    assert _single("PSA100")["condition"] == "Single"


def test_t2_psa100_does_not_hit_psa10_row():
    cond, _cid, _basis = resolve_condition_v2("PSA100", "", S, list(_SINGLE), {}, prefer_lowest_value=True)
    assert cond != "PSA10"


# T3
def test_t3_single_without_word_is_single_r7():
    row = _single("")
    assert (row["condition"], row["condition_basis"]) == ("Single", "R7:単品既定")
    assert not row["condition_basis"].startswith("R4")
    assert all(r["kind"] != "condition_unknown" for r in row["review"])


# T4
def test_t4_promo_pack_without_word_is_unopened_r8():
    row = _promo("")
    assert (row["condition"], row["condition_basis"]) == ("未開封", "R8:プロモパック既定")


# T5
def test_t5_promo_pack_opened_and_psa10():
    assert _promo("開封済み")["condition"] == "開封済み"
    assert _promo("PSA10")["condition"] == "PSA10"


# T6
@pytest.mark.parametrize("word", ["未開封", "開封前", "新品未開封", "開封していない", "開封なし"])
def test_t6_unopened_words_are_not_opened(word):
    assert _promo(word)["condition"] != "開封済み"


# T7
def test_t7_opened_and_psa10_is_review():
    row = _promo("開封済み PSA10")
    assert any(r["kind"] == pf.REVIEW_MULTIPLE_CANDIDATES for r in row["review"])
    assert _promo("開封済み")["review"] == [] or all(r["kind"] != pf.REVIEW_MULTIPLE_CANDIDATES for r in _promo("開封済み")["review"])


# 行が無い間は今と同じ（シングル系は Error）
def test_without_scoped_rows_single_stays_unchanged():
    with_rows = _single("")
    none = _one("作りカード", scoped={})
    assert with_rows["condition"] == "Single"
    assert none["condition"] in ("不明", "Error")


# T8
def _session(rows):
    info = MagicMock()
    info.first.return_value = (1,)
    main = MagicMock()
    main.fetchall.return_value = rows
    session = MagicMock()
    session.execute.side_effect = [info, main]
    return session


_DB_ROWS = [
    ("1", "CN0003", "Sealed box", 4, "箱系", "未開封", "", "KEYWORD", "OUTPUT", "box", 1),
    ("2", "CN0015", "PSA10", 2, "シングル系", "x", "", "REGEX", "OUTPUT", "single", 1),
    ("3", "CN0021", "開封済み", 2, "プロモパック系", "x", "", "REGEX", "OUTPUT", "promo_pack", 2),
]


def test_t8_default_call_hides_scoped_groups():
    assert [e["code"] for e in load_condition_entries(_session(_DB_ROWS))] == ["CN0003"]


def test_t8_opt_in_returns_scoped_groups():
    got = load_condition_entries(_session(_DB_ROWS), include_scoped_groups=True)
    assert [e["code"] for e in got] == ["CN0003", "CN0015", "CN0021"]


def test_t8_box_product_result_is_same_with_scoped_rows_in_masters():
    def box(scoped):
        return _one("作り箱 シュリンク付き", scoped)

    a, b = box({}), box(_SCOPED)
    assert (a["condition"], a["condition_basis"], a["unit"]) == (b["condition"], b["condition_basis"], b["unit"])


def test_other_kubun_hits_ignores_scoped_rows():
    entries = [*_COND, *_SINGLE, *_PROMO]
    assert pf._other_kubun_hits("PSA10 開封済み", "箱系", entries) == []


# C6：群の中で id を引く
def test_c6_condition_id_is_taken_inside_the_group():
    masters = {"cond_entries": _COND, "cond_canonical_to_uuid": {"PSA10": "1"}, "product_first": _masters()}
    assert svc._condition_columns("PSA10", masters, S) == ("PSA10", 915, True)
    assert svc._condition_columns("PSA10", masters, P) == ("PSA10", 922, True)
    assert svc._condition_columns("Single", masters, S) == ("Single", 919, True)
    assert svc._condition_columns("未開封", masters, P) == ("未開封", 920, True)


def test_c6_other_kubun_and_missing_rows_keep_old_path():
    masters = {"cond_entries": _COND, "cond_canonical_to_uuid": {"PSA10": "1", "FLAG_SINGLE": "8"}, "product_first": _masters({})}
    assert svc._condition_columns("PSA10", masters, "箱系") == ("PSA10", 1, True)
    assert svc._condition_columns("PSA10", masters, S) == ("PSA10", 1, True)
    assert svc._condition_columns("Single", masters, S)[0] == "FLAG_SINGLE"


def test_load_v102_masters_keeps_scoped_rows_out_of_cond_entries(monkeypatch):
    """v102 の cond_entries（v101 の _state_words も同じ一覧を読む）に群の行は入らず、別に持つ。"""
    from app.services import tcg_analyzer_svc as analyzer

    calls = {}

    def fake_load(session, include_scoped_groups=False):
        calls["flag"] = include_scoped_groups
        return [*_COND, *_SINGLE, *_PROMO]

    monkeypatch.setattr(analyzer, "load_condition_entries", fake_load)
    monkeypatch.setattr(analyzer, "load_status_master", lambda s: [])
    monkeypatch.setattr(analyzer, "load_lookup_maps", lambda s: (None, None, {}, None, {}, {}))
    monkeypatch.setattr(analyzer, "load_ship_master", lambda s: [])
    monkeypatch.setattr(analyzer, "load_ship_drop_master", lambda s: [])
    monkeypatch.setattr(svc, "load_product_first_masters", lambda s: _masters({}))
    masters, _units = svc.load_v102_masters(MagicMock())
    assert calls["flag"] is True
    assert [e["code"] for e in masters["cond_entries"]] == [e["code"] for e in _COND]
    assert [e["canonical"] for e in masters["product_first"].scoped_cond_entries["single"]] == [e["canonical"] for e in _SINGLE]
    assert len(masters["product_first"].scoped_cond_entries["promo_pack"]) == 3
    assert v101._state_words(masters["cond_entries"]) == v101._state_words(_COND)
