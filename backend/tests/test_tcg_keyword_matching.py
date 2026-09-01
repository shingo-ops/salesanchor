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
    app_kubun_matches,
    match_keyword,
    match_one_kw,
    match_pid_name_first,
    normalize_en,
    resolve_condition_v2,
    resolve_unit_v2,
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


# ---------------------------------------------------------------------------
# app_kubun_matches (GAS appKubunMatches_ 移植)
# ---------------------------------------------------------------------------

class TestAppKubunMatches:
    """GAS appKubunMatches_ (investigate2.gs:9583-9596) との一致確認"""

    def test_empty_app_kubun_matches_all(self):
        assert app_kubun_matches("", "箱系大") is True
        assert app_kubun_matches("", "パック系") is True
        assert app_kubun_matches("", "") is True

    def test_hakokei_dai_matches_hakokei_dai(self):
        assert app_kubun_matches("箱系大", "箱系大") is True

    def test_hakokei_dai_does_not_match_hakokei(self):
        # kubun='箱系' だけでは '箱系大' の条件を満たさない
        assert app_kubun_matches("箱系大", "箱系") is False

    def test_hakokei_matches_hakokei_only(self):
        # '箱系' 条件: "箱系" in kubun AND "箱系大" NOT in kubun
        assert app_kubun_matches("箱系", "箱系") is True

    def test_hakokei_does_not_match_hakokei_dai(self):
        # kubun='箱系大' は '箱系大' を含むので '箱系' 条件ではマッチしない
        assert app_kubun_matches("箱系", "箱系大") is False

    def test_tani_fumei_matches_fumei(self):
        assert app_kubun_matches("単位不明", "不明") is True

    def test_tani_fumei_matches_empty_kubun(self):
        assert app_kubun_matches("単位不明", "") is True

    def test_tani_fumei_does_not_match_tandpin(self):
        # '単品系' は '不明' でも '' でもない
        assert app_kubun_matches("単位不明", "単品系") is False

    def test_pack_kei_matches_pack_kei(self):
        assert app_kubun_matches("パック系", "パック系") is True

    def test_pack_kei_does_not_match_hakokei(self):
        assert app_kubun_matches("パック系", "箱系大") is False

    def test_combo_app_kubun_matches_one(self):
        # '枚系,単位不明' — 枚系 in 単品系? No. 単位不明: '単品系' not in ('不明','') → False
        assert app_kubun_matches("枚系,単位不明", "単品系") is False

    def test_combo_app_kubun_matches_fumei(self):
        # '枚系,単位不明' → 単位不明 条件で kubun='不明' にマッチ
        assert app_kubun_matches("枚系,単位不明", "不明") is True


# ---------------------------------------------------------------------------
# resolve_unit_v2
# ---------------------------------------------------------------------------

# テスト用エイリアスマップ（DB不要）
_UNIT_ALIAS_TO_INFO: dict = {
    "Case": ("Case", "箱系大"),
    "ケース": ("Case", "箱系大"),
    "case": ("Case", "箱系大"),
    "Box": ("Box", "箱系"),
    "ボックス": ("Box", "箱系"),
    "Piece": ("Piece", "単品系"),
    "枚": ("Piece", "単品系"),
    "Pack": ("Pack", "パック系"),
}


class TestResolveUnitV2:
    """resolve_unit_v2 の動作確認"""

    def test_exact_match_returns_canonical_and_kubun(self):
        canonical, kubun, resolved = resolve_unit_v2("Case", _UNIT_ALIAS_TO_INFO)
        assert canonical == "Case"
        assert kubun == "箱系大"
        assert resolved is True

    def test_japanese_alias_resolves(self):
        canonical, kubun, resolved = resolve_unit_v2("ケース", _UNIT_ALIAS_TO_INFO)
        assert canonical == "Case"
        assert kubun == "箱系大"
        assert resolved is True

    def test_lowercase_fallback(self):
        # "CASE" は大文字だが lowercase map で "case" にヒット
        canonical, kubun, resolved = resolve_unit_v2("CASE", _UNIT_ALIAS_TO_INFO)
        assert canonical == "Case"
        assert kubun == "箱系大"
        assert resolved is True

    def test_piece_unit_returns_tanpin_kubun(self):
        canonical, kubun, resolved = resolve_unit_v2("Piece", _UNIT_ALIAS_TO_INFO)
        assert canonical == "Piece"
        assert kubun == "単品系"
        assert resolved is True

    def test_unknown_unit_returns_fumei(self):
        # 未知語 → (raw, '不明', False)
        canonical, kubun, resolved = resolve_unit_v2("謎の単位", _UNIT_ALIAS_TO_INFO)
        assert canonical == "謎の単位"
        assert kubun == "不明"
        assert resolved is False

    def test_empty_string_returns_none(self):
        canonical, kubun, resolved = resolve_unit_v2("", _UNIT_ALIAS_TO_INFO)
        assert canonical is None
        assert kubun == ""
        assert resolved is False

    def test_whitespace_only_returns_none(self):
        canonical, kubun, resolved = resolve_unit_v2("   ", _UNIT_ALIAS_TO_INFO)
        assert canonical is None
        assert kubun == ""
        assert resolved is False


# ---------------------------------------------------------------------------
# resolve_condition_v2
# ---------------------------------------------------------------------------

# GAS 実データに基づくテスト用 condEntries（load_condition_entries 相当）
# priority ASC → app_kubun 長 DESC でソート済み
_COND_ENTRIES = [
    # priority=1
    {
        "cond_id": "uuid-cn0008",
        "code": "CN0008",
        "canonical": "FLAG_SINGLE",
        "priority": 1,
        "app_kubun": "枚系,単位不明",
        "search_kw": "PSA,BGS,CGC,ARS,鑑定,SAR,SR,UR,CHR,プロモ,連番,単品,枚",
        "exclude_kw": "",
    },
    # priority=2, app_kubun長 DESC: パック系(4) > 箱系大(3) > 箱系大(3) > 箱系(2)
    {
        "cond_id": "uuid-cn0010",
        "code": "CN0010",
        "canonical": "Searched pack",
        "priority": 2,
        "app_kubun": "パック系",
        "search_kw": "サーチ済,サーチ済み",
        "exclude_kw": "未サーチ,サーチ痕なし",
    },
    {
        "cond_id": "uuid-cn0002",
        "code": "CN0002",
        "canonical": "Damaged case",
        "priority": 2,
        "app_kubun": "箱系大",
        "search_kw": "傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B",
        "exclude_kw": "",
    },
    {
        "cond_id": "uuid-cn0009",
        "code": "CN0009",
        "canonical": "Opened case",
        "priority": 2,
        "app_kubun": "箱系大",
        "search_kw": "カートンテープカット,テープカット済,テープカット,テープ切",
        "exclude_kw": "",
    },
    {
        "cond_id": "uuid-cn0004",
        "code": "CN0004",
        "canonical": "Damaged sealed box",
        "priority": 2,
        "app_kubun": "箱系",
        "search_kw": "傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B",
        "exclude_kw": "",
    },
    # priority=3, app_kubun='' (全適用)
    {
        "cond_id": "uuid-cn0005",
        "code": "CN0005",
        "canonical": "No shrink box",
        "priority": 3,
        "app_kubun": "",
        "search_kw": "シュリなし,シュリ無し,シュリ無,シュリンクなし,シュリンク無し,シュリンク無,no shrink",
        "exclude_kw": "",
    },
    {
        "cond_id": "uuid-cn0006",
        "code": "CN0006",
        "canonical": "Opened box",
        "priority": 3,
        "app_kubun": "",
        "search_kw": "ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み",
        "exclude_kw": "",
    },
    {
        "cond_id": "uuid-cn0007",
        "code": "CN0007",
        "canonical": "Unsearched pack",
        "priority": 3,
        "app_kubun": "",
        "search_kw": "未サーチ,サーチなし,サーチ痕なし,サーチ痕無し,サーチ無し",
        "exclude_kw": "[サーチ済み]",
    },
    # priority=4, app_kubun長 DESC: 箱系大(3) > 箱系(2)
    {
        "cond_id": "uuid-cn0001",
        "code": "CN0001",
        "canonical": "Case",
        "priority": 4,
        "app_kubun": "箱系大",
        "search_kw": "通常品,[通常品]",
        "exclude_kw": "傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B",
    },
    {
        "cond_id": "uuid-cn0003",
        "code": "CN0003",
        "canonical": "Sealed box",
        "priority": 4,
        "app_kubun": "箱系",
        "search_kw": "通常品,[通常品],未開封,新品未開封,新品,シュリンク付き,シュリ付,シュリ付き,シュリンクあり,シュリ有り,シュリ有",
        "exclude_kw": "傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B",
    },
]

_COND_UUID_MAP = {e["canonical"]: e["cond_id"] for e in _COND_ENTRIES}


class TestResolveConditionV2:
    """
    GAS resolveCondition_ R1〜R4 ロジック移植の動作確認。
    DB接続不要 — _COND_ENTRIES でモック。
    """

    # --- R1: flagNote ---

    def test_r1_flag_note_prepended_when_box_contains_single_kw(self):
        # kubun='箱系大'（isBoxOrCase=True）+ raw_state に SR（FLAG_SINGLE 語）を含む
        # → flagNote が basis に付く。最終マッチは R4:通常品（Case）
        canonical, cond_id, basis = resolve_condition_v2(
            "SR 通常品", "", "箱系大", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Case"
        assert cond_id == "uuid-cn0001"
        assert "単品語あり・要確認" in basis
        assert "SR" in basis
        assert "R4" in basis

    def test_r1_no_flag_note_when_not_box(self):
        # kubun='単品系'（isBoxOrCase=False）→ flagNote は付かない
        # FLAG_SINGLE 語があっても basis に "単品語あり" は出ない
        canonical, cond_id, basis = resolve_condition_v2(
            "SR", "", "単品系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert "単品語あり" not in basis

    # --- R2: ダメージ語 ---

    def test_r2_damaged_case_with_hakokei_dai(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "傷み", "", "箱系大", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Damaged case"
        assert cond_id == "uuid-cn0002"
        assert basis.startswith("R2:")

    def test_r2_damaged_sealed_box_with_hakokei(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "箱痛み", "", "箱系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Damaged sealed box"
        assert cond_id == "uuid-cn0004"
        assert basis.startswith("R2:")

    def test_r2_damage_kw_ignored_for_pack_kei(self):
        # パック系 + 傷み → R2 Damaged case/sealed box の appKubun が不一致 → R3/R4b へ
        canonical, cond_id, basis = resolve_condition_v2(
            "傷み", "", "パック系", _COND_ENTRIES, _COND_UUID_MAP
        )
        # Damage 語は '箱系大'/'箱系' の条件 → パック系では R2 はスキップ
        assert canonical != "Damaged case"
        assert canonical != "Damaged sealed box"

    # --- R3: 特殊語（シュリなし / ペリなし / 未サーチ） ---

    def test_r3_no_shrink_box(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "シュリなし", "", "箱系大", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "No shrink box"
        assert cond_id == "uuid-cn0005"
        assert basis.startswith("R3:")

    def test_r3_opened_box(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "ペリ無し", "", "箱系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Opened box"
        assert cond_id == "uuid-cn0006"
        assert basis.startswith("R3:")

    def test_r3_unsearched_pack(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "未サーチ", "", "パック系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Unsearched pack"
        assert cond_id == "uuid-cn0007"
        assert basis.startswith("R3:")

    def test_r3_searched_pack_excluded_by_unsearched(self):
        # CN0007 exclude_kw=['[サーチ済み]'] で '[サーチ済み]' を除外
        # 'サーチ痕なし' が raw_state にある → CN0007 exclude_kw に 'サーチ痕なし'... wait
        # CN0007 exclude_kw='[サーチ済み]' — これは '[サーチ済み]' という文字列
        # raw_state='[サーチ済み] 未サーチ' → exclude_kw=['[サーチ済み]'] → [... ']' hit?
        # Actually let's test: raw_state='[サーチ済み]' → CN0007 search='未サーチ,...' → no hit anyway
        # Better test: exclude blocks CN0010 Searched pack
        canonical, cond_id, basis = resolve_condition_v2(
            "サーチ痕なし", "", "パック系", _COND_ENTRIES, _COND_UUID_MAP
        )
        # 'サーチ痕なし' → CN0010 exclude_kw に '未サーチ,サーチ痕なし' があるので除外
        # CN0007 search_kw に 'サーチ痕なし' あり → Unsearched pack
        assert canonical == "Unsearched pack"

    # --- R4a: data-driven ---

    def test_r4a_case_tsujohin(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "通常品", "", "箱系大", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Case"
        assert cond_id == "uuid-cn0001"
        assert "R4" in basis
        assert "通常品" in basis

    def test_r4a_sealed_box_mikaifuu(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "未開封", "", "箱系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Sealed box"
        assert cond_id == "uuid-cn0003"
        assert "R4" in basis

    # --- R4b: code fallback ---

    def test_r4b_empty_state_hakokei_dai_returns_case(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "", "", "箱系大", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Case"
        assert basis == "R4:単位既定"

    def test_r4b_empty_state_hakokei_returns_sealed_box(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "", "", "箱系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Sealed box"
        assert basis == "R4:単位既定"

    def test_r4b_empty_state_tanpin_returns_flag_single(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "", "", "単品系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "FLAG_SINGLE"
        assert "R4:単位既定" in basis

    def test_r4b_empty_state_fumei_returns_flag_single(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "", "", "不明", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "FLAG_SINGLE"

    # --- CN0008 Piece シナリオ（ユーザー要件必須）---
    # raw_state に FLAG_SINGLE 語 (PSA10) があり kubun='単品系' の場合：
    #   - R1 pre-pass: isBoxOrCase=False → flagNote なし
    #   - Main loop: CN0008 appKubun='枚系,単位不明' vs kubun='単品系':
    #       '枚系' in '単品系'? No ('単品系' != '枚系' substring)
    #       '単位不明': '単品系' in ('不明','')? No
    #       → False → CN0008 は main loop でマッチしない
    #   - R4b fallback: kubun='単品系' → FLAG_SINGLE
    # GAS の動作と一致 (R4 経由)

    def test_cn0008_piece_reaches_flag_single_via_r4_not_main_loop(self):
        canonical, cond_id, basis = resolve_condition_v2(
            "PSA10", "", "単品系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "FLAG_SINGLE"
        # main loop ではなく R4b 経由なので basis は "R4:単位既定:単位不明"
        assert "R4:単位既定" in basis
        # flagNote は付かない（isBoxOrCase=False）
        assert "単品語あり" not in basis

    # --- R5: パック既定 (GAS: applyPackConditionDefault, AnalysisV2PackCondition.gs) ---
    # kubun=パック系(UN0003) かつ R4b で FLAG_SINGLE になる行は R5 で Searched pack に変換。
    # GAS 実測: basisDist R5=60件, Searched pack=61件 (残1件はキーワード直接マッチ)。

    def test_r5_pack_kubun_empty_state_returns_searched_pack(self):
        # raw_state='' + kubun='パック系' → main loop 不一致 → R4b → R5:パック既定
        canonical, cond_id, basis = resolve_condition_v2(
            "", "", "パック系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Searched pack"
        assert cond_id == "uuid-cn0010"
        assert basis == "R5:パック既定"

    def test_r5_pack_kubun_with_unmatched_state_returns_searched_pack(self):
        # raw_state='買取品'（どのキーワードにも一致しない）+ kubun='パック系' → R5
        canonical, cond_id, basis = resolve_condition_v2(
            "買取品", "", "パック系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Searched pack"
        assert basis == "R5:パック既定"

    def test_r5_not_applied_to_tanpin_kei(self):
        # 単品系は R5 対象外 → FLAG_SINGLE のまま
        canonical, cond_id, basis = resolve_condition_v2(
            "", "", "単品系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "FLAG_SINGLE"
        assert "R4:単位既定" in basis

    def test_r5_not_applied_when_keyword_already_matched(self):
        # サーチ済み → CN0010 の search_kw にヒット → R2/main ループで Searched pack (basis=R2: ではなく R2:サーチ済み)
        # R5 より前にキーワードマッチが発火するので basis は R5 ではない
        canonical, cond_id, basis = resolve_condition_v2(
            "サーチ済み", "", "パック系", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "Searched pack"
        assert "R5" not in basis  # キーワードマッチ経由なので R5 basis ではない

    # --- ORDER BY タイブレーカー: CN0005 (No shrink box) が CN0006 (Opened box) より先 ---
    # GAS 根拠: investigate2.gs:9705-9710 — SHURI チェックが PERI より先に実行される。
    # _COND_ENTRIES は code ASC 順 (CN0005→CN0006) で定義済み。

    def test_r3_shuri_wins_over_peri_when_both_present(self):
        # 'シュリなし　ペリなし' — 両キーワードが存在するとき CN0005 (No shrink box) が先にヒット
        canonical, cond_id, basis = resolve_condition_v2(
            "シュリなし\u3000ペリなし", "", "条件つき", _COND_ENTRIES, _COND_UUID_MAP
        )
        assert canonical == "No shrink box"
        assert cond_id == "uuid-cn0005"
        assert "R3:シュリなし" in basis
