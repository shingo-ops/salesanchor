"""除外ワードの一致が、状態の合図の語（public.conditions）に収まるときだけ無視する規則の単体試験。

設計: docs/handoff/excl-cond-contain/design.md
原文は社外秘のため使わない。商品名・本文はすべて作り例。DB には触れない。
"""
from __future__ import annotations

import pytest

import app.services.gemini_raw_copy_v102_product_first as pf
from app.services.extraction_judgement_svc import (
    ProductEntry,
    _excluded_keywords,
    build_cond_terms,
    fold_for_match,
    match_product,
    normalize_for_match,
)


def _product(exclude, keywords=("アビスアイ",)):
    return ProductEntry(
        id=1, product_code=None, mark=None, work_id=1, search_keywords=tuple(keywords), exclude_keywords=tuple(exclude),
    )


def _excl(text, exclude, cue_words=(), strict=True):
    cond_terms = build_cond_terms([{"match_type": "KEYWORD", "search_kw": ",".join(cue_words)}]) if cue_words else ()
    return _excluded_keywords(
        _product(exclude), normalize_for_match(text), fold_for_match(text), strict, cond_terms
    )


@pytest.mark.parametrize("strict", [True, False])
class TestContain:
    def test_ar_inside_arpack_is_ignored(self, strict):
        assert _excl("アビスアイ ARパック", ["AR"], ["ARパック"], strict) == ()

    def test_fullwidth_spaced_arpack_is_ignored(self, strict):
        assert _excl("アビスアイ ＡＲ　パック", ["AR"], ["ARパック"], strict) == ()

    def test_standalone_ar_still_excluded(self, strict):
        assert _excl("アビスアイ AR 1枚", ["AR"], ["ARパック"], strict) == ("AR",)

    def test_sar_not_contained_by_arpack(self, strict):
        assert _excl("アビスアイ SARパック", ["SAR"], ["ARパック"], strict) == ("SAR",)

    def test_shorter_cue_does_not_ignore(self, strict):
        assert _excl("アビスアイ PSA10", ["PSA10"], ["psa"], strict) == ("PSA10",)

    def test_same_length_cue_does_not_ignore(self, strict):
        assert _excl("アビスアイ CHR", ["CHR"], ["CHR"], strict) == ("CHR",)

    def test_longer_exclude_than_cue_is_kept(self, strict):
        assert _excl("アビスアイ FUTURISTIC", ["FUTURISTIC"], ["ur"], strict) == ("FUTURISTIC",)

    def test_both_arpack_and_standalone_ar_in_one_line(self, strict):
        assert _excl("アビスアイ ARパック AR", ["AR"], ["ARパック"], strict) == ("AR",)

    def test_empty_cond_terms_is_unchanged(self, strict):
        assert _excl("アビスアイ ARパック", ["AR"], (), strict) == ("AR",)


def test_empty_cond_terms_matches_legacy_call_signature():
    text = "アビスアイ ARパック SAR"
    product = _product(["AR", "SAR", "PSA10"])
    nb, folded = normalize_for_match(text), fold_for_match(text)
    legacy = _excluded_keywords(product, nb, folded, True)
    assert _excluded_keywords(product, nb, folded, True, ()) == legacy == ("AR", "SAR")


def test_cond_terms_without_folded_masks_nb_only():
    product = _product(["AR"])
    nb = normalize_for_match("アビスアイ ARパック")
    assert _excluded_keywords(product, nb, None, False, build_cond_terms([{"search_kw": "ARパック"}])) == ()


def test_build_cond_terms_filters_type_normalizes_and_orders():
    terms = build_cond_terms([
        {"match_type": "KEYWORD", "search_kw": "ＡＲパック, psa ,"},
        {"match_type": "LITERAL", "search_kw": "AR確定パック"},
        {"match_type": "REGEX", "search_kw": "^ar.*$"},
        {"match_type": "DEFAULT", "search_kw": "x"},
        {"search_kw": "psa"},
    ])
    assert terms == ("ar確定ぱっく", "arぱっく", "psa")


def test_match_product_passes_cond_terms():
    terms = build_cond_terms([{"search_kw": "ARパック"}])
    block = "アビスアイ ARパック"
    assert match_product(block, [_product(["AR"])], strict_codes=True).status == "unmatched"
    assert match_product(block, [_product(["AR"])], strict_codes=True, cond_terms=terms).status == "matched"


def test_g2_uses_index_cond_terms():
    entries = (_product(["AR"]),)
    index = pf.build_g2_index(entries, frozenset(), frozenset())
    assert pf.match_product_g2("アビスアイ ARパック", index).status == "unmatched"
    with_terms = pf.dataclass_replace(index, cond_terms=build_cond_terms([{"search_kw": "ARパック"}]))
    assert pf.match_product_g2("アビスアイ ARパック", with_terms).status == "matched"
    assert pf.match_product_g2("アビスアイ AR 1枚", with_terms).status == "unmatched"


def test_with_cond_terms_returns_copy_and_empty_is_identity():
    masters = pf.ProductFirstMasters(product_entries=(_product(["AR"]),), product_kubun={}, condition_unit={}, ignore_phrases=())
    assert pf.with_cond_terms(masters, ()) is masters
    updated = pf.with_cond_terms(masters, ("arぱっく",))
    assert updated.g2_index.cond_terms == ("arぱっく",)
    assert masters.g2_index is None
    assert pf.match_text_g2("アビスアイ ARパック", updated).status == "matched"
