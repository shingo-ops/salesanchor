"""
GAS investigate2.gs との動作一致検証テスト。

GAS matchKeyword_ エンジンの移植 (name-first-v2) を単体で検証する。
DB接続不要。

GAS 対応行:
  normalizeEn_  : investigate2.gs:9569
  tokenAndMatch_: investigate2.gs:9730
  matchOneKw_   : investigate2.gs:9977
  matchKeyword_ : investigate2.gs:9995
"""
from __future__ import annotations

import pytest

from app.services.tcg_analyzer_svc import (
    match_keyword,
    match_one_kw,
    match_pid_name_first,
    normalize_en,
    token_and_match,
)


# ---------------------------------------------------------------------------
# normalize_en
# ---------------------------------------------------------------------------

class TestNormalizeEn:
    """GAS normalizeEn_ (investigate2.gs:9569) との一致確認"""

    def test_fullwidth_latin_to_halfwidth(self):
        # Ａ (U+FF21) → A (U+0041) → lowercase a
        assert normalize_en("Ａ") == "a"

    def test_fullwidth_digits(self):
        # １００ → 100
        assert normalize_en("１００") == "100"

    def test_fullwidth_symbols(self):
        # ！ (U+FF01) → ! (U+0021)
        assert normalize_en("！") == "!"

    def test_already_halfwidth(self):
        assert normalize_en("hello") == "hello"

    def test_uppercase_lowercased(self):
        assert normalize_en("Hello World") == "hello world"

    def test_japanese_unchanged(self):
        # ひらがな・カタカナは U+FF01-FF60 の範囲外 → 変換なし
        assert normalize_en("ポケモン") == "ポケモン"

    def test_mixed_fullwidth_halfwidth(self):
        # "スタートデッキ１００" → "スタートデッキ100"
        assert normalize_en("スタートデッキ１００") == "スタートデッキ100"

    def test_empty_string(self):
        assert normalize_en("") == ""

    def test_none_equivalent(self):
        # GAS: (s || '') — Python は呼び出し側で保証するが空文字も通す
        assert normalize_en("") == ""

    def test_fullwidth_ampersand(self):
        # ＆ (U+FF06) → & (U+0026)
        assert normalize_en("ＰＫＭ＆ＰＫＭ") == "pkm&pkm"


# ---------------------------------------------------------------------------
# token_and_match
# ---------------------------------------------------------------------------

class TestTokenAndMatch:
    """GAS tokenAndMatch_ (investigate2.gs:9730) との一致確認"""

    def test_single_token_hit(self):
        # kw="サーチ済" → token=["サーチ済"] → in norm_text
        norm_text = normalize_en("買取品のためサーチ済みの可能性あり")
        assert token_and_match("サーチ済", norm_text) is True

    def test_two_tokens_both_present(self):
        # kw="ブラックボルト DX" → tokens=["ブラックボルト", "dx"]
        norm_text = normalize_en("ブラックボルト DX ボックス")
        assert token_and_match("ブラックボルト DX", norm_text) is True

    def test_two_tokens_order_independent(self):
        # 順序不問 (AND照合)
        norm_text = normalize_en("DX ブラックボルト ボックス")
        assert token_and_match("ブラックボルト DX", norm_text) is True

    def test_missing_token_returns_false(self):
        norm_text = normalize_en("ブラックボルト ボックス")
        assert token_and_match("ブラックボルト DX", norm_text) is False

    def test_fullwidth_in_kw_normalizes(self):
        # キーワード側の全角数字が正規化されて一致
        # kw="スタートデッキ１００" → normalize → "スタートデッキ100"
        norm_text = normalize_en("スタートデッキ100")
        assert token_and_match("スタートデッキ１００", norm_text) is True

    def test_empty_kw_returns_false(self):
        assert token_and_match("", "任意テキスト") is False

    def test_space_only_kw_returns_false(self):
        assert token_and_match("   ", "任意テキスト") is False

    def test_4th_anniversary_space_keyword(self):
        # "4周年 四皇トレジャーゲット" は空白で2トークン → AND照合
        # 元テキスト: "4周年!四皇トレジャーゲット キャンペーンパック"
        kw = "4周年 四皇トレジャーゲット"
        norm_text = normalize_en("4周年!四皇トレジャーゲット キャンペーンパック")
        # token_and_match は空白分割のみ → "4周年" と "四皇トレジャーゲット" の2トークン
        assert token_and_match(kw, norm_text) is True


# ---------------------------------------------------------------------------
# match_one_kw
# ---------------------------------------------------------------------------

class TestMatchOneKw:
    """GAS matchOneKw_ (investigate2.gs:9977) との一致確認"""

    # --- ASCII 単語境界 ---

    def test_ascii_word_boundary_no_false_positive(self):
        # "AR" が "CARD" にヒットしない (GAS 要件)
        norm_text = normalize_en("CARD")  # "card"
        assert match_one_kw("AR", norm_text) is False

    def test_ascii_word_boundary_standalone(self):
        # "AR" が "AR ボックス" にヒットする
        norm_text = normalize_en("AR ボックス")
        assert match_one_kw("AR", norm_text) is True

    def test_ascii_case_insensitive(self):
        # "sr" でも "SR" テキストにヒット
        norm_text = normalize_en("SR ランダムバルク")
        assert match_one_kw("sr", norm_text) is True

    def test_ascii_surrounded_by_japanese(self):
        # "PSA" が "PSA鑑定品" に — 後ろが日本語なので境界あり
        norm_text = normalize_en("PSA鑑定品")
        assert match_one_kw("PSA", norm_text) is True

    def test_ascii_no_partial_word(self):
        # "SAR" が "ランダムバルクSAR" にヒット（前が日本語）
        norm_text = normalize_en("ランダムバルクSAR")
        assert match_one_kw("SAR", norm_text) is True

    def test_ascii_partial_match_blocked(self):
        # "SA" が "SAR" にヒットしない（後ろに [a-z] がある）
        norm_text = normalize_en("SAR")
        assert match_one_kw("SA", norm_text) is False

    # --- 日本語 → tokenAndMatch_ ---

    def test_japanese_single_token(self):
        norm_text = normalize_en("メガドリームボックス")
        assert match_one_kw("メガドリーム", norm_text) is True

    def test_japanese_token_miss(self):
        norm_text = normalize_en("スタートデッキ")
        assert match_one_kw("メガドリーム", norm_text) is False

    def test_empty_kw_returns_false(self):
        assert match_one_kw("", "any") is False

    # --- 全角/半角混在 ---

    def test_fullwidth_kw_matches_halfwidth_text(self):
        # キーワード "スタートデッキ１００" → normalize → "スタートデッキ100"
        # テキスト "スタートデッキ100" → normalize → "スタートデッキ100"
        norm_text = normalize_en("スタートデッキ100")
        assert match_one_kw("スタートデッキ１００", norm_text) is True

    def test_halfwidth_kw_matches_fullwidth_text(self):
        # キーワード "スタートデッキ100" → normalize → "スタートデッキ100"
        # テキスト "スタートデッキ１００" → normalize → "スタートデッキ100"
        norm_text = normalize_en("スタートデッキ１００")
        assert match_one_kw("スタートデッキ100", norm_text) is True


# ---------------------------------------------------------------------------
# match_keyword
# ---------------------------------------------------------------------------

class TestMatchKeyword:
    """GAS matchKeyword_ (investigate2.gs:9995) との一致確認"""

    def test_hit_with_single_kw(self):
        hit, kw = match_keyword("ポケモン card box", ["ポケモン"], [])
        assert hit is True
        assert kw == "ポケモン"

    def test_no_hit_returns_false(self):
        hit, kw = match_keyword("ワンピース card", ["ポケモン"], [])
        assert hit is False
        assert kw is None

    def test_exclude_kw_blocks_hit(self):
        # 検索語ヒットでも除外語があれば除外
        hit, kw = match_keyword("ポケモン バルク", ["ポケモン"], ["バルク"])
        assert hit is False
        assert kw is None

    def test_empty_search_kw_returns_all_match(self):
        # GAS: searchKwStr が空 → '(既定)' でhit
        hit, kw = match_keyword("任意テキスト", [], [])
        assert hit is True
        assert kw == "(既定)"

    def test_ascii_word_boundary(self):
        # "AR" が "CARD" にヒットしない
        hit, _ = match_keyword("CARD", ["AR"], [])
        assert hit is False

    def test_fullwidth_text_kw_match(self):
        # 全角テキスト "スタートデッキ１００" にキーワード "スタートデッキ100" がヒット
        hit, matched = match_keyword("スタートデッキ１００", ["スタートデッキ100"], [])
        assert hit is True

    def test_space_keyword_token_and(self):
        # "4周年 四皇トレジャーゲット" → 2トークンAND
        hit, matched = match_keyword(
            "4周年!四皇トレジャーゲット キャンペーンパック",
            ["4周年 四皇トレジャーゲット"],
            [],
        )
        assert hit is True

    def test_first_matching_kw_returned(self):
        hit, matched = match_keyword("ポケモン", ["ドラゴン", "ポケモン", "遊戯王"], [])
        assert hit is True
        assert matched == "ポケモン"


# ---------------------------------------------------------------------------
# match_pid_name_first (統合)
# ---------------------------------------------------------------------------

class TestMatchPidNameFirst:
    """match_pid_name_first の統合動作確認"""

    def test_single_candidate(self):
        code, basis, resolved, candidates = match_pid_name_first(
            "ポケモン ボックス",
            ["PM0001", "PM0002"],
            {"PM0001": ["ポケモン"], "PM0002": ["ワンピース"]},
            {},
        )
        assert resolved is True
        assert code == "PM0001"
        assert "SK:" in basis

    def test_no_candidate(self):
        code, basis, resolved, candidates = match_pid_name_first(
            "遊戯王 パック",
            ["PM0001"],
            {"PM0001": ["ポケモン"]},
            {},
        )
        assert resolved is False
        assert code is None
        assert basis == "NONE"

    def test_excluded_candidate_not_returned(self):
        code, basis, resolved, candidates = match_pid_name_first(
            "ポケモン バルク",
            ["PM0001"],
            {"PM0001": ["ポケモン"]},
            {"PM0001": ["バルク"]},
        )
        assert resolved is False
        assert code is None

    def test_multi_candidate(self):
        code, basis, resolved, candidates = match_pid_name_first(
            "ポケモン カード",
            ["PM0001", "PM0002"],
            {"PM0001": ["ポケモン"], "PM0002": ["ポケモン カード"]},
            {},
        )
        # PM0002 のキーワード "ポケモン カード" (len=7) > PM0001 の "ポケモン" (len=4)
        assert resolved is False  # 複数候補
        assert "MULTI" in basis

    def test_fullwidth_kw_match(self):
        # テキスト側に全角数字 → normalize_en で吸収
        code, basis, resolved, _ = match_pid_name_first(
            "スタートデッキ１００",
            ["PM0001"],
            {"PM0001": ["スタートデッキ100"]},
            {},
        )
        assert resolved is True
        assert code == "PM0001"

    def test_ascii_word_boundary_no_false_positive(self):
        # "AR" が "CARD" にヒットしない
        code, basis, resolved, _ = match_pid_name_first(
            "CARD",
            ["PM0001"],
            {"PM0001": ["AR"]},
            {},
        )
        assert resolved is False
