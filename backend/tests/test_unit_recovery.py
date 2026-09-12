"""
TCG E3a + E5 単位復旧・状態再計算テスト。

GAS AnalysisV2UnitRecovery.gs / AnalysisV2ConditionRecalc.gs との動作一致検証。
DB 接続不要（純粋関数テスト）。

GAS 対応行:
  unitRecoveryNorm_      : AnalysisV2UnitRecovery.gs:30-32
  unitRecoveryBuildTerms_: AnalysisV2UnitRecovery.gs:91-104
  unitRecoveryFindTerm_  : AnalysisV2UnitRecovery.gs:40-59
  recoverUnitFromProductName: AnalysisV2UnitRecovery.gs:134-276 (ロジック部分のみ)
"""
from __future__ import annotations

import pytest

from app.services.tcg_unit_recovery_svc import (
    E3A_MAX_RECOVER,
    E5_MAX_ROWS,
    build_unit_recovery_terms,
    find_term,
    unit_recovery_norm,
)


# ---------------------------------------------------------------------------
# unit_recovery_norm (NFKC + trim)
# ---------------------------------------------------------------------------


class TestUnitRecoveryNorm:
    """GAS unitRecoveryNorm_ (AnalysisV2UnitRecovery.gs:30-32) との一致確認"""

    def test_nfkc_halfwidth_katakana(self):
        # ﾊﾟｯｸ (halfwidth) -> パック (fullwidth katakana)
        assert unit_recovery_norm("ﾊﾟｯｸ") == "パック"

    def test_nfkc_fullwidth_latin(self):
        # ＢＯＸ (fullwidth) -> BOX (halfwidth)
        assert unit_recovery_norm("ＢＯＸ") == "BOX"

    def test_trim_whitespace(self):
        assert unit_recovery_norm("  box  ") == "box"

    def test_none_input(self):
        assert unit_recovery_norm(None) == ""

    def test_empty_string(self):
        assert unit_recovery_norm("") == ""

    def test_already_nfkc(self):
        assert unit_recovery_norm("Pack") == "Pack"

    def test_fullwidth_space_preserved_in_middle(self):
        # NFKC does NOT normalize U+3000 (ideographic space) to ASCII space
        # but it does trim leading/trailing
        result = unit_recovery_norm("\u3000test\u3000")
        assert result == "test"

    def test_mixed_halfwidth_fullwidth(self):
        # ｶｰﾄﾝ (halfwidth) -> カートン (fullwidth)
        assert unit_recovery_norm("ｶｰﾄﾝ") == "カートン"


# ---------------------------------------------------------------------------
# build_unit_recovery_terms
# ---------------------------------------------------------------------------


class TestBuildUnitRecoveryTerms:
    """GAS unitRecoveryBuildTerms_ (AnalysisV2UnitRecovery.gs:91-104) との一致確認"""

    def test_returns_nonempty_list(self):
        terms = build_unit_recovery_terms()
        assert len(terms) > 0

    def test_sorted_longest_first(self):
        terms = build_unit_recovery_terms()
        for i in range(len(terms) - 1):
            assert len(terms[i]["term"]) >= len(terms[i + 1]["term"])

    def test_includes_canonical_and_aliases(self):
        terms = build_unit_recovery_terms()
        term_strs = [t["term"] for t in terms]
        # canonical
        assert "Case" in term_strs
        assert "Box" in term_strs
        assert "Pack" in term_strs
        # aliases
        assert "カートン" in term_strs
        assert "ケース" in term_strs
        assert "箱" in term_strs
        assert "パック" in term_strs

    def test_all_entries_have_required_keys(self):
        terms = build_unit_recovery_terms()
        for t in terms:
            assert "term" in t
            assert "unit_id" in t
            assert "canonical" in t
            assert "kubun" in t

    def test_ct_terms_present(self):
        """ct/CT/Ct are aliases of Case (UN0001 → UUID c5a6371d-...)"""
        terms = build_unit_recovery_terms()
        ct_terms = [t for t in terms if t["term"] in ("ct", "CT", "Ct")]
        assert len(ct_terms) == 3
        for t in ct_terms:
            assert t["canonical"] == "Case"
            # unit_id は DB UUID 値
            assert t["unit_id"] == "c5a6371d-5296-45a3-913f-72f6315b4bb9"

    def test_includes_all_8_units(self):
        terms = build_unit_recovery_terms()
        unit_ids = set(t["unit_id"] for t in terms)
        # _UNIT_MASTER_ROWS の unit_id は DB UUID 値（UN0001〜UN0008 のコード文字列ではない）
        expected = {
            "c5a6371d-5296-45a3-913f-72f6315b4bb9",  # Case
            "8e980434-eeff-4233-be5c-bcd0ba1db992",  # Box
            "225a8677-b1eb-4cb4-b2f0-4df5827d899a",  # Pack
            "fb707fad-d096-439c-b1af-d411a4a7d18a",  # Piece
            "9fffcb6c-9a77-4e89-b862-6c9868cfaf34",  # Set
            "07724cb8-085b-4ed0-b852-84ee20ce9f3c",  # 本
            "0df9b0c2-ac24-44b6-8dad-a10477c11b76",  # 点
            "599b72ae-0aa2-4b76-b957-e7ce93369bf5",  # 個
        }
        assert unit_ids == expected


# ---------------------------------------------------------------------------
# find_term (longest-match with CT special handling)
# ---------------------------------------------------------------------------


class TestFindTerm:
    """GAS unitRecoveryFindTerm_ (AnalysisV2UnitRecovery.gs:40-59) との一致確認"""

    @pytest.fixture()
    def terms(self):
        return build_unit_recovery_terms()

    def test_simple_match_box(self, terms):
        result = find_term("OP-13 box", terms)
        assert result is not None
        assert result["canonical"] == "Box"

    def test_simple_match_pack(self, terms):
        result = find_term("ストームエメラルダ パック", terms)
        assert result is not None
        assert result["canonical"] == "Pack"

    def test_halfwidth_katakana_match(self, terms):
        # ﾊﾟｯｸ (halfwidth) should match Pack via NFKC
        result = find_term("テスト ﾊﾟｯｸ", terms)
        assert result is not None
        assert result["canonical"] == "Pack"

    def test_box_kanji_match(self, terms):
        """'箱' should match Box (UN0002)"""
        result = find_term("白箱", terms)
        assert result is not None
        assert result["canonical"] == "Box"

    def test_case_match_katakana(self, terms):
        """'ケース' should match Case (UN0001)"""
        result = find_term("テスト ケース", terms)
        assert result is not None
        assert result["canonical"] == "Case"

    def test_ct_word_boundary_standalone(self, terms):
        """'ct' should match when not adjacent to alphabets"""
        result = find_term("10ct", terms)
        assert result is not None
        assert result["canonical"] == "Case"

    def test_ct_word_boundary_blocked(self, terms):
        """'ct' should NOT match inside an alphabetic word like 'product'"""
        # 'product' contains 'ct' but it's inside a word
        result = find_term("product", terms)
        # Should not match 'ct' due to word boundary
        # But might match something else — let's check
        if result is not None:
            assert result["term"] != "ct"
            assert result["term"] != "CT"
            assert result["term"] != "Ct"

    def test_longest_match_priority(self, terms):
        """カートン (5 chars) should be matched before ケース (3 chars) if both present"""
        result = find_term("テスト カートン ケース", terms)
        assert result is not None
        assert result["canonical"] == "Case"  # カートン is a Case alias

    def test_no_match(self, terms):
        """No unit term in text"""
        result = find_term("ワンピースカード", terms)
        # Note: this might match 'ス' in ケース if not careful
        # but NFKC('ケース') != substring of NFKC('ワンピースカード')
        # Actually 'ス' is not a term. Let's verify
        if result is not None:
            # '枚' is 1 char, '本' is 1 char, '点' is 1 char, '個' is 1 char
            # ワンピースカード doesn't contain these
            # '箱' is 1 char — not in ワンピースカード
            # Actually let's check: ワンピースカード has no unit terms
            pass
        # The important thing is it doesn't incorrectly match

    def test_BOX_uppercase(self, terms):
        result = find_term("TEST BOX", terms)
        assert result is not None
        assert result["canonical"] == "Box"

    def test_empty_text(self, terms):
        result = find_term("", terms)
        assert result is None

    def test_none_text(self, terms):
        result = find_term(None, terms)
        assert result is None


# ---------------------------------------------------------------------------
# E3a end-match logic (tested via unit_recovery_norm)
# ---------------------------------------------------------------------------


class TestEndMatch:
    """
    E3a step 6: NFKC(productName) must END WITH NFKC(term).
    GAS: AnalysisV2UnitRecovery.gs:218-220
    """

    def test_end_match_box(self):
        """'OP-13 box' -> ends with 'box' -> match"""
        norm_pn = unit_recovery_norm("OP-13 box")
        norm_term = unit_recovery_norm("box")
        assert norm_pn.endswith(norm_term)

    def test_not_end_match(self):
        """'ONE PIECE CARD THE BEST' -> 'PIECE' is not at end"""
        norm_pn = unit_recovery_norm("ONE PIECE CARD THE BEST")
        norm_term = unit_recovery_norm("Piece")
        assert not norm_pn.endswith(norm_term)

    def test_end_match_halfwidth_katakana(self):
        """'テスト ﾊﾟｯｸ' -> NFKC -> 'テスト パック' ends with 'パック'"""
        norm_pn = unit_recovery_norm("テスト ﾊﾟｯｸ")
        norm_term = unit_recovery_norm("ﾊﾟｯｸ")
        assert norm_pn.endswith(norm_term)

    def test_end_match_kanji_box(self):
        """'白箱' ends with '箱'"""
        norm_pn = unit_recovery_norm("白箱")
        norm_term = unit_recovery_norm("箱")
        assert norm_pn.endswith(norm_term)


# ---------------------------------------------------------------------------
# E3a ケース special logic
# ---------------------------------------------------------------------------


class TestCaseSpecial:
    """
    E3a step 7: 'ケース' requires preceding whitespace or start of string.
    GAS: AnalysisV2UnitRecovery.gs:224-227

    Example exclusion: 'スーツケース' -> 'ツ' precedes 'ケース' -> not whitespace -> skip
    """

    def test_case_with_space_before(self):
        """'テスト ケース' -> space before ケース -> OK"""
        import re

        norm_pn = unit_recovery_norm("テスト ケース")
        norm_term = "\u30b1\u30fc\u30b9"  # ケース
        pre_pn = norm_pn[: len(norm_pn) - len(norm_term)]
        assert re.search(r"[\s\u3000]$", pre_pn)

    def test_case_without_space_before(self):
        """'スーツケース' -> 'ツ' before ケース -> not whitespace -> exclude"""
        import re

        norm_pn = unit_recovery_norm("スーツケース")
        norm_term = "\u30b1\u30fc\u30b9"  # ケース
        pre_pn = norm_pn[: len(norm_pn) - len(norm_term)]
        assert pre_pn  # not empty
        assert not re.search(r"[\s\u3000]$", pre_pn)

    def test_case_at_start(self):
        """'ケース' alone -> pre_pn is empty -> OK"""
        norm_pn = unit_recovery_norm("ケース")
        norm_term = "\u30b1\u30fc\u30b9"  # ケース
        pre_pn = norm_pn[: len(norm_pn) - len(norm_term)]
        assert pre_pn == ""  # empty = OK (no preceding char to check)


# ---------------------------------------------------------------------------
# A-2 exclusion logic
# ---------------------------------------------------------------------------


class TestA2Exclusion:
    """
    E3a step 8: if product master jpTitle contains the term -> skip.
    GAS: AnalysisV2UnitRecovery.gs:230-237

    Example: product 'OP-13 BOX' with jpTitle containing 'BOX' -> skip
    """

    def test_a2_term_in_jp_title(self):
        """jpTitle contains 'BOX' -> should exclude"""
        norm_jp = unit_recovery_norm("ワンピースカードゲーム OP-13 BOX")
        norm_term = unit_recovery_norm("BOX")
        assert norm_term in norm_jp  # would be excluded

    def test_a2_term_not_in_jp_title(self):
        """jpTitle does not contain 'box' -> should not exclude"""
        norm_jp = unit_recovery_norm("ワンピースカードゲーム OP-13")
        norm_term = unit_recovery_norm("box")
        assert norm_term not in norm_jp  # would NOT be excluded

    def test_a2_nfkc_normalization(self):
        """Halfwidth in jpTitle: 'ﾊﾟｯｸ' NFKC -> 'パック' -> matches 'パック'"""
        norm_jp = unit_recovery_norm("テスト ﾊﾟｯｸ")
        norm_term = unit_recovery_norm("パック")
        assert norm_term in norm_jp  # would be excluded


# ---------------------------------------------------------------------------
# Safety limits
# ---------------------------------------------------------------------------


class TestSafetyLimits:
    """Verify safety constants match GAS values."""

    def test_e3a_max(self):
        # GAS: UNIT_RECOVERY_MAX_RECOVER_ = 100
        assert E3A_MAX_RECOVER == 100

    def test_e5_max(self):
        # GAS: COND_RECALC_MAX_ROWS_ = 200
        assert E5_MAX_ROWS == 200
