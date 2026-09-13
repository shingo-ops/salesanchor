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

from unittest.mock import MagicMock

import pytest

from app.services.tcg_analyzer_svc import (
    app_kubun_matches,
    build_note_ja,
    build_review_reasons,
    load_note_master,
    match_keyword,
    match_one_kw,
    match_pid_name_first,
    normalize_en,
    resolve_condition_v2,
    resolve_unit_v2,
    token_and_match,
)


def _note_entry(
    note_id: str,
    label_ja: str,
    *,
    match_type: str = "LITERAL",
    search_keywords: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
    search_pattern: str = "",
    label_template: str = "",
) -> dict:
    return {
        "id": note_id,
        "label_ja": label_ja,
        "match_type": match_type,
        "search_keywords": search_keywords or [],
        "exclude_keywords": exclude_keywords or [],
        "search_pattern": search_pattern,
        "label_template": label_template,
    }


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

    def test_empty_search_kw_returns_no_match(self):
        # GAS: matchPid_(!srchStr) → return でスキップ。キーワード未登録商品は候補にしない
        hit, kw = match_keyword("任意テキスト", [], [])
        assert hit is False
        assert kw is None

    def test_empty_search_kw_with_text_returns_no_match(self):
        # キーワード未登録商品はいかなる商品名でも候補にならない
        hit, kw = match_keyword("スタートデッキGenerations", [], [])
        assert hit is False
        assert kw is None

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
# build_note_ja / build_review_reasons (NOTE-B2)
# ---------------------------------------------------------------------------

class TestLoadNoteMaster:
    def test_loads_regex_fields(self):
        session = MagicMock()
        session.execute.return_value.fetchall.return_value = [
            (
                "NJ030",
                "指定日発送",
                "",
                "完売",
                2,
                "REGEX",
                r"(\d{1,2})/(\d{1,2})発送",
                "$1/$2発送",
            )
        ]

        assert load_note_master(session) == [
            {
                "id": "NJ030",
                "label_ja": "指定日発送",
                "search_keywords": [],
                "exclude_keywords": ["完売"],
                "match_type": "REGEX",
                "search_pattern": r"(\d{1,2})/(\d{1,2})発送",
                "label_template": "$1/$2発送",
            }
        ]
        statement = str(session.execute.call_args.args[0])
        assert "match_type, search_pattern, label_template" in statement


_EXISTING_LITERAL_NOTE_CASES = [
    ("NJ001", "検品開封済み", "検品のため", ["テープカット", "カートンテープカット"]),
    ("NJ002", "プロモ付き", "プロモ付", ["プロモ無し", "プロモなし", "プロモ無", "雑誌プロモ", "カードセット"]),
    ("NJ003", "プロモなし", "プロモ無し", ["プロモ付", "プロモ入り"]),
    ("NJ004", "再販品", "再販", ["初版", "初回生産"]),
    ("NJ005", "初版品", "初版", ["再販", "再版"]),
    ("NJ006", "ダメージ", "ダメージ", []),
    ("NJ007", "スジ", "スジ", ["スペースジャグラー"]),
    ("NJ008", "凹み", "凹み", []),
    ("NJ009", "潰れ", "潰れ", []),
    ("NJ010", "破れ・破損", "破れ", []),
    ("NJ011", "反り", "反り", []),
    ("NJ012", "傷・キズ", "キズ", ["傷み", "箱痛み"]),
    ("NJ013", "汚れ", "汚れ", []),
    ("NJ014", "箱痛み", "箱痛み", []),
    ("NJ015", "被りあり", "被りあり", ["被りなし", "重複なし"]),
    ("NJ016", "被りなし", "被りなし", ["被りあり"]),
    ("NJ017", "ランダム", "ランダム", ["完全ランダム", "被りなし"]),
    ("NJ018", "完全ランダム", "完全ランダム", []),
    ("NJ019", "白箱", "白箱", []),
    ("NJ020", "スリーブ入り", "スリーブ入り", ["スリーブ無し", "スリーブなし"]),
    ("NJ021", "本付き", "本付き", []),
    ("NJ022", "雑誌付き", "雑誌付き", []),
    ("NJ023", "発売日発送", "発売日発送", ["前日", "翌日", "時まで", "注文で", "注文確定"]),
    ("NJ024", "発売日前日発送", "発売日前日", []),
    ("NJ025", "発売日翌日発送", "発売日翌日", ["受注の翌日"]),
    ("NJ026", "即日発送可", "即日発送", []),
    ("NJ027", "入荷次第発送", "入荷次第", []),
    ("NJ028", "発送日要相談", "発送日要相談", []),
    ("NJ029", "国内発送のみ", "国内発送のみ", []),
    ("NJ035", "買取品", "買取品", []),
    ("NJ036", "問屋品", "問屋", []),
    ("NJ037", "店舗品", "店舗仕入", []),
    ("NJ038", "正規流通品", "正規流通", []),
    ("NJ039", "サーチ済の可能性", "サーチ済", ["サーチ痕無", "サーチ痕なし", "サーチ跡無", "未サーチ"]),
    ("NJ040", "未サーチ", "未サーチ", []),
    ("NJ041", "伝票跡", "伝票跡", []),
    ("NJ042", "テープ跡", "テープ跡", ["テープカット"]),
    ("NJ043", "ラベル跡", "ラベル跡", []),
    ("NJ044", "シリアル切り取り", "シリアル切り取り", ["シリアルのみ"]),
    ("NJ045", "カートン数字記載", "数字の記載", []),
    ("NJ046", "段ボール傷", "段ボール傷", []),
    ("NJ047", "B品", "B品", []),
    ("NJ048", "上部切り取り", "上部切り取り", []),
    ("NJ049", "美品", "美品", []),
    ("NJ050", "カートン発送可", "カートン可", []),
    ("NJ054", "大口割引可", "大口", []),
    ("NJ055", "写真掲載可", "写真掲載可", []),
    ("NJ056", "SNS投稿不可", "SNSへの投稿不可", []),
]


@pytest.mark.parametrize(
    ("note_id", "label_ja", "representative_memo", "exclude_keywords"),
    _EXISTING_LITERAL_NOTE_CASES,
)
def test_existing_48_literal_note_outputs_are_preserved(
    note_id: str,
    label_ja: str,
    representative_memo: str,
    exclude_keywords: list[str],
):
    entries = [
        _note_entry(
            note_id,
            label_ja,
            search_keywords=[representative_memo],
            exclude_keywords=exclude_keywords,
        )
    ]
    assert build_note_ja(representative_memo, entries) == label_ja


class TestBuildNoteJa:
    def test_literal_behavior_is_preserved(self):
        entries = [
            _note_entry("NJ063", "予約商品", search_keywords=["予約商品", "予約品"])
        ]
        assert build_note_ja("予約商品です", entries) == "予約商品"

    def test_regex_normalizes_fullwidth_date_and_expands_groups(self):
        entries = [
            _note_entry(
                "NJ030",
                "指定日発送",
                match_type="REGEX",
                search_pattern=r"(\d{1,2})[/月](\d{1,2})日?.{0,4}?(発送|出荷)",
                label_template="$1/$2発送",
            )
        ]
        assert build_note_ja("９／１６（水）発送", entries) == "9/16発送"

    def test_optional_capture_is_preserved(self):
        entries = [
            _note_entry(
                "NJ033",
                "到着後発送",
                match_type="REGEX",
                search_pattern=r"到着後\s*(\d{1,2})日以内発送(目安)?",
                label_template="到着後$1日以内発送$2",
            )
        ]
        assert build_note_ja("到着後3日以内発送目安", entries) == "到着後3日以内発送目安"

    def test_exclusion_wall_prevents_broad_date_duplicate(self):
        entries = [
            _note_entry(
                "NJ051",
                "日付前後発送",
                match_type="REGEX",
                search_pattern=r"(\d{1,2})/(\d{1,2})前後(発送|入荷)",
                label_template="$1/$2前後発送",
                exclude_keywords=["完売"],
            ),
            _note_entry(
                "NJ030",
                "指定日発送",
                match_type="REGEX",
                search_pattern=r"(\d{1,2})[/月](\d{1,2})日?.{0,4}?(発送|出荷)",
                label_template="$1/$2発送",
                exclude_keywords=["完売", "前後", "までに", "〜", "~", "ー", "-"],
            ),
        ]
        assert build_note_ja("9/12前後発送", entries) == "9/12前後発送"

    def test_exclusion_wall_can_leave_compound_memo_unmatched(self):
        entries = [
            _note_entry(
                "NJ031",
                "日付範囲発送",
                match_type="REGEX",
                search_pattern=r"(\d{1,2})月(\d{1,2})日[〜~ー-](\d{1,2})日出荷",
                label_template="$1/$2〜$1/$3発送",
                exclude_keywords=["完売"],
            )
        ]
        assert build_note_ja("9月16日〜18日出荷は完売", entries) is None

    def test_invalid_regex_is_ignored(self):
        entries = [
            _note_entry(
                "BROKEN",
                "壊れた札",
                match_type="REGEX",
                search_pattern="(",
                label_template="$1",
            )
        ]
        assert build_note_ja("任意のメモ", entries) is None


class TestBuildReviewReasons:
    def test_unmatched_nonempty_memo_is_added(self):
        assert build_review_reasons(True, [], "未分類メモ", None) == ["note_unmatched"]

    def test_matched_note_does_not_add_reason(self):
        assert build_review_reasons(True, [], "9/16発送", "9/16発送") == []

    def test_blank_memo_does_not_add_reason(self):
        assert build_review_reasons(True, [], "   ", None) == []

    def test_existing_reasons_keep_order_before_note_unmatched(self):
        assert build_review_reasons(False, ["PM1", "PM2"], "未分類メモ", None) == [
            "pid_unresolved",
            "multi_candidate",
            "note_unmatched",
        ]


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


_MEMO_NEGATIONS = "[サーチ済み],未サーチではない,未サーチではありません,未サーチとは限らない,未サーチ保証なし,未サーチ保証無し,サーチ済"
_STATE_NEGATIONS = ["伝票剥がし跡ありません", "伝票剥がし跡ありではない", "伝票剥がし跡ありではありません"]


@pytest.mark.parametrize("memo,expected", [
    ("※未サーチ品", "Unsearched pack"), ("サーチ痕なし", "Unsearched pack"),
    ("", "Searched pack"), ("未サーチではない", "Searched pack"),
    ("未サーチではありません", "Searched pack"), ("未サーチとは限らない", "Searched pack"),
    ("未サーチ保証なし", "Searched pack"), ("未サーチ保証無し", "Searched pack"),
    ("未サーチ サーチ済み混在", "Searched pack"), ("配送後の破損は保証しません", "Searched pack"),
])
def test_condition_memo_pack_default_only(memo, expected):
    entries = [dict(e, exclude_kw=_MEMO_NEGATIONS) if e["code"] == "CN0007" else e for e in _COND_ENTRIES]
    actual = resolve_condition_v2("", "商品", "パック系", entries, _COND_UUID_MAP, raw_memo=memo)
    assert actual[0] == expected
    assert actual[2].startswith("R3:MEMO:") if expected == "Unsearched pack" else actual[2] == "R5:パック既定"


@pytest.mark.parametrize("state,kubun", [("", "箱系"), ("", "箱系大"), ("", "不明"),
                                               ("サーチ済み", "パック系"), ("ペリなし", "パック系")])
def test_condition_memo_preserves_existing_decision(state, kubun):
    entries = [*_COND_ENTRIES, {"code": "CN0010", "cond_id": "searched", "canonical": "Searched pack",
                               "priority": 4, "app_kubun": "パック系", "search_kw": "サーチ済", "exclude_kw": ""}]
    baseline = resolve_condition_v2(state, "商品", kubun, entries, _COND_UUID_MAP)
    assert resolve_condition_v2(state, "商品", kubun, entries, _COND_UUID_MAP, raw_memo="未サーチ") == baseline


def test_condition_memo_missing_or_disabled_priority_master():
    entries = [e for e in _COND_ENTRIES if e["code"] != "CN0007"]
    assert resolve_condition_v2("", "商品", "パック系", entries, {}, raw_memo="未サーチ")[0] == "Searched pack"
    disabled = dict(next(e for e in _COND_ENTRIES if e["code"] == "CN0007"), priority=0)
    assert resolve_condition_v2("", "商品", "パック系", [*entries, disabled], {}, raw_memo="未サーチ")[0] == "Searched pack"


@pytest.mark.parametrize("memo,state,expected", [
    ("", "伝票剥がし跡あり", "伝票剥がし跡あり"),
    ("伝票剥がし跡あり", "", "伝票剥がし跡あり"),
    ("伝票剥がし跡あり", "伝票剥がし跡あり", "伝票剥がし跡あり"),
    ("伝票跡", "", "伝票跡"), ("", "伝票跡", None),
    ("", "伝票剥がし跡なし", None),
    *[("", word, None) for word in _STATE_NEGATIONS],
    ("", "", None),
])
def test_state_literal_note_scope_and_negation(memo, state, expected):
    notes = [{"id": "NJ041", "label_ja": "伝票跡", "match_type": "LITERAL",
              "search_keywords": ["伝票跡", "伝票痕", "伝票剥がし跡"], "exclude_keywords": ["伝票剥がし跡あり"]},
             {"id": "NJ079", "label_ja": "伝票剥がし跡あり", "match_type": "STATE_LITERAL",
              "search_keywords": ["伝票剥がし跡あり"], "exclude_keywords": _STATE_NEGATIONS}]
    assert build_note_ja(memo, notes, raw_state=state) == expected


def test_state_does_not_feed_legacy_regex_or_literal():
    notes = [{"id": "legacy", "label_ja": "旧札", "match_type": "LITERAL",
              "search_keywords": ["伝票跡"], "exclude_keywords": []},
             {"id": "regex", "label_ja": "空", "match_type": "REGEX", "search_pattern": "^$",
              "search_keywords": [], "exclude_keywords": []}]
    assert build_note_ja("", notes, raw_state="伝票跡") is None


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


# CARD-LINE-WORK-MATCHING-V3-01: work evidence and product-only gates.
from app.services.tcg_analyzer_svc import (
    is_model_keyword,
    match_pid_with_work,
    resolve_work_evidence,
)

WORKS = [
    dict(id="pokemon", display_name="Pokemon", alt_name="ポケモン"),
    dict(id="onepiece", display_name="One Piece", alt_name="ワンピース"),
    dict(id="gundam", display_name="GUNDAM", alt_name="ガンダム"),
]


@pytest.mark.parametrize("keyword,expected", [
    ("EB01", True), ("EB-01", True), ("EB - 01", True), ("S8a-G", True),
    ("ＥＢ０１", True), ("EB01 special", False), ("151", False), ("AR", False),
    ("THE BEST vol.2", False), ("MEGA スタートデッキ100", False),
])
def test_model_keyword_contract(keyword, expected):
    assert is_model_keyword(keyword) is expected


@pytest.mark.parametrize("name,source,start,end,work,span,expected", [
    ("ガンダム EB01", "ガンダム EB01", 1, 1, "ガンダム", "L0001", "gundam"),
    ("EB01", "【ガンダム】\nEB01", 2, 2, "ガンダム", "L0001", "gundam"),
    ("EB01", "[GUNDAM]\nEB01", 2, 2, "GUNDAM", "L0001", "gundam"),
    ("EB01", "ガンダム EB01\nEB01", 2, 2, "ガンダム", "L0001", None),
    ("EB01", "ガンダム\nワンピース\nEB01", 3, 3, "ガンダム", "L0001", None),
    ("EB01", "ガンダム\nワンピース\nEB01", 3, 3, "ワンピース", "L0002", "onepiece"),
    ("ポケモン 商品", "ガンダム\nポケモン 商品", 2, 2, "ポケモン", "L0002", "pokemon"),
    ("ポケモン 商品", "ガンダム\nポケモン 商品", 2, 2, "ガンダム", "L0001", None),
    ("ガンダム ワンピース EB01", "ガンダム ワンピース EB01", 1, 1, "ガンダム", "L0001", None),
    ("EB01", "ガンダム\nEB01", 2, 2, "GUNDAM", "L0001", None),
    ("ガンダム EB01", "ガンダム EB01", 1, 1, "ガンダム", "L0099", None),
    ("ガンダム EB01", "ガンダム EB01", 1, 1, "未知", "L0001", None),
    ("ガンダム EB01", "ガンダム EB01", 1, 1, "", "", None),
    ("ガンダム EB01", "ガンダム EB01", 1, 1, None, None, "gundam"),
    # v5: missing evidence uses the explicit independent raw work heading.
    ("EB01", "ガンダム\nEB01", 2, 2, None, None, "gundam"),
])
def test_work_scope(name, source, start, end, work, span, expected):
    assert resolve_work_evidence(name, source, start, end, work, span, WORKS) == expected


def test_inactive_duplicate_and_unsplit_aliases_rejected():
    assert resolve_work_evidence("ガンダム EB01", "", 1, 1, None, None,
                                 [dict(WORKS[2], is_active=False)]) is None
    assert resolve_work_evidence("ガンダム EB01", "", 1, 1, None, None,
                                 WORKS + [dict(WORKS[2], id="duplicate")]) is None
    assert resolve_work_evidence("ガンダム EB01", "", 1, 1, None, None,
                                 [dict(WORKS[2], alt_name="ガンダム|Gundam")]) is None


def test_work_constraint_does_not_fallback_or_resolve_code_only():
    kw = {"OP": ["EB01"], "NO_WORK": ["EB01"]}
    for work in ("gundam", None):
        result = match_pid_with_work("EB01", list(kw), kw, {}, work_id=work,
                                     product_work_ids={"OP": "onepiece"})
        assert result == (None, "NONE", False, [])
    assert match_pid_with_work("ワンピース EB01", list(kw), kw, {}, work_id="onepiece",
                               product_work_ids={"OP": "onepiece"})[0] == "OP"


def test_unknown_work_checks_all_matching_keywords():
    for kws in (["EB01", "メモリアルコレクション"], ["メモリアルコレクション", "EB01"]):
        result = match_pid_with_work("EB01 メモリアルコレクション", ["OP"], {"OP": kws}, {},
                                     work_id=None, product_work_ids={})
        assert result[0] == "OP" and result[2] is True
        assert "SK:メモリアルコレクション" in result[1]


@pytest.mark.parametrize("state,memo,excluded", [("PSA10", "", True), ("", "コロちゃお", True), ("", "", False)])
def test_exclusions_are_item_fields_only(state, memo, excluded):
    result = match_pid_with_work("スタートデッキ100", ["NORMAL"], {"NORMAL": ["スタートデッキ100"]},
                                 {"NORMAL": ["コロ", "PSA10"]}, work_id=None,
                                 product_work_ids={}, raw_state=state, raw_memo=memo)
    assert result[2] is not excluded


def test_and_exclusion_never_crosses_fields_and_memo_not_search_input():
    result = match_pid_with_work("スタートデッキ100 コロ", ["NORMAL"], {"NORMAL": ["スタートデッキ100"]},
                                 {"NORMAL": ["コロ 限定"]}, work_id=None,
                                 product_work_ids={}, raw_memo="限定")
    assert result[2] is True
    result = match_pid_with_work("不明", ["NORMAL"], {"NORMAL": ["スタートデッキ100"]}, {},
                                 work_id=None, product_work_ids={}, raw_memo="スタートデッキ100")
    assert result[2] is False


# A-phase saved design fixtures, captured 2026-09-13. Product labels/dictionaries
# only; no live DB/API reads. Before/after tuples are frozen design evidence.
# Snapshot SHA256: cfd70fede988b88802e703fd53afcde705b91e0cc1257c326e4e31c8b752c007
# Each row: code, title, work, search, exclusions, legacy tuple, A-phase tuple.
SPACE_SAVED_PRODUCTS = [('PM0001',
  'モンスターボールミラー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['モンスターボールミラー'],
  [],
  ('PM0001', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:モンスターボールミラー', True, ['PM0001']),
  ('PM0001', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:モンスターボールミラー', True, ['PM0001'])),
 ('PM0002',
  'RRカード',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['RR バルク'],
  ['CHR', 'RRR', 'SAR', 'SR', 'Sバルク'],
  (None, 'NONE', False, []),
  (None, 'NONE', False, [])),
 ('PM0003',
  'RRRカード',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['RRR バルク'],
  ['CHR', 'SAR', 'SR', 'Sバルク'],
  (None, 'NONE', False, []),
  (None, 'NONE', False, [])),
 ('PM0004',
  'Sカード',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['Sバルク'],
  ['CHR', 'RR', 'RRR', 'SAR', 'SR'],
  (None, 'NONE', False, []),
  (None, 'NONE', False, [])),
 ('PM0005',
  'SRカード',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['SRバルク'],
  ['CHR', 'RR', 'RRR', 'SAR', 'Sバルク'],
  (None, 'NONE', False, []),
  (None, 'NONE', False, [])),
 ('PM0006',
  'SARカード',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['SAR バルク'],
  ['CHR', 'RR', 'RRR', 'SR', 'Sバルク'],
  (None, 'NONE', False, []),
  (None, 'NONE', False, [])),
 ('PM0007',
  'AR/CHR ダブりなし',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['AR',
   'AR CHR バルク ダブりなし',
   'AR.CHR バルク ダブりなし',
   'AR/CHR バルク ダブりなし',
   'AR CHR バルク 被りなし',
   'AR.CHR バルク 被りなし',
   'AR/CHR バルク 被りなし',
   'CHR バルク ダブりなし',
   'CHR バルク 被りなし'],
  ['2枚', 'ダブりあり', '被りあり'],
  ('PM0007', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:AR', True, ['PM0007']),
  ('PM0007', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:AR', True, ['PM0007'])),
 ('PM0008',
  'AR/CHR ダブりあり',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['AR',
   'AR CHR バルク ダブりあり',
   'AR.CHR バルク ダブりあり',
   'AR/CHR バルク ダブりあり',
   'AR CHR バルク 被りあり',
   'AR.CHR バルク 被りあり',
   'AR/CHR バルク 被りあり',
   'CHR バルク ダブりあり',
   'CHR バルク 被りあり'],
  ['2枚', 'ダブりなし', '被りなし'],
  ('PM0008', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:AR', True, ['PM0008']),
  ('PM0008', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:AR', True, ['PM0008'])),
 ('PM0009',
  'AR/CHR ダブり2枚まで',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['AR',
   'AR.CHR バルク ダブり2枚まで',
   'AR/CHR バルク ダブり2枚まで',
   'AR CHR バルク 被り2枚まで',
   'AR.CHR バルク 被り2枚まで',
   'AR/CHR バルク 被り2枚まで',
   'CHR バルク 被り2枚まで'],
  ['ダブりあり', 'ダブりなし', '被りあり', '被りなし'],
  ('PM0009', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:AR', True, ['PM0009']),
  ('PM0009', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:AR', True, ['PM0009'])),
 ('PM0010',
  'ARカード ダブりなし',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['AR ダブりなし', 'AR ダブり無し', 'AR 被りなし', 'AR 被り無し'],
  ['CHR', 'ダブりあり', '被りあり'],
  ('PM0010',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0010/PM.PM0007):要確認',
   False,
   ['PM0010', 'PM0007']),
  ('PM0010',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0010/PM.PM0007):要確認',
   False,
   ['PM0010', 'PM0007'])),
 ('PM0011',
  'ARカード ダブりあり',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['AR ダブりあり', 'AR 被りあり'],
  ['CHR', 'ダブりなし', '被りなし'],
  ('PM0011',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0011/PM.PM0008):要確認',
   False,
   ['PM0011', 'PM0008']),
  ('PM0011',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0011/PM.PM0008):要確認',
   False,
   ['PM0011', 'PM0008'])),
 ('PM0012',
  'コレクションサン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['コレクション サン'],
  [],
  ('PM0012', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:コレクション サン', True, ['PM0012']),
  ('PM0012', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:コレクション サン', True, ['PM0012'])),
 ('PM0013',
  'コレクションムーン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['コレクション ムーン'],
  [],
  ('PM0013', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:コレクション ムーン', True, ['PM0013']),
  ('PM0013', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:コレクション ムーン', True, ['PM0013'])),
 ('PM0014',
  'サン&ムーン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['サン&ムーン'],
  [],
  ('PM0014', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:サン&ムーン', True, ['PM0014']),
  ('PM0014', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:サン&ムーン', True, ['PM0014'])),
 ('PM0015',
  'キミを待つ島々',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['キミを待つ島々'],
  [],
  ('PM0015', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:キミを待つ島々', True, ['PM0015']),
  ('PM0015', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:キミを待つ島々', True, ['PM0015'])),
 ('PM0016',
  'アローラの月光',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['アローラ 月光'],
  [],
  ('PM0016', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:アローラ 月光', True, ['PM0016']),
  ('PM0016', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:アローラ 月光', True, ['PM0016'])),
 ('PM0017',
  '新たなる試練の向こう',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['新たなる試練'],
  [],
  ('PM0017', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:新たなる試練', True, ['PM0017']),
  ('PM0017', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:新たなる試練', True, ['PM0017'])),
 ('PM0018',
  '光を喰らう闇',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['光を喰らう闇'],
  [],
  ('PM0018', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:光を喰らう闇', True, ['PM0018']),
  ('PM0018', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:光を喰らう闇', True, ['PM0018'])),
 ('PM0019',
  '闘う虹を見たか',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['闘う虹'],
  [],
  ('PM0019', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:闘う虹', True, ['PM0019']),
  ('PM0019', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:闘う虹', True, ['PM0019'])),
 ('PM0020',
  'ひかる伝説',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ひかる伝説'],
  [],
  ('PM0020', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ひかる伝説', True, ['PM0020']),
  ('PM0020', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ひかる伝説', True, ['PM0020'])),
 ('PM0021',
  '覚醒の勇者',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['覚醒の勇者'],
  [],
  ('PM0021', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:覚醒の勇者', True, ['PM0021']),
  ('PM0021', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:覚醒の勇者', True, ['PM0021'])),
 ('PM0022',
  '超次元の暴獣',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['超次元の暴獣'],
  [],
  ('PM0022', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:超次元の暴獣', True, ['PM0022']),
  ('PM0022', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:超次元の暴獣', True, ['PM0022'])),
 ('PM0023',
  'GXバトルブースト',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['バトルブースト'],
  [],
  ('PM0023', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バトルブースト', True, ['PM0023']),
  ('PM0023', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バトルブースト', True, ['PM0023'])),
 ('PM0024',
  'ウルトラサン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ウルトラサン'],
  [],
  ('PM0024', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ウルトラサン', True, ['PM0024']),
  ('PM0024', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ウルトラサン', True, ['PM0024'])),
 ('PM0025',
  'ウルトラムーン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ウルトラムーン'],
  [],
  ('PM0025', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ウルトラムーン', True, ['PM0025']),
  ('PM0025', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ウルトラムーン', True, ['PM0025'])),
 ('PM0026',
  'ウルトラフォース',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ウルトラフォース'],
  [],
  ('PM0026', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ウルトラフォース', True, ['PM0026']),
  ('PM0026', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ウルトラフォース', True, ['PM0026'])),
 ('PM0027',
  '禁断の光',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['禁断の光'],
  [],
  ('PM0027', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:禁断の光', True, ['PM0027']),
  ('PM0027', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:禁断の光', True, ['PM0027'])),
 ('PM0028',
  'ドラゴンストーム',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ドラゴンストーム'],
  [],
  ('PM0028', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ドラゴンストーム', True, ['PM0028']),
  ('PM0028', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ドラゴンストーム', True, ['PM0028'])),
 ('PM0029',
  'チャンピオンロード',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['チャンピオンロード'],
  [],
  ('PM0029', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:チャンピオンロード', True, ['PM0029']),
  ('PM0029', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:チャンピオンロード', True, ['PM0029'])),
 ('PM0030',
  '裂空のカリスマ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['裂空のカリスマ'],
  [],
  ('PM0030', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:裂空のカリスマ', True, ['PM0030']),
  ('PM0030', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:裂空のカリスマ', True, ['PM0030'])),
 ('PM0031',
  '迅雷スパーク',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['迅雷スパーク'],
  [],
  ('PM0031', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:迅雷スパーク', True, ['PM0031']),
  ('PM0031', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:迅雷スパーク', True, ['PM0031'])),
 ('PM0032',
  'フェアリーライズ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['フェアリーライズ'],
  [],
  ('PM0032', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:フェアリーライズ', True, ['PM0032']),
  ('PM0032', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:フェアリーライズ', True, ['PM0032'])),
 ('PM0033',
  '超爆インパクト',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['超爆インパクト'],
  [],
  ('PM0033', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:超爆インパクト', True, ['PM0033']),
  ('PM0033', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:超爆インパクト', True, ['PM0033'])),
 ('PM0034',
  'ダークオーダー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ダークオーダー'],
  [],
  ('PM0034', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ダークオーダー', True, ['PM0034']),
  ('PM0034', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ダークオーダー', True, ['PM0034'])),
 ('PM0035',
  'GXウルトラシャイニー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ウルトラシャイニー'],
  [],
  ('PM0035', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ウルトラシャイニー', True, ['PM0035']),
  ('PM0035', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ウルトラシャイニー', True, ['PM0035'])),
 ('PM0036',
  'ナイトユニゾン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ナイトユニゾン'],
  [],
  ('PM0036', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ナイトユニゾン', True, ['PM0036']),
  ('PM0036', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ナイトユニゾン', True, ['PM0036'])),
 ('PM0037',
  'フルメタルウォール',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['フルメタルウォール'],
  [],
  ('PM0037', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:フルメタルウォール', True, ['PM0037']),
  ('PM0037', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:フルメタルウォール', True, ['PM0037'])),
 ('PM0038',
  'ダブルブレイズ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ダブルブレイズ'],
  [],
  ('PM0038', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ダブルブレイズ', True, ['PM0038']),
  ('PM0038', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ダブルブレイズ', True, ['PM0038'])),
 ('PM0039',
  'ジージーエンド',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ジージーエンド'],
  [],
  ('PM0039', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ジージーエンド', True, ['PM0039']),
  ('PM0039', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ジージーエンド', True, ['PM0039'])),
 ('PM0040',
  '名探偵ピカチュウ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['名探偵ピカチュウ'],
  ['プロモ'],
  ('PM0040', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:名探偵ピカチュウ', True, ['PM0040']),
  ('PM0040', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:名探偵ピカチュウ', True, ['PM0040'])),
 ('PM0041',
  'スカイレジェンド',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スカイレジェンド'],
  [],
  ('PM0041', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スカイレジェンド', True, ['PM0041']),
  ('PM0041', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スカイレジェンド', True, ['PM0041'])),
 ('PM0042',
  'ミラクルツイン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ミラクルツイン'],
  [],
  ('PM0042', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ミラクルツイン', True, ['PM0042']),
  ('PM0042', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ミラクルツイン', True, ['PM0042'])),
 ('PM0043',
  'リミックスバウト',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['リミックスバウト'],
  [],
  ('PM0043', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:リミックスバウト', True, ['PM0043']),
  ('PM0043', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:リミックスバウト', True, ['PM0043'])),
 ('PM0044',
  'ドリームリーグ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ドリームリーグ'],
  [],
  ('PM0044', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ドリームリーグ', True, ['PM0044']),
  ('PM0044', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ドリームリーグ', True, ['PM0044'])),
 ('PM0045',
  'オルタージェネシス',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['オルタージェネシス'],
  [],
  ('PM0045', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:オルタージェネシス', True, ['PM0045']),
  ('PM0045', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:オルタージェネシス', True, ['PM0045'])),
 ('PM0046',
  'TAG TEAM GX タッグオールスターズ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['タッグオールスター', 'タッグオールスターズ'],
  [],
  ('PM0046', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:タッグオールスター', True, ['PM0046']),
  ('PM0046', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:タッグオールスター', True, ['PM0046'])),
 ('PM0047',
  'ソード',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ソード'],
  ['シールド', 'プレシャス'],
  ('PM0047', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ソード', True, ['PM0047']),
  ('PM0047', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ソード', True, ['PM0047'])),
 ('PM0048',
  'シールド',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['シールド'],
  ['プレシャス'],
  ('PM0048', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:シールド', True, ['PM0048']),
  ('PM0048', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:シールド', True, ['PM0048'])),
 ('PM0049',
  'VMAXライジング',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['VMAXライジング'],
  [],
  ('PM0049',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0049/PM.PM0074):要確認',
   False,
   ['PM0049', 'PM0074']),
  ('PM0049',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0049/PM.PM0074):要確認',
   False,
   ['PM0049', 'PM0074'])),
 ('PM0050',
  '反逆クラッシュ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['反逆クラッシュ'],
  [],
  ('PM0050', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:反逆クラッシュ', True, ['PM0050']),
  ('PM0050', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:反逆クラッシュ', True, ['PM0050'])),
 ('PM0051',
  '爆炎ウォーカー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['爆炎ウォーカー'],
  [],
  ('PM0051', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:爆炎ウォーカー', True, ['PM0051']),
  ('PM0051', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:爆炎ウォーカー', True, ['PM0051'])),
 ('PM0052',
  'ムゲンゾーン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ムゲンゾーン'],
  [],
  ('PM0052', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ムゲンゾーン', True, ['PM0052']),
  ('PM0052', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ムゲンゾーン', True, ['PM0052'])),
 ('PM0053',
  '伝説の鼓動',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['伝説の鼓動'],
  [],
  ('PM0053', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:伝説の鼓動', True, ['PM0053']),
  ('PM0053', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:伝説の鼓動', True, ['PM0053'])),
 ('PM0054',
  '仰天のボルテッカー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['仰天', '仰天ボルテッカー'],
  [],
  ('PM0054', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:仰天', True, ['PM0054']),
  ('PM0054', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:仰天', True, ['PM0054'])),
 ('PM0055',
  'シャイニースターV',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['shiny v box', 'シャイニースター'],
  [],
  ('PM0055', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:シャイニースター', True, ['PM0055']),
  ('PM0055', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:シャイニースター', True, ['PM0055'])),
 ('PM0056',
  'スペシャルBOX ポケモンセンターカナザワオープン記念',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カナザワ', 'スペシャルBOX カナザワ', 'スペシャルBOX ポケセン', 'スペシャルボックス カナザワ'],
  ['トウホク', 'ヒロシマ', 'フクオカ'],
  ('PM0056', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:カナザワ', True, ['PM0056']),
  ('PM0056', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:カナザワ', True, ['PM0056'])),
 ('PM0057',
  '連撃マスター',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['連撃マスター'],
  [],
  ('PM0057', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:連撃マスター', True, ['PM0057']),
  ('PM0057', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:連撃マスター', True, ['PM0057'])),
 ('PM0058',
  '一撃マスター',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['一撃マスター'],
  [],
  ('PM0058', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:一撃マスター', True, ['PM0058']),
  ('PM0058', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:一撃マスター', True, ['PM0058'])),
 ('PM0059',
  '双璧のファイター',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['双璧'],
  ['覇者'],
  ('PM0059', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:双璧', True, ['PM0059']),
  ('PM0059', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:双璧', True, ['PM0059'])),
 ('PM0060',
  '白銀のランス',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['白銀'],
  [],
  ('PM0060', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:白銀', True, ['PM0060']),
  ('PM0060', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:白銀', True, ['PM0060'])),
 ('PM0061',
  '漆黒のガイスト',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['漆黒'],
  [],
  ('PM0061', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:漆黒', True, ['PM0061']),
  ('PM0061', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:漆黒', True, ['PM0061'])),
 ('PM0062',
  'イーブイヒーローズ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['イーブイヒーローズ'],
  ['イーブイズセット'],
  ('PM0062', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:イーブイヒーローズ', True, ['PM0062']),
  ('PM0062', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:イーブイヒーローズ', True, ['PM0062'])),
 ('PM0063',
  'イーブイヒーローズ イーブイズセット',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['イーブイズセット', 'イーブイヒーローズ イーブイズセット', 'イーブイヒーローズイーブイズセット'],
  [],
  ('PM0063', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:イーブイズセット', True, ['PM0063']),
  ('PM0063', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:イーブイズセット', True, ['PM0063'])),
 ('PM0064',
  'ハイクラスデッキ ゲンガーVMAX',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ハイクラスデッキ ゲンガーVMAX'],
  ['インテレオンVMAX'],
  ('PM0064',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0064/PM.PM0074):要確認',
   False,
   ['PM0064', 'PM0074']),
  ('PM0064',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0064/PM.PM0074):要確認',
   False,
   ['PM0064', 'PM0074'])),
 ('PM0065',
  'ハイクラスデッキ インテレオンVMAX',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ハイクラスデッキ インテレオンVMAX'],
  ['ゲンガーVMAX'],
  ('PM0065',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0065/PM.PM0074):要確認',
   False,
   ['PM0065', 'PM0074']),
  ('PM0065',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0065/PM.PM0074):要確認',
   False,
   ['PM0065', 'PM0074'])),
 ('PM0066',
  'ハイクラスデッキダブルBOX ゲンガーVMAX＆インテレオンVMAX',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ハイクラスデッキダブルBOX ゲンガーVMAX＆インテレオンVMAX', 'ハイクラスデッキダブルボックス'],
  [],
  ('PM0066',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0066/PM.PM0074):要確認',
   False,
   ['PM0066', 'PM0074']),
  ('PM0066',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0066/PM.PM0074):要確認',
   False,
   ['PM0066', 'PM0074'])),
 ('PM0067',
  '蒼空ストリーム',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['蒼空'],
  [],
  ('PM0067', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:蒼空', True, ['PM0067']),
  ('PM0067', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:蒼空', True, ['PM0067'])),
 ('PM0068',
  '摩天パーフェクト',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['摩天'],
  [],
  ('PM0068', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:摩天', True, ['PM0068']),
  ('PM0068', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:摩天', True, ['PM0068'])),
 ('PM0069',
  'ポケモン切手BOX',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['切手', '切手Box', '切手BOX'],
  [],
  ('PM0069', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:切手', True, ['PM0069']),
  ('PM0069', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:切手', True, ['PM0069'])),
 ('PM0070',
  'フュージョンアーツ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['フュージョンアーツ'],
  [],
  ('PM0070', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:フュージョンアーツ', True, ['PM0070']),
  ('PM0070', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:フュージョンアーツ', True, ['PM0070'])),
 ('PM0071',
  '25th Anniversary Collection',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['25th Anniversary Collection', '25thANNIVERSARYCOLLECTION'],
  ['25th Aniniversary Golden Box',
   '25th Anniversary Collection プロモ',
   '25th Anniversary Collection プロモパック',
   'プロモパック'],
  ('PM0071', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:25th Anniversary Collection', True, ['PM0071']),
  ('PM0071', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:25th Anniversary Collection', True, ['PM0071'])),
 ('PM0072',
  '25th Anniversary Collection プロモパック',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['25th Anniversary Collection プロモ',
   '25th Anniversary Collection プロモパック',
   '25th アニバーサリー プロモパック',
   '25thプロモパック'],
  ['25th Golden Box'],
  ('PM0072',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:25th Anniversary Collection プロモ',
   True,
   ['PM0072']),
  ('PM0072',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:25th Anniversary Collection プロモ',
   True,
   ['PM0072'])),
 ('PM0073',
  '25th Aniniversary Golden Box',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['25th Aniniversary Golden Box', '25th Goleen Box', 'ゴールデンボックス'],
  ['25th Anniversary Collection'],
  ('PM0073', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:25th Aniniversary Golden Box', True, ['PM0073']),
  ('PM0073', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:25th Aniniversary Golden Box', True, ['PM0073'])),
 ('PM0074',
  'VMAXクライマックス',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['VMAX'],
  [],
  ('PM0074', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:VMAX', True, ['PM0074']),
  ('PM0074', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:VMAX', True, ['PM0074'])),
 ('PM0075',
  'スターバース',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スターバース'],
  [],
  ('PM0075', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スターバース', True, ['PM0075']),
  ('PM0075', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スターバース', True, ['PM0075'])),
 ('PM0076',
  'バトルリージョン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['バトルリージョン'],
  [],
  ('PM0076', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バトルリージョン', True, ['PM0076']),
  ('PM0076', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バトルリージョン', True, ['PM0076'])),
 ('PM0077',
  'スペースジャグラー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スペースジャグラー'],
  [],
  ('PM0077', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スペースジャグラー', True, ['PM0077']),
  ('PM0077', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スペースジャグラー', True, ['PM0077'])),
 ('PM0078',
  'タイムゲイザー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['タイムゲイザ-', 'タイムゲイザー'],
  [],
  ('PM0078', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:タイムゲイザー', True, ['PM0078']),
  ('PM0078', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:タイムゲイザー', True, ['PM0078'])),
 ('PM0079',
  'ダークファンタズマ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ダークファンタズマ'],
  [],
  ('PM0079', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ダークファンタズマ', True, ['PM0079']),
  ('PM0079', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ダークファンタズマ', True, ['PM0079'])),
 ('PM0080',
  'Pokemon GO',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['Pokemon GO', 'ポケモン GO', 'ポケモンGO'],
  [],
  ('PM0080', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:Pokemon GO', True, ['PM0080']),
  ('PM0080', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:Pokemon GO', True, ['PM0080'])),
 ('PM0081',
  'ロストアビス',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ロストアビス'],
  [],
  ('PM0081', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ロストアビス', True, ['PM0081']),
  ('PM0081', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ロストアビス', True, ['PM0081'])),
 ('PM0082',
  'ROMANCE DAWN',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-01', 'OP01', 'ROMANCE DAWN', 'ROMANCE DAWN OP-01', 'ロマンスドーン'],
  [],
  ('PM0082', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:ROMANCE DAWN', True, ['PM0082']),
  ('PM0082', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:ROMANCE DAWN', True, ['PM0082'])),
 ('PM0083',
  '白熱のアルカナ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['白熱'],
  [],
  ('PM0083', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:白熱', True, ['PM0083']),
  ('PM0083', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:白熱', True, ['PM0083'])),
 ('PM0084',
  'パラダイムトリガー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['パラダイムトリガー'],
  [],
  ('PM0084', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:パラダイムトリガー', True, ['PM0084']),
  ('PM0084', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:パラダイムトリガー', True, ['PM0084'])),
 ('PM0085',
  '頂上決戦',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-02', 'OP02', '頂上決戦', '頂上決戦 OP-02'],
  [],
  ('PM0085', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:頂上決戦', True, ['PM0085']),
  ('PM0085', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:頂上決戦', True, ['PM0085'])),
 ('PM0086',
  'プレシャス コレクターボックス ソード&シールド',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['プレシャスコレクターBOX', 'プレシャスコレクターボック', 'プレシャス コレクターボックス', 'プレシャスコレクターボックス', 'プレシャスコレクターボックス ソード&シールド'],
  [],
  ('PM0086', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:プレシャス コレクターボックス', True, ['PM0086']),
  ('PM0086', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:プレシャス コレクターボックス', True, ['PM0086'])),
 ('PM0087',
  'VSTARユニバース',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['VSTAR', 'VSTARユニバース'],
  [],
  ('PM0087', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:VSTAR', True, ['PM0087']),
  ('PM0087', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:VSTAR', True, ['PM0087'])),
 ('PM0088',
  'スカーレットex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スカーレット'],
  [],
  ('PM0088', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スカーレット', True, ['PM0088']),
  ('PM0088', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スカーレット', True, ['PM0088'])),
 ('PM0089',
  'バイオレットex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['バイオレット'],
  [],
  ('PM0089', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バイオレット', True, ['PM0089']),
  ('PM0089', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バイオレット', True, ['PM0089'])),
 ('PM0090',
  'スターターセットex ニャオハ＆ルカリオex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ニャオハ＆ルカリオ', 'ニャオハ＆ルカリオex'],
  [],
  ('PM0274',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0274/PM.PM0090):要確認',
   False,
   ['PM0274', 'PM0090']),
  ('PM0274',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0274/PM.PM0090):要確認',
   False,
   ['PM0274', 'PM0090'])),
 ('PM0091',
  'スターターセットex ホゲータ＆デンリュウex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ホゲータ＆デンリュウ', 'ホゲータ＆デンリュウex'],
  [],
  ('PM0091', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ホゲータ＆デンリュウ', True, ['PM0091']),
  ('PM0091', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ホゲータ＆デンリュウ', True, ['PM0091'])),
 ('PM0092',
  'スターターセットex クワッス＆ミミッキュex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['クワッス＆ミミッキュ', 'クワッス＆ミミッキュex'],
  [],
  ('PM0092', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:クワッス＆ミミッキュ', True, ['PM0092']),
  ('PM0092', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:クワッス＆ミミッキュ', True, ['PM0092'])),
 ('PM0093',
  'プレミアムトレーナーボックスex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['プレミアムトレーナーボックスex'],
  [],
  ('PM0093', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:プレミアムトレーナーボックスex', True, ['PM0093']),
  ('PM0093', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:プレミアムトレーナーボックスex', True, ['PM0093'])),
 ('PM0094',
  '強大な敵',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-03', 'OP03', '強大な敵', '強大な敵 OP-03'],
  [],
  ('PM0094', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:強大な敵', True, ['PM0094']),
  ('PM0094', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:強大な敵', True, ['PM0094'])),
 ('PM0095',
  'トリプレットビート',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['トリプレットビート'],
  [],
  ('PM0095', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:トリプレットビート', True, ['PM0095']),
  ('PM0095', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:トリプレットビート', True, ['PM0095'])),
 ('PM0096',
  'スターターセットex ピカチュウex＆パーモット',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ピカチュウex＆パーモット', 'ピカチュウex＆パーモットex'],
  [],
  ('PM0096', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ピカチュウex＆パーモット', True, ['PM0096']),
  ('PM0096', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ピカチュウex＆パーモット', True, ['PM0096'])),
 ('PM0097',
  'スノーハザード',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スノーハザード'],
  ['&クレイバースト', 'ジムセット', 'ポケセン', 'ポケモンセンター'],
  ('PM0097', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スノーハザード', True, ['PM0097']),
  ('PM0097', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スノーハザード', True, ['PM0097'])),
 ('PM0098',
  'クレイバースト',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['クレイバースト'],
  ['ジムセット', 'ポケセン', 'ポケモンセンター'],
  ('PM0098', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:クレイバースト', True, ['PM0098']),
  ('PM0098', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:クレイバースト', True, ['PM0098'])),
 ('PM0099',
  'スノーハザード&クレイバースト ポケモンセンター・ジムセット',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スノーハザード&クレイバースト ジムセット', 'スノーハザード&クレイバースト ポケセン', 'スノーハザード&クレイバースト ポケモンセンター'],
  [],
  ('PM0099', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スノーハザード&クレイバースト ジムセット', True, ['PM0099']),
  ('PM0099', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スノーハザード&クレイバースト ジムセット', True, ['PM0099'])),
 ('PM0100',
  'exスペシャルセット',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスペシャルセット'],
  [],
  ('PM0100', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:exスペシャルセット', True, ['PM0100']),
  ('PM0100', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:exスペシャルセット', True, ['PM0100'])),
 ('PM0101',
  '長場 ピカチュウ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['NAGABA ピカチュウ', 'NAGABAピカチュウ', '長場 ピカチュウ', '長場ピカチュウ', '長場 ピカチュウプロモ'],
  ['PSA10', 'イーブイ'],
  ('PM0101', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:長場 ピカチュウ', True, ['PM0101']),
  ('PM0101', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:長場 ピカチュウ', True, ['PM0101'])),
 ('PM0102',
  '長場 イーブイ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['NAGABA イーブイ', 'NAGABAイーブイズプロモパック', '長場 イーブイ', '長場イーブイ', '長場 イーブイプロモ'],
  ['PSA10', 'ピカチュウ'],
  ('PM0102', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:長場 イーブイ', True, ['PM0102']),
  ('PM0102', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:長場 イーブイ', True, ['PM0102'])),
 ('PM0103',
  '謀略の王国',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-04', 'OP04', '謀略の王国', '謀略の王国 OP-04'],
  [],
  ('PM0103', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:謀略の王国', True, ['PM0103']),
  ('PM0103', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:謀略の王国', True, ['PM0103'])),
 ('PM0104',
  'ポケモンカード151',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['151', 'ポケモンカード151'],
  ['fat', 'hope', 'journey', 'jumbo', 'slim', 'surprised', 'vol.3', 'マスターボールミラー', '収集啦', '礼盒'],
  ('PM0104', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:151', True, ['PM0104']),
  ('PM0104', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:151', True, ['PM0104'])),
 ('PM0105',
  '黒炎の支配者',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['黒炎'],
  ['デッキビルド', 'デッキビルドBOX 黒炎の支配者'],
  ('PM0105', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:黒炎', True, ['PM0105']),
  ('PM0105', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:黒炎', True, ['PM0105'])),
 ('PM0106',
  'ポケモンワールドチャンピオンシップス2023横浜 記念デッキ ピカチュウ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ワールドチャンピオンシップス2023横浜', '横浜 記念デッキ', '横浜 記念デッキ ピカチュウ'],
  [],
  ('PM0106', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ワールドチャンピオンシップス2023横浜', True, ['PM0106']),
  ('PM0106', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ワールドチャンピオンシップス2023横浜', True, ['PM0106'])),
 ('PM0107',
  'デッキビルドBOX 黒炎の支配者',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['デッキビルド 黒炎の支配者'],
  [],
  ('PM0107', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:デッキビルド 黒炎の支配者', True, ['PM0107']),
  ('PM0107', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:デッキビルド 黒炎の支配者', True, ['PM0107'])),
 ('PM0108',
  'TANTO プロモカードパック',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['TANTO プロモ', 'TANTOプロモカードパック', 'TANTO プロモパック'],
  ['PSA10'],
  ('PM0108', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:TANTO プロモ', True, ['PM0108']),
  ('PM0108', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:TANTO プロモ', True, ['PM0108'])),
 ('PM0109',
  'レイジングサーフ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['レイジングサーフ'],
  [],
  ('PM0109', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:レイジングサーフ', True, ['PM0109']),
  ('PM0109', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:レイジングサーフ', True, ['PM0109'])),
 ('PM0110',
  'スターターセット テラスタル ミュウツーex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ミュウツーex'],
  [],
  ('PM0110', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ミュウツーex', True, ['PM0110']),
  ('PM0110', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ミュウツーex', True, ['PM0110'])),
 ('PM0111',
  'スターターセット テラスタル ラウドボーンex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ラウドボーンex'],
  [],
  ('PM0111', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ラウドボーンex', True, ['PM0111']),
  ('PM0111', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ラウドボーンex', True, ['PM0111'])),
 ('PM0112',
  '名探偵ピカチュウ プロモ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['名探偵ピカチュウ プロモ', '名探偵ピカチュウプロモ'],
  ['Box', 'PSA10'],
  ('PM0112', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:名探偵ピカチュウ プロモ', True, ['PM0112']),
  ('PM0112', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:名探偵ピカチュウ プロモ', True, ['PM0112'])),
 ('PM0113',
  '古代の咆哮',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['古代の咆哮'],
  [],
  ('PM0113', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:古代の咆哮', True, ['PM0113']),
  ('PM0113', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:古代の咆哮', True, ['PM0113'])),
 ('PM0114',
  '未来の一閃',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['未来の一閃'],
  [],
  ('PM0114', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:未来の一閃', True, ['PM0114']),
  ('PM0114', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:未来の一閃', True, ['PM0114'])),
 ('PM0115',
  'スペシャルデッキセットex フシギバナ・リザードン・カメックス',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スペシャルデッキセットex'],
  ['PSA'],
  ('PM0115', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スペシャルデッキセットex', True, ['PM0115']),
  ('PM0115', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スペシャルデッキセットex', True, ['PM0115'])),
 ('PM0116',
  'ポケモンカードゲーム Classic',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['Classic', 'クラシック', 'クラシック Classic', 'ポケモン Classic', 'ポケモンカード Classic', 'ポケモンカード クラシック', 'ポケモンクラシック'],
  [],
  ('PM0116', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:Classic', True, ['PM0116']),
  ('PM0116', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:Classic', True, ['PM0116'])),
 ('PM0117',
  'シャイニートレジャーex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['shiny treasures', 'シャイニートレジャー'],
  [],
  ('PM0117', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:シャイニートレジャー', True, ['PM0117']),
  ('PM0117', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:シャイニートレジャー', True, ['PM0117'])),
 ('PM0118',
  '新時代の主役',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-05', 'OP05', '新時代の主役', '新時代の主役 OP-05'],
  [],
  ('PM0118', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:新時代の主役', True, ['PM0118']),
  ('PM0118', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:新時代の主役', True, ['PM0118'])),
 ('PM0119',
  'サイバージャッジ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['サイバージャッジ'],
  [],
  ('PM0119', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:サイバージャッジ', True, ['PM0119']),
  ('PM0119', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:サイバージャッジ', True, ['PM0119'])),
 ('PM0120',
  'ワイルドフォース',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ワイルドフォース'],
  [],
  ('PM0120', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ワイルドフォース', True, ['PM0120']),
  ('PM0120', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ワイルドフォース', True, ['PM0120'])),
 ('PM0121',
  'スターターデッキ＆ビルドセット 古代のコライドンex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['古代のコライドンex'],
  [],
  ('PM0121', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:古代のコライドンex', True, ['PM0121']),
  ('PM0121', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:古代のコライドンex', True, ['PM0121'])),
 ('PM0122',
  'スターターデッキ＆ビルドセット 未来のミライドンex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['未来のミライドンex'],
  [],
  ('PM0122', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:未来のミライドンex', True, ['PM0122']),
  ('PM0122', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:未来のミライドンex', True, ['PM0122'])),
 ('PM0123',
  'メモリアルコレクション',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['EB-01', 'EB01', 'メモリアルコレクション'],
  [],
  ('PM0123', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:メモリアルコレクション', True, ['PM0123']),
  ('PM0123', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:メモリアルコレクション', True, ['PM0123'])),
 ('PM0124',
  '覚醒の鼓動',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['FB-01', 'FB01', '覚醒の鼓動'],
  [],
  ('PM0124', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:覚醒の鼓動', True, ['PM0124']),
  ('PM0124', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:覚醒の鼓動', True, ['PM0124'])),
 ('PM0125',
  'バトルアカデミー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['バトルアカデミー'],
  ['いつでもどこでも'],
  ('PM0125', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バトルアカデミー', True, ['PM0125']),
  ('PM0125', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バトルアカデミー', True, ['PM0125'])),
 ('PM0126',
  'いつでもどこでもバトルアカデミー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['いつでもどこでも'],
  [],
  ('PM0126', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:いつでもどこでも', True, ['PM0126']),
  ('PM0126', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:いつでもどこでも', True, ['PM0126'])),
 ('PM0127',
  '双璧の覇者',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-06', 'OP06', '双璧の覇者', '双璧の覇者 OP-06'],
  ['ファイター'],
  ('PM0127', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:双璧の覇者', True, ['PM0127']),
  ('PM0127', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:双璧の覇者', True, ['PM0127'])),
 ('PM0128',
  'クリムゾンヘイズ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['クリムゾンヘイズ'],
  [],
  ('PM0128', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:クリムゾンヘイズ', True, ['PM0128']),
  ('PM0128', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:クリムゾンヘイズ', True, ['PM0128'])),
 ('PM0129',
  '変幻の仮面',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['変幻の仮面'],
  ['オーガポン'],
  ('PM0129', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:変幻の仮面', True, ['PM0129']),
  ('PM0129', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:変幻の仮面', True, ['PM0129'])),
 ('PM0130',
  '烈火の闘気',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['FB-02', 'FB02', '烈火の闘気'],
  [],
  ('PM0130', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:烈火の闘気', True, ['PM0130']),
  ('PM0130', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:烈火の闘気', True, ['PM0130'])),
 ('PM0131',
  'バトルマスターデッキ テラスタル リザードンex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['リザードンex'],
  [],
  ('PM0131', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:リザードンex', True, ['PM0131']),
  ('PM0131', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:リザードンex', True, ['PM0131'])),
 ('PM0132',
  'バトルマスターデッキ パオジアンex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['パオジアンex'],
  [],
  ('PM0132', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:パオジアンex', True, ['PM0132']),
  ('PM0132', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:パオジアンex', True, ['PM0132'])),
 ('PM0133',
  'ナイトワンダラー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ナイトワンダラー'],
  [],
  ('PM0133', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ナイトワンダラー', True, ['PM0133']),
  ('PM0133', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ナイトワンダラー', True, ['PM0133'])),
 ('PM0134',
  '500年後の未来',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['500年後の未来', '500年後の未来 OP-07', 'OP-07', 'OP07'],
  [],
  ('PM0134', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:500年後の未来', True, ['PM0134']),
  ('PM0134', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:500年後の未来', True, ['PM0134'])),
 ('PM0135',
  'ステラミラクル',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ステラミラクル'],
  ['デッキビルド', 'デッキビルドBOX ステラミラクル'],
  ('PM0135', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ステラミラクル', True, ['PM0135']),
  ('PM0135', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ステラミラクル', True, ['PM0135'])),
 ('PM0136',
  'デッキビルドBOX ステラミラクル',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['デッキビルド ステラミラクル'],
  [],
  ('PM0136', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:デッキビルド ステラミラクル', True, ['PM0136']),
  ('PM0136', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:デッキビルド ステラミラクル', True, ['PM0136'])),
 ('PM0137',
  'THE BEST',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['ONE PIECE CARD THE BEST', 'PRB-01', 'PRB01', 'THE BEST', 'THE BEST PRB-01', 'ワンピース THE BEST'],
  ['OF XY', 'PRB-02', 'PRB02', 'vol.2', 'ストレージ'],
  ('PM0137', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:THE BEST', True, ['PM0137']),
  ('PM0137', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:THE BEST', True, ['PM0137'])),
 ('PM0138',
  '怒りの咆哮',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['FB-03', 'FB03', '怒りの咆哮'],
  [],
  ('PM0138', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:怒りの咆哮', True, ['PM0138']),
  ('PM0138', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:怒りの咆哮', True, ['PM0138'])),
 ('PM0139',
  'スターターセット テラスタイプ：ステラ ニンフィアex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ニンフィアex'],
  [],
  ('PM0139', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ニンフィアex', True, ['PM0139']),
  ('PM0139', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ニンフィアex', True, ['PM0139'])),
 ('PM0140',
  'スターターセット テラスタイプ：ステラ ソウブレイズex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ソウブレイズex'],
  [],
  ('PM0140', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ソウブレイズex', True, ['PM0140']),
  ('PM0140', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ソウブレイズex', True, ['PM0140'])),
 ('PM0141',
  '新たなる皇帝',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-09', 'OP09', '新たなる皇帝', '新たなる皇帝 OP-09'],
  [],
  ('PM0141', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:新たなる皇帝', True, ['PM0141']),
  ('PM0141', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:新たなる皇帝', True, ['PM0141'])),
 ('PM0142',
  '楽園ドラゴーナ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['楽園'],
  [],
  ('PM0142', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:楽園', True, ['PM0142']),
  ('PM0142', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:楽園', True, ['PM0142'])),
 ('PM0143',
  '二つの伝説',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-08', 'OP08', '二つの伝説', '二つの伝説 OP-08'],
  [],
  ('PM0143', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:二つの伝説', True, ['PM0143']),
  ('PM0143', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:二つの伝説', True, ['PM0143'])),
 ('PM0144',
  '超電ブレイカー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['超電'],
  [],
  ('PM0144', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:超電', True, ['PM0144']),
  ('PM0144', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:超電', True, ['PM0144'])),
 ('PM0145',
  '限界を超えし者',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['FB-04', 'FB04', '限界を超えし者'],
  [],
  ('PM0145', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:限界を超えし者', True, ['PM0145']),
  ('PM0145', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:限界を超えし者', True, ['PM0145'])),
 ('PM0147',
  'テラスタルフェスex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['テラスタルフェス'],
  [],
  ('PM0147', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:テラスタルフェス', True, ['PM0147']),
  ('PM0147', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:テラスタルフェス', True, ['PM0147'])),
 ('PM0148',
  'バトルパートナーズ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['バトルパートナーズ'],
  ['デッキビルド', 'デッキビルドBOX バトルパートナーズ'],
  ('PM0148', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バトルパートナーズ', True, ['PM0148']),
  ('PM0148', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:バトルパートナーズ', True, ['PM0148'])),
 ('PM0149',
  'ナンジャモ プロモ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ナンジャモ プロモ', 'ナンジャモプロモ'],
  ['PSA10'],
  ('PM0149', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ナンジャモ プロモ', True, ['PM0149']),
  ('PM0149', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ナンジャモ プロモ', True, ['PM0149'])),
 ('PM0150',
  'デッキビルドBOX バトルパートナーズ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['デッキビルド バトルパートナーズ'],
  [],
  ('PM0150', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:デッキビルド バトルパートナーズ', True, ['PM0150']),
  ('PM0150', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:デッキビルド バトルパートナーズ', True, ['PM0150'])),
 ('PM0151',
  'コレクションファイルセット N',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['コレクションファイルセット N', 'コレクションファイルセットN', 'ファイルセットN'],
  ['コレクションファイルセットリーリエ', 'ファイルセット リーリエ'],
  ('PM0151', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:コレクションファイルセット N', True, ['PM0151']),
  ('PM0151', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:コレクションファイルセット N', True, ['PM0151'])),
 ('PM0152',
  'コレクションファイルセット リーリエ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['コレクションファイルセットリーリエ', 'コレクションファイルリーリエ', 'ファイルセット リーリエ'],
  ['コレクションファイルセットN', 'ファイルセットN'],
  ('PM0152', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ファイルセット リーリエ', True, ['PM0152']),
  ('PM0152', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ファイルセット リーリエ', True, ['PM0152'])),
 ('PM0153',
  'Anime25th collection',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['Anime25th collection',
   'Anime25th collection EB-02',
   'EB-02',
   'EB02',
   'エクストラブースター Anime25th collection EB-02'],
  [],
  ('PM0153', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:Anime25th collection', True, ['PM0153']),
  ('PM0153', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:Anime25th collection', True, ['PM0153'])),
 ('PM0154',
  '未知なる冒険',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['FB-05', 'FB05', '未知なる冒険'],
  [],
  ('PM0154', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:未知なる冒険', True, ['PM0154']),
  ('PM0154', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:未知なる冒険', True, ['PM0154'])),
 ('PM0155',
  'スターターセットex マリィのモルペコ＆オーロンゲex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['マリィのモルペコ＆オーロンゲ', 'マリィのモルペコ＆オーロンゲex'],
  [],
  ('PM0155', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:マリィのモルペコ＆オーロンゲ', True, ['PM0155']),
  ('PM0155', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:マリィのモルペコ＆オーロンゲ', True, ['PM0155'])),
 ('PM0156',
  'スターターセットex ダイゴのダンバル＆メタグロスex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ダイゴのダンバル&メタグロス', 'ダイゴのダンバル&メタグロスex'],
  [],
  ('PM0156', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ダイゴのダンバル&メタグロス', True, ['PM0156']),
  ('PM0156', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ダイゴのダンバル&メタグロス', True, ['PM0156'])),
 ('PM0157',
  '神速の拳',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-11', 'OP11', '神速の拳', '神速の拳  OP-11'],
  [],
  ('PM0157', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:神速の拳', True, ['PM0157']),
  ('PM0157', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:神速の拳', True, ['PM0157'])),
 ('PM0158',
  '熱風のアリーナ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['熱風'],
  ['プロモ', '熱風のアリーナ プロモ'],
  ('PM0158', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:熱風', True, ['PM0158']),
  ('PM0158', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:熱風', True, ['PM0158'])),
 ('PM0159',
  '熱風のアリーナ プロモ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['熱風アリーナ プロモ', '熱風のアリーナ プロモ', '熱風 プロモ'],
  ['Box'],
  ('PM0159', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:熱風のアリーナ プロモ', True, ['PM0159']),
  ('PM0159', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:熱風のアリーナ プロモ', True, ['PM0159'])),
 ('PM0160',
  '王族の血統',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-10', 'OP10', '王族の血統', '王族の血統  OP-10'],
  ['師弟の絆'],
  ('PM0160', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:王族の血統', True, ['PM0160']),
  ('PM0160', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:王族の血統', True, ['PM0160'])),
 ('PM0161',
  'ロケット団の栄光',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ロケット団', 'ロケット団の栄光'],
  ['アタッシュケース'],
  ('PM0161', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ロケット団', True, ['PM0161']),
  ('PM0161', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ロケット団', True, ['PM0161'])),
 ('PM0162',
  'ゆずソフト',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['ゆずソフト'],
  [],
  ('PM0162', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:ゆずソフト', True, ['PM0162']),
  ('PM0162', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:ゆずソフト', True, ['PM0162'])),
 ('PM0163',
  '魔法少女にあこがれて',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['魔法少女にあこがれて'],
  [],
  ('PM0163', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:魔法少女にあこがれて', True, ['PM0163']),
  ('PM0163', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:魔法少女にあこがれて', True, ['PM0163'])),
 ('PM0164',
  '迫り来る脅威',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['FB-06', 'FB06', '迫り来る脅威'],
  [],
  ('PM0164', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:迫り来る脅威', True, ['PM0164']),
  ('PM0164', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:迫り来る脅威', True, ['PM0164'])),
 ('PM0165',
  'ブラックボルトDX',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ブラックボルト DX', 'ブラックボルトDX', 'ブラックボルト デラックス', 'ブラックボルトデラックス'],
  [],
  ('PM0165', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ブラックボルト DX', True, ['PM0165']),
  ('PM0165', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ブラックボルト DX', True, ['PM0165'])),
 ('PM0166',
  'ホワイトフレアDX',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ホワイトフレア DX', 'ホワイトフレアDX', 'ホワイトフレア デラックス', 'ホワイトフレアデラックス'],
  [],
  ('PM0166', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ホワイトフレア DX', True, ['PM0166']),
  ('PM0166', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ホワイトフレア DX', True, ['PM0166'])),
 ('PM0167',
  'ブラックボルト',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ブラックボルト'],
  ['DX', 'デラックス'],
  ('PM0167', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ブラックボルト', True, ['PM0167']),
  ('PM0167', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ブラックボルト', True, ['PM0167'])),
 ('PM0168',
  'ホワイトフレア',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ホワイトフレア'],
  ['DX', 'デラックス'],
  ('PM0168', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ホワイトフレア', True, ['PM0168']),
  ('PM0168', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ホワイトフレア', True, ['PM0168'])),
 ('PM0169',
  'HARUKAZE',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['HARUKAZE'],
  [],
  ('PM0169', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:HARUKAZE', True, ['PM0169']),
  ('PM0169', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:HARUKAZE', True, ['PM0169'])),
 ('PM0170',
  'MANGA BOOSTER 01',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['MANGA BOOSTER 01', 'SB-01', 'SB01'],
  [],
  ('PM0170', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:MANGA BOOSTER 01', True, ['PM0170']),
  ('PM0170', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:MANGA BOOSTER 01', True, ['PM0170'])),
 ('PM0171',
  'Newtype Rising',
  '17fe2232-49b7-4989-a23d-b7d82923c7f3',
  ['GD01', 'GD-01 Newtype Rising', 'GD01 Newtype Rising', 'Newtype Rising'],
  [],
  ('PM0171', 'WORK:17fe2232-49b7-4989-a23d-b7d82923c7f3|SK:Newtype Rising', True, ['PM0171']),
  ('PM0171', 'WORK:17fe2232-49b7-4989-a23d-b7d82923c7f3|SK:Newtype Rising', True, ['PM0171'])),
 ('PM0172',
  'THE BEST vol.2',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['CARD THE BEST vol.2',
   'ONE PIECE CARD THE BEST vol.2',
   'PRB-02',
   'PRB02',
   'THE BEST vol.2',
   'THE BEST vol.2  PRB-02'],
  ['THE BEST vol.1'],
  ('PM0172', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:THE BEST vol.2', True, ['PM0172']),
  ('PM0172', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:THE BEST vol.2', True, ['PM0172'])),
 ('PM0173',
  'メガブレイブ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['MEGAブレイブ', 'メガブレイブ'],
  ['ポケセン', 'ポケモンセンター', 'ポケモンセンターセット', 'メガシンフォニア'],
  ('PM0173', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガブレイブ', True, ['PM0173']),
  ('PM0173', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガブレイブ', True, ['PM0173'])),
 ('PM0174',
  'メガシンフォニア',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['MEGAメガシンフォニア', 'メガシンフォニア'],
  ['ポケセン', 'ポケモンセンター', 'ポケモンセンターセット', 'メガブレイブ'],
  ('PM0174', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガシンフォニア', True, ['PM0174']),
  ('PM0174', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガシンフォニア', True, ['PM0174'])),
 ('PM0175',
  'プレミアムトレーナーボックスMEGA',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['MEGAトレーナーボックス', 'MEGA プレミアムトレーナーボックス', 'トレーナーボックスMEGA', 'プレミアムトレーナー MEGA', 'メガトレーナー'],
  ['MEGAドリームex'],
  ('PM0175', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:MEGA プレミアムトレーナーボックス', True, ['PM0175']),
  ('PM0175', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:MEGA プレミアムトレーナーボックス', True, ['PM0175'])),
 ('PM0176',
  'メガシンフォニア ポケモンセンターセット',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['メガシンフォニア ポケセン', 'メガシンフォニア ポケモンセンター'],
  [],
  ('PM0176', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガシンフォニア ポケモンセンター', True, ['PM0176']),
  ('PM0176', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガシンフォニア ポケモンセンター', True, ['PM0176'])),
 ('PM0177',
  'メガブレイブ ポケモンセンターセット',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['メガブレイブ ポケセン', 'メガブレイブ ポケモンセンター'],
  [],
  ('PM0177', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガブレイブ ポケモンセンター', True, ['PM0177']),
  ('PM0177', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガブレイブ ポケモンセンター', True, ['PM0177'])),
 ('PM0178',
  'ピカチュウ マクドナルド プロモ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ピカチュウ マクドナルド', 'マクドナルド', 'マクドナルドプロモ', 'マクドナルドプロモパック'],
  ['PSA10'],
  ('PM0178', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ピカチュウ マクドナルド', True, ['PM0178']),
  ('PM0178', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ピカチュウ マクドナルド', True, ['PM0178'])),
 ('PM0179',
  'ONE PIECE DAY’25 プロモ',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['ONE PIECE DAY 25',
   'ONE PIECE DAY’25',
   'ONE PIECE DAY25',
   'ONE PIECE DAY 25 プロモ',
   'ONE PIECE DAY’25プロモ',
   'ワンピースDAY25'],
  [],
  ('PM0179', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:ONE PIECE DAY’25', True, ['PM0179']),
  ('PM0179', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:ONE PIECE DAY’25', True, ['PM0179'])),
 ('PM0180',
  '師弟の絆',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-12', 'OP12', '師弟の絆', '師弟の絆 OP-12'],
  [],
  ('PM0180', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:師弟の絆', True, ['PM0180']),
  ('PM0180', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:師弟の絆', True, ['PM0180'])),
 ('PM0181',
  '受け継がれる意志',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-13', 'OP13', '受け継がれる意思', '受け継がれる意思 OP-13'],
  [],
  (None, 'NONE', False, []),
  (None, 'NONE', False, [])),
 ('PM0182',
  'スペシャルBOX ポケモンセンタートウホク',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['specialty box tohoku', 'スペシャルBOXトウホク', 'スペシャルボックス トウホク', 'トウホク', 'ポケモンセンター トウホク'],
  ['カナザワ', 'ヒロシマ', 'フクオカ'],
  ('PM0182', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:トウホク', True, ['PM0182']),
  ('PM0182', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:トウホク', True, ['PM0182'])),
 ('PM0183',
  '異種族レビュアーズ',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['interspecies reviews', '異種族レビュアーズ'],
  [],
  ('PM0183', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:異種族レビュアーズ', True, ['PM0183']),
  ('PM0183', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:異種族レビュアーズ', True, ['PM0183'])),
 ('PM0184',
  'スターターセットMEGA メガゲンガーex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['MEGAゲンガー', 'MEGAゲンガーex', 'メガゲンガー', 'メガゲンガーex'],
  ['MEGディアンシー', 'スペシャルデッキセット'],
  ('PM0184', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガゲンガー', True, ['PM0184']),
  ('PM0184', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガゲンガー', True, ['PM0184'])),
 ('PM0185',
  'スターターセットMEGA メガディアンシーex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['MEGAメガディアンシー', 'MEGAメガディアンシーex', 'メガディアンシー', 'メガディアンシーex'],
  ['MEGAゲンガー'],
  ('PM0185', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガディアンシー', True, ['PM0185']),
  ('PM0185', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:メガディアンシー', True, ['PM0185'])),
 ('PM0186',
  'スペシャルBOX ポケモンセンターヒロシマ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スペシャルBOXヒロシマ', 'スペシャルボックス ヒロシマ', 'ヒロシマ', 'ポケモンセンター ヒロシマ'],
  ['カナザワ', 'トウホク', 'フクオカ'],
  ('PM0186', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ヒロシマ', True, ['PM0186']),
  ('PM0186', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ヒロシマ', True, ['PM0186'])),
 ('PM0187',
  '神龍への願い',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['FB-07', 'FB07', '神龍への願い'],
  [],
  ('PM0187', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:神龍への願い', True, ['PM0187']),
  ('PM0187', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:神龍への願い', True, ['PM0187'])),
 ('PM0188',
  'インフェルノX',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['インフェルノ'],
  [],
  ('PM0188', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:インフェルノ', True, ['PM0188']),
  ('PM0188', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:インフェルノ', True, ['PM0188'])),
 ('PM0189',
  'スペシャルBOX ポケモンセンターフクオカ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スペシャルBOXフクオカ', 'スペシャルボックス フクオカ', 'フクオカ', 'ポケモンセンター フクオカ'],
  ['カナザワ', 'トウホク', 'ヒロシマ'],
  ('PM0189', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:フクオカ', True, ['PM0189']),
  ('PM0189', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:フクオカ', True, ['PM0189'])),
 ('PM0190',
  'ONE PIECE magazine Vol.20 付録プロモ',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['One Piece マガジン', 'ST21-014', 'ワンピース マガジン', 'ワンピース マガジンプロモ'],
  ['ヒロインズ'],
  (None, 'NONE', False, []),
  (None, 'NONE', False, [])),
 ('PM0191',
  'プロモーションカードセット 2025',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['プロモーションカードセット2025', 'ワンピース プロモーションカードセット'],
  ['PSA10'],
  (None, 'NONE', False, []),
  ('PM0191', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:プロモーションカードセット2025', True, ['PM0191'])),
 ('PM0192',
  'Dual Impact',
  '17fe2232-49b7-4989-a23d-b7d82923c7f3',
  ['Dual Impact', 'Dual Impact GD02', 'GD-02', 'GD02', 'GD02 Dual Impact'],
  [],
  ('PM0192', 'WORK:17fe2232-49b7-4989-a23d-b7d82923c7f3|SK:Dual Impact', True, ['PM0192']),
  ('PM0192', 'WORK:17fe2232-49b7-4989-a23d-b7d82923c7f3|SK:Dual Impact', True, ['PM0192'])),
 ('PM0193',
  'Heroines edition',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['EB-03', 'EB03', 'EB-03 Heroines edition', 'Heroines edition'],
  [],
  ('PM0193', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:Heroines edition', True, ['PM0193']),
  ('PM0193', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:Heroines edition', True, ['PM0193'])),
 ('PM0194',
  'sprite',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['sprite'],
  [],
  ('PM0194', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:sprite', True, ['PM0194']),
  ('PM0194', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:sprite', True, ['PM0194'])),
 ('PM0195',
  'MANGA BOOSTER 02',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['MANGA BOOSTER 02', 'SB-02', 'SB02'],
  ['MANGA BOOSTER 01'],
  ('PM0195', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:MANGA BOOSTER 02', True, ['PM0195']),
  ('PM0195', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:MANGA BOOSTER 02', True, ['PM0195'])),
 ('PM0196',
  '蒼海の七傑',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-14', 'OP14', '蒼海の七傑', '蒼海の七傑 OP-14'],
  ['OP-13 受け継がれる意思'],
  ('PM0196', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:蒼海の七傑', True, ['PM0196']),
  ('PM0196', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:蒼海の七傑', True, ['PM0196'])),
 ('PM0197',
  '誇り高き戦闘民族',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['FB-08', 'FB08', 'FB08 誇り高き戦闘民族', '誇り高き戦闘民族'],
  [],
  ('PM0197', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:誇り高き戦闘民族', True, ['PM0197']),
  ('PM0197', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:誇り高き戦闘民族', True, ['PM0197'])),
 ('PM0198',
  'MEGAドリームex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['MEGAドリーム', 'MEGAドリームex', 'メガドリーム', 'メガドリームex'],
  ['MEGAトレーナーボックス'],
  ('PM0198', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:MEGAドリーム', True, ['PM0198']),
  ('PM0198', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:MEGAドリーム', True, ['PM0198'])),
 ('PM0199',
  'ONE PIECE BASE SHOP リミテッドカードコレクション VOL1',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['ONE PIECE BASE SHOP', 'ONE PIECE BASE SHOP リミテッドカードコレクション VOL1', 'リミテッドカードコレクション VOL1'],
  [],
  ('PM0199', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:ONE PIECE BASE SHOP', True, ['PM0199']),
  ('PM0199', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:ONE PIECE BASE SHOP', True, ['PM0199'])),
 ('PM0200',
  'MEGA スタートデッキ100 バトルコレクション',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['MEGAスタートデッキ',
   'MEGA スタートデッキ100',
   'MEGAスタートデッキ100',
   'MEGA バトルコレクション',
   'スタートデッキ100',
   'メガ スタートデッキ100',
   'メガスタートデッキ100'],
  ['ex', 'Generations', 'コロ', 'コロコロ', 'コロちゃお', 'コロチャオ'],
  ('PM0200', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:MEGA スタートデッキ100', True, ['PM0200']),
  ('PM0200', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:MEGA スタートデッキ100', True, ['PM0200'])),
 ('PM0201',
  '枕',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['Weiss Shwarz 枕', '枕'],
  [],
  ('PM0201', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:枕', True, ['PM0201']),
  ('PM0201', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:枕', True, ['PM0201'])),
 ('PM0202',
  'ムニキスゼロ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ムニキスゼロ'],
  [],
  ('PM0202', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ムニキスゼロ', True, ['PM0202']),
  ('PM0202', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ムニキスゼロ', True, ['PM0202'])),
 ('PM0203',
  'MEGA スペシャルカードセット メガエルレイドex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['MEGA スペシャルカードセット メガエルレイドex', 'スペシャルカードセット メガエルレイドex', 'メガエルレイドex'],
  [],
  ('PM0203', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:MEGA スペシャルカードセット メガエルレイドex', True, ['PM0203']),
  ('PM0203', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:MEGA スペシャルカードセット メガエルレイドex', True, ['PM0203'])),
 ('PM0204',
  'Lose&Whisp',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['Lose&Whisp'],
  [],
  ('PM0204', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:Lose&Whisp', True, ['PM0204']),
  ('PM0204', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:Lose&Whisp', True, ['PM0204'])),
 ('PM0205',
  'Steel Requiem',
  '17fe2232-49b7-4989-a23d-b7d82923c7f3',
  ['GD-03',
   'GD03',
   'GD-03 Steel Requiem',
   'GD03 Steel Requiem',
   'Steel Requiem',
   'Steel Requiem GD-03',
   'Steel Requiem GD03'],
  [],
  ('PM0205', 'WORK:17fe2232-49b7-4989-a23d-b7d82923c7f3|SK:Steel Requiem', True, ['PM0205']),
  ('PM0205', 'WORK:17fe2232-49b7-4989-a23d-b7d82923c7f3|SK:Steel Requiem', True, ['PM0205'])),
 ('PM0206',
  'EGGHEAD CRISIS',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['EB-04', 'EB04', 'EB-04 EGGHEAD CRISIS', 'EGGHEAD CRISIS'],
  [],
  ('PM0206', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:EGGHEAD CRISIS', True, ['PM0206']),
  ('PM0206', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:EGGHEAD CRISIS', True, ['PM0206'])),
 ('PM0207',
  '神の島の冒険',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-15', 'OP15', 'OP-15 神の島の冒険', '神の島の冒険'],
  [],
  ('PM0207', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:神の島の冒険', True, ['PM0207']),
  ('PM0207', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:神の島の冒険', True, ['PM0207'])),
 ('PM0208',
  '学園アイドルマスター Vol.2',
  'e48fbbd0-dc10-43a5-a085-becd5b0c9bb9',
  ['学園アイドルマスター Vol.2'],
  [],
  ('PM0208', 'WORK:e48fbbd0-dc10-43a5-a085-becd5b0c9bb9|SK:学園アイドルマスター Vol.2', True, ['PM0208']),
  ('PM0208', 'WORK:e48fbbd0-dc10-43a5-a085-becd5b0c9bb9|SK:学園アイドルマスター Vol.2', True, ['PM0208'])),
 ('PM0209',
  'ニンジャスピナー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ニンジャスピナー'],
  [],
  ('PM0209', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ニンジャスピナー', True, ['PM0209']),
  ('PM0209', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ニンジャスピナー', True, ['PM0209'])),
 ('PM0210',
  'D.C. Re:tune',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['D.C. Re:tune'],
  [],
  ('PM0210', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:D.C. Re:tune', True, ['PM0210']),
  ('PM0210', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:D.C. Re:tune', True, ['PM0210'])),
 ('PM0211',
  '俺だけレベルアップな件',
  'e48fbbd0-dc10-43a5-a085-becd5b0c9bb9',
  ['俺だけレベルアップ', '俺だけレベルアップな件'],
  [],
  ('PM0211', 'WORK:e48fbbd0-dc10-43a5-a085-becd5b0c9bb9|SK:俺だけレベルアップ', True, ['PM0211']),
  ('PM0211', 'WORK:e48fbbd0-dc10-43a5-a085-becd5b0c9bb9|SK:俺だけレベルアップ', True, ['PM0211'])),
 ('PM0212',
  '収集啦151 聚 slim（中国版）',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['151 vol.4 slim', '151 vol4 slim', '151 聚 slim', '151聚slim'],
  [],
  ('PM0212', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:151 聚 slim', True, ['PM0212']),
  ('PM0212', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:151 聚 slim', True, ['PM0212'])),
 ('PM0213',
  '収集啦151 聚 jumbo（中国版）',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['151 vol.4 jumbo', '151 vol4 jumbo', '151 聚 jumbo'],
  [],
  ('PM0213', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:151 聚 jumbo', True, ['PM0213']),
  ('PM0213', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:151 聚 jumbo', True, ['PM0213'])),
 ('PM0214',
  '収集啦151 旅 slim（中国版）',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['151 journey slim', '151 vol.1 slim', '151 vol1 slim', '151 旅 slim', '151 旅slim'],
  [],
  ('PM0214', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:151 旅 slim', True, ['PM0214']),
  ('PM0214', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:151 旅 slim', True, ['PM0214'])),
 ('PM0215',
  '最初的伙伴精品礼盒 御三家3箱セット（中国版）',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['starter gift box', '御三家 3箱', '御三家3箱', '最初的伙伴 御三家', '礼盒 御三家'],
  ['妙蛙种子', '小火龙', '杰尼龟'],
  ('PM0215', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:御三家 3箱', True, ['PM0215']),
  ('PM0215', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:御三家 3箱', True, ['PM0215'])),
 ('PM0216',
  '最初的伙伴精品礼盒 妙蛙种子（中国版）',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['bulbasaur gift box', '妙蛙种子', '最初的伙伴 妙蛙'],
  [],
  ('PM0216', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:妙蛙种子', True, ['PM0216']),
  ('PM0216', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:妙蛙种子', True, ['PM0216'])),
 ('PM0217',
  '最初的伙伴精品礼盒 小火龙（中国版）',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['charmander gift box', '小火龙', '最初的伙伴 小火龙'],
  [],
  ('PM0217', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:小火龙', True, ['PM0217']),
  ('PM0217', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:小火龙', True, ['PM0217'])),
 ('PM0218',
  '最初的伙伴精品礼盒 杰尼龟（中国版）',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['squirtle gift box', '最初的伙伴 杰尼龟', '杰尼龟'],
  [],
  ('PM0218', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:最初的伙伴 杰尼龟', True, ['PM0218']),
  ('PM0218', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:最初的伙伴 杰尼龟', True, ['PM0218'])),
 ('PM0219',
  'ストームエメラルダ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ストームエメラルダ'],
  [],
  ('PM0219', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ストームエメラルダ', True, ['PM0219']),
  ('PM0219', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ストームエメラルダ', True, ['PM0219'])),
 ('PM0220',
  'アビスアイ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['アビスアイ'],
  [],
  ('PM0220', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:アビスアイ', True, ['PM0220']),
  ('PM0220', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:アビスアイ', True, ['PM0220'])),
 ('PM0221',
  'ワイルドブレイズ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['ワイルドブレイズ'],
  [],
  ('PM0221', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ワイルドブレイズ', True, ['PM0221']),
  ('PM0221', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ワイルドブレイズ', True, ['PM0221'])),
 ('PM0222',
  'OP16 決戦の刻',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-16', 'OP16', '決戦の刻'],
  [],
  ('PM0222', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:OP16', True, ['PM0222']),
  ('PM0222', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:OP16', True, ['PM0222'])),
 ('PM0223',
  '遊戯王 LIMIT OVER COLLECTION THE HEROES',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['LIMIT OVER COLLECTION THE HEROES', 'LIMIT OVER HEROES', 'デュエルモンスターズ LIMIT OVER HEROES', '遊戯王 HEROES'],
  [],
  ('PM0223',
   'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:LIMIT OVER COLLECTION THE HEROES',
   True,
   ['PM0223']),
  ('PM0223',
   'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:LIMIT OVER COLLECTION THE HEROES',
   True,
   ['PM0223'])),
 ('PM0224',
  '遊戯王 LIMIT OVER COLLECTION THE RIVALS',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['LIMIT OVER COLLECTION THE RIVALS', 'LIMIT OVER RIVALS', 'デュエルモンスターズ LIMIT OVER RIVALS', '遊戯王 RIVALS'],
  [],
  ('PM0224',
   'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:LIMIT OVER COLLECTION THE RIVALS',
   True,
   ['PM0224']),
  ('PM0224',
   'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:LIMIT OVER COLLECTION THE RIVALS',
   True,
   ['PM0224'])),
 ('PM0225',
  'UNION ARENA 勝利の女神NIKKE【PC02BT】',
  'e48fbbd0-dc10-43a5-a085-becd5b0c9bb9',
  ['NIKKE', 'PC02BT'],
  [],
  ('PM0225', 'WORK:e48fbbd0-dc10-43a5-a085-becd5b0c9bb9|SK:NIKKE', True, ['PM0225']),
  ('PM0225', 'WORK:e48fbbd0-dc10-43a5-a085-becd5b0c9bb9|SK:NIKKE', True, ['PM0225'])),
 ('PM0226',
  'FB-09',
  '389328ec-289b-49dd-a379-c03f8afd570f',
  ['FB-09', 'FB09'],
  [],
  ('PM0226', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:FB-09', True, ['PM0226']),
  ('PM0226', 'WORK:389328ec-289b-49dd-a379-c03f8afd570f|SK:FB-09', True, ['PM0226'])),
 ('PM0227',
  '3rd anniversary set',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['3rd anniversary', '3rd anniversary set'],
  [],
  ('PM0227', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:3rd anniversary', True, ['PM0227']),
  ('PM0227', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:3rd anniversary', True, ['PM0227'])),
 ('PM0228',
  '葬送のフリーレン 新装版',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['フリーレン 新装版', '葬送のフリーレン 新装版'],
  [],
  ('PM0228', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:フリーレン 新装版', True, ['PM0228']),
  ('PM0228', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:フリーレン 新装版', True, ['PM0228'])),
 ('PM0229',
  'レトロカード バルク',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['B grade', 'bulk', 'Bグレード', 'retro', 'retro card', 'レトロ'],
  [],
  ('PM0229', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:レトロ', True, ['PM0229']),
  ('PM0229', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:レトロ', True, ['PM0229'])),
 ('PM0230',
  'トライアルデッキ 【推しの子】',
  'e330062e-fae8-4fcb-b620-3aa86c51dcfe',
  ['oshi no ko', 'OSK', 'trial deck', '推しの子'],
  [],
  ('PM0230', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:推しの子', True, ['PM0230']),
  ('PM0230', 'WORK:e330062e-fae8-4fcb-b620-3aa86c51dcfe|SK:推しの子', True, ['PM0230'])),
 ('PM0231',
  'ビクティニ レッドプロモ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['red promo', 'victini', 'victini promo', 'ビクティニ'],
  [],
  ('PM0231', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ビクティニ', True, ['PM0231']),
  ('PM0231', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:ビクティニ', True, ['PM0231'])),
 ('PM0232',
  '物語のはじまり',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['THE FIRST CHAPTER', 'ファーストチャプター', '物語のはじまり'],
  [],
  ('PM0232', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:物語のはじまり', True, ['PM0232']),
  ('PM0232', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:物語のはじまり', True, ['PM0232'])),
 ('PM0233',
  'フラッドボーンの渾沌',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['RISE OF THE FLOODBORN', 'フラッドボーン', 'フラッドボーンの渾沌', 'ブラッドボーンの渾沌'],
  [],
  ('PM0233', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:フラッドボーン', True, ['PM0233']),
  ('PM0233', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:フラッドボーン', True, ['PM0233'])),
 ('PM0234',
  'インクランド探訪',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['INTO THE INKLANDS', 'インクランド探訪', 'イングランド探訪'],
  [],
  ('PM0234', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:インクランド探訪', True, ['PM0234']),
  ('PM0234', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:インクランド探訪', True, ['PM0234'])),
 ('PM0235',
  '逆襲のアースラ',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ["URSULA'S RETURN", 'URSULAS RETURN', '逆襲のアースラ'],
  [],
  ('PM0235', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:逆襲のアースラ', True, ['PM0235']),
  ('PM0235', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:逆襲のアースラ', True, ['PM0235'])),
 ('PM0236',
  '星々の輝き',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['SHIMMERING SKIES', '星々の輝き'],
  [],
  ('PM0236', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:星々の輝き', True, ['PM0236']),
  ('PM0236', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:星々の輝き', True, ['PM0236'])),
 ('PM0237',
  '大いなるアズライト',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['AZURITE SEA', 'アズライト', '大いなるアズライト'],
  [],
  ('PM0237', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:アズライト', True, ['PM0237']),
  ('PM0237', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:アズライト', True, ['PM0237'])),
 ('PM0238',
  'アーケイジアと魔法の島',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ["ARCHAZIA'S ISLAND", 'ARCHAZIAS ISLAND', 'アーケイジア', 'アーケイジアと魔法の島'],
  [],
  ('PM0238', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:アーケイジア', True, ['PM0238']),
  ('PM0238', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:アーケイジア', True, ['PM0238'])),
 ('PM0239',
  'ジャファーの王権',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['REIGN OF JAFAR', 'ジャファーの王権'],
  [],
  ('PM0239', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:ジャファーの王権', True, ['PM0239']),
  ('PM0239', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:ジャファーの王権', True, ['PM0239'])),
 ('PM0240',
  '物語のおもいで',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['FABLED', '物語のおもいで'],
  [],
  ('PM0240', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:物語のおもいで', True, ['PM0240']),
  ('PM0240', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:物語のおもいで', True, ['PM0240'])),
 ('PM0243',
  '未知なる彼方へ!',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['WILDS UNKNOWN', '未知なる彼方へ'],
  [],
  ('PM0243', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:未知なる彼方へ', True, ['PM0243']),
  ('PM0243', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:未知なる彼方へ', True, ['PM0243'])),
 ('PM0244',
  'ヴァインズ・アタック!',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['ATTACK OF THE VINE', 'ヴァインズ・アタック', 'ヴァインズアタック'],
  [],
  ('PM0244', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:ヴァインズ・アタック', True, ['PM0244']),
  ('PM0244', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:ヴァインズ・アタック', True, ['PM0244'])),
 ('PM0245',
  'ハイペリアシティ',
  '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27',
  ['HYPERIA CITY', 'ハイペリアシティ', 'ハイリペアシティ'],
  [],
  ('PM0245', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:ハイペリアシティ', True, ['PM0245']),
  ('PM0245', 'WORK:1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27|SK:ハイペリアシティ', True, ['PM0245'])),
 ('PM0246',
  'LEGACY OF DESTRUCTION',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['LEDE', 'LEGACY OF DESTRUCTION', 'レガシー・オブ・デストラクション'],
  [],
  ('PM0246', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:LEGACY OF DESTRUCTION', True, ['PM0246']),
  ('PM0246', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:LEGACY OF DESTRUCTION', True, ['PM0246'])),
 ('PM0247',
  'INFINITE FORBIDDEN',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['INFINITE FORBIDDEN', 'INFO', 'インフィニット・フォビドゥン', 'インフィニットフォビドゥン'],
  [],
  ('PM0247', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:INFINITE FORBIDDEN', True, ['PM0247']),
  ('PM0247', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:INFINITE FORBIDDEN', True, ['PM0247'])),
 ('PM0248',
  'RAGE OF THE ABYSS',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['RAGE OF THE ABYSS', 'ROTA', 'レイジ・オブ・ジ・アビス'],
  [],
  ('PM0248', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:RAGE OF THE ABYSS', True, ['PM0248']),
  ('PM0248', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:RAGE OF THE ABYSS', True, ['PM0248'])),
 ('PM0249',
  'SUPREME DARKNESS',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['SUDA', 'SUPREME DARKNESS', 'スプリーム・ダークネス'],
  [],
  ('PM0249', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:SUPREME DARKNESS', True, ['PM0249']),
  ('PM0249', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:SUPREME DARKNESS', True, ['PM0249'])),
 ('PM0250',
  'ALLIANCE INSIGHT',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['ALIN', 'ALLIANCE INSIGHT', 'アライアンス・インサイト'],
  [],
  ('PM0250', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:ALLIANCE INSIGHT', True, ['PM0250']),
  ('PM0250', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:ALLIANCE INSIGHT', True, ['PM0250'])),
 ('PM0251',
  'DUELIST ADVANCE',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['DUAD', 'DUELIST ADVANCE', 'デュエリスト・アドバンス'],
  [],
  ('PM0251', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:DUELIST ADVANCE', True, ['PM0251']),
  ('PM0251', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:DUELIST ADVANCE', True, ['PM0251'])),
 ('PM0252',
  'DOOM OF DIMENSIONS',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['DOOD', 'DOOM OF DIMENSIONS'],
  [],
  ('PM0252', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:DOOM OF DIMENSIONS', True, ['PM0252']),
  ('PM0252', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:DOOM OF DIMENSIONS', True, ['PM0252'])),
 ('PM0253',
  'BURST PROTOCOL',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['BPRO', 'BURST PROTOCOL'],
  [],
  ('PM0253', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:BURST PROTOCOL', True, ['PM0253']),
  ('PM0253', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:BURST PROTOCOL', True, ['PM0253'])),
 ('PM0254',
  'BLAZING DOMINION',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['BLAZING DOMINION', 'BLZD'],
  [],
  ('PM0254', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:BLAZING DOMINION', True, ['PM0254']),
  ('PM0254', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:BLAZING DOMINION', True, ['PM0254'])),
 ('PM0255',
  'CHAOS ORIGINS',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['CHAOS ORIGINS', 'CORI'],
  [],
  ('PM0255', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:CHAOS ORIGINS', True, ['PM0255']),
  ('PM0255', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:CHAOS ORIGINS', True, ['PM0255'])),
 ('PM0256',
  'QUARTER CENTURY CHRONICLE side:UNITY',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['QCCU', 'QUARTER CENTURY CHRONICLE side UNITY', 'QUARTER CENTURY CHRONICLE UNITY', 'クォーターセンチュリークロニクル'],
  [],
  (None, 'NONE', False, []),
  (None, 'NONE', False, [])),
 ('PM0257',
  'QUARTER CENTURY CHRONICLE side:PRIDE',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['QCCP', 'QUARTER CENTURY CHRONICLE PRIDE', 'QUARTER CENTURY CHRONICLE side PRIDE'],
  [],
  (None, 'NONE', False, []),
  (None, 'NONE', False, [])),
 ('PM0258',
  'QUARTER CENTURY DUELIST BOX',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['QCDB', 'QUARTER CENTURY DUELIST BOX'],
  [],
  ('PM0258', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:QUARTER CENTURY DUELIST BOX', True, ['PM0258']),
  ('PM0258', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:QUARTER CENTURY DUELIST BOX', True, ['PM0258'])),
 ('PM0259',
  'QUARTER CENTURY ART COLLECTION',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['QCAC', 'QUARTER CENTURY ART COLLECTION', 'クォーターセンチュリー アート コレクション'],
  [],
  ('PM0259', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:QUARTER CENTURY ART COLLECTION', True, ['PM0259']),
  ('PM0259',
   'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:QUARTER CENTURY ART COLLECTION',
   True,
   ['PM0259'])),
 ('PM0260',
  'BEYOND THE BRAVE',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['BETB', 'BEYOND THE BRAVE'],
  [],
  ('PM0260', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:BEYOND THE BRAVE', True, ['PM0260']),
  ('PM0260', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:BEYOND THE BRAVE', True, ['PM0260'])),
 ('PM0261',
  'QUARTER CENTURY LIMITED PACK',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['QUARTER CENTURY LIMITED PACK'],
  [],
  ('PM0261', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:QUARTER CENTURY LIMITED PACK', True, ['PM0261']),
  ('PM0261', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:QUARTER CENTURY LIMITED PACK', True, ['PM0261'])),
 ('PM0262',
  'QUARTER CENTURY TRINITY BOX',
  '1129cb04-6002-44a5-bf6f-acc609c17b9c',
  ['QUARTER CENTURY TRINITY BOX'],
  [],
  ('PM0262', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:QUARTER CENTURY TRINITY BOX', True, ['PM0262']),
  ('PM0262', 'WORK:1129cb04-6002-44a5-bf6f-acc609c17b9c|SK:QUARTER CENTURY TRINITY BOX', True, ['PM0262'])),
 ('PM0263',
  '30th CELEBRATION',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['30th CELEBRATION', '30thCELEBRATION', '30周年セレブレーション'],
  ['FUTURISTIC', 'エーフィ', 'プレミアムデッキセット'],
  ('PM0263', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:30th CELEBRATION', True, ['PM0263']),
  ('PM0263', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:30th CELEBRATION', True, ['PM0263'])),
 ('PM0264',
  'FUTURISTIC BOX',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['30th CELEBRATION FUTURISTIC', 'FUTURISTIC BOX', 'フューチャリスティック'],
  ['エーフィ', 'プレミアムデッキセット'],
  ('PM0264', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:FUTURISTIC BOX', True, ['PM0264']),
  ('PM0264', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:FUTURISTIC BOX', True, ['PM0264'])),
 ('PM0265',
  '30th CELEBRATION プレミアムデッキセット',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['30th CELEBRATION プレミアムデッキセット', 'エーフィ・ブラッキー', 'エーフィブラッキー'],
  ['FUTURISTIC'],
  ('PM0265', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:30th CELEBRATION プレミアムデッキセット', True, ['PM0265']),
  ('PM0265', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:30th CELEBRATION プレミアムデッキセット', True, ['PM0265'])),
 ('PM0266',
  'OP-17',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['OP-17', 'OP17', "WORLD'S STRONGEST WARRIORS", '世界最強の戦士'],
  [],
  ('PM0266', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:OP-17', True, ['PM0266']),
  ('PM0266', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:OP-17', True, ['PM0266'])),
 ('PM0267',
  'ONE PIECE magazine Vol.21 特集ヒロインズ 021 付録プロモ',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['ONE PIECE magazine Vol.21', 'ヒロインズ 021', 'ワンピースマガジン ヒロインズ'],
  [],
  ('PM0267', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:ONE PIECE magazine Vol.21', True, ['PM0267']),
  ('PM0267', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:ONE PIECE magazine Vol.21', True, ['PM0267'])),
 ('PM0268',
  '4周年!四皇トレジャーゲット キャンペーンパック',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['4周年トレジャーパック', '4周年 四皇トレジャーゲット', '四皇トレジャーゲット', '四皇トレジャーパック'],
  [],
  ('PM0268', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:4周年 四皇トレジャーゲット', True, ['PM0268']),
  ('PM0268', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:4周年 四皇トレジャーゲット', True, ['PM0268'])),
 ('PM0269',
  'ONE PIECE magazine Vol.16 付録プロモ',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['magazine Vol.16', 'P-028'],
  [],
  ('PM0269', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:magazine Vol.16', True, ['PM0269']),
  ('PM0269', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:magazine Vol.16', True, ['PM0269'])),
 ('PM0270',
  'ONE PIECE magazine Vol.17 付録プロモ',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['magazine Vol.17', 'P-046'],
  [],
  ('PM0270', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:magazine Vol.17', True, ['PM0270']),
  ('PM0270', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:magazine Vol.17', True, ['PM0270'])),
 ('PM0271',
  'ONE PIECE magazine 別冊 Focus on ONE PIECE FAN LETTER 付録プロモ',
  'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
  ['FAN LETTER', 'P-096'],
  [],
  ('PM0271', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:FAN LETTER', True, ['PM0271']),
  ('PM0271', 'WORK:c6acce0e-fe08-446a-adae-8e9bc946b8b0|SK:FAN LETTER', True, ['PM0271'])),
 ('PM0272',
  'ポケモンカードゲーム MEGA スターターセットex イーブイex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['イーブイex', 'スターターセットex イーブイ'],
  ['種セット'],
  ('PM0272', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:イーブイex', True, ['PM0272']),
  ('PM0272', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:イーブイex', True, ['PM0272'])),
 ('PM0273',
  'ポケモンカードゲーム MEGA スターターセットex ゾロア＆ゾロアークex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スターターセットex ゾロア', 'ゾロアークex'],
  ['種セット'],
  ('PM0273', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スターターセットex ゾロア', True, ['PM0273']),
  ('PM0273', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スターターセットex ゾロア', True, ['PM0273'])),
 ('PM0274',
  'ポケモンカードゲーム MEGA スターターセットex ニャオハ＆マスカーニャex',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スターターセットex ニャオハ', 'マスカーニャex'],
  ['種セット'],
  ('PM0274', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スターターセットex ニャオハ', True, ['PM0274']),
  ('PM0274', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スターターセットex ニャオハ', True, ['PM0274'])),
 ('PM0275',
  'ポケモンカードゲーム MEGA スターターセットex 3種セット',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['スターターセットex 3種セット', 'スターターセットex ３種セット'],
  [],
  ('PM0275', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スターターセットex 3種セット', True, ['PM0275']),
  ('PM0275', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:スターターセットex 3種セット', True, ['PM0275'])),
 ('PM0276',
  'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット フシギダネ・ヒトカゲ・ゼニガメ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カードセット フシギダネ'],
  [],
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0276):要確認',
   False,
   ['PM0263', 'PM0276']),
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0276):要確認',
   False,
   ['PM0263', 'PM0276'])),
 ('PM0277',
  'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット チコリータ・ヒノアラシ・ワニノコ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カードセット チコリータ'],
  [],
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0277):要確認',
   False,
   ['PM0263', 'PM0277']),
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0277):要確認',
   False,
   ['PM0263', 'PM0277'])),
 ('PM0278',
  'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット キモリ・アチャモ・ミズゴロウ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カードセット キモリ'],
  [],
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0278):要確認',
   False,
   ['PM0263', 'PM0278']),
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0278):要確認',
   False,
   ['PM0263', 'PM0278'])),
 ('PM0279',
  'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ナエトル・ヒコザル・ポッチャマ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カードセット ナエトル'],
  [],
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0279):要確認',
   False,
   ['PM0263', 'PM0279']),
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0279):要確認',
   False,
   ['PM0263', 'PM0279'])),
 ('PM0280',
  'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ツタージャ・ポカブ・ミジュマル',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カードセット ツタージャ'],
  [],
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0280):要確認',
   False,
   ['PM0263', 'PM0280']),
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0280):要確認',
   False,
   ['PM0263', 'PM0280'])),
 ('PM0281',
  'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ハリマロン・フォッコ・ケロマツ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カードセット ハリマロン'],
  [],
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0281):要確認',
   False,
   ['PM0263', 'PM0281']),
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0281):要確認',
   False,
   ['PM0263', 'PM0281'])),
 ('PM0282',
  'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット モクロー・ニャビー・アシマリ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カードセット モクロー'],
  [],
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0282):要確認',
   False,
   ['PM0263', 'PM0282']),
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0282):要確認',
   False,
   ['PM0263', 'PM0282'])),
 ('PM0283',
  'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット サルノリ・ヒバニー・メッソン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カードセット サルノリ'],
  [],
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0283):要確認',
   False,
   ['PM0263', 'PM0283']),
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0283):要確認',
   False,
   ['PM0263', 'PM0283'])),
 ('PM0284',
  'ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ニャオハ・ホゲータ・クワッス',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['カードセット ニャオハ'],
  [],
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0284):要確認',
   False,
   ['PM0263', 'PM0284']),
  ('PM0263',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0263/PM.PM0284):要確認',
   False,
   ['PM0263', 'PM0284'])),
 ('PM0285',
  'ポケモンカードゲーム MEGA スタートデッキ100 バトルコレクション コロちゃおVer.',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['コロちゃお', 'コロチャオ'],
  [],
  ('PM0285', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:コロちゃお', True, ['PM0285']),
  ('PM0285', 'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|SK:コロちゃお', True, ['PM0285'])),
 ('PM0286',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 草 ジュナイパー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ ジュナイパー'],
  [],
  ('PM0286',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0286/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0286', 'PM0088', 'PM0089']),
  ('PM0286',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0286/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0286', 'PM0088', 'PM0089'])),
 ('PM0287',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 炎 ビクティニ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ ビクティニ'],
  [],
  ('PM0287',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0287/PM.PM0088/PM.PM0089/PM.PM0231):要確認',
   False,
   ['PM0287', 'PM0088', 'PM0089', 'PM0231']),
  ('PM0287',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0287/PM.PM0088/PM.PM0089/PM.PM0231):要確認',
   False,
   ['PM0287', 'PM0088', 'PM0089', 'PM0231'])),
 ('PM0288',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 水 ゲッコウガ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ ゲッコウガ'],
  [],
  ('PM0288',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0288/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0288', 'PM0088', 'PM0089']),
  ('PM0288',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0288/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0288', 'PM0088', 'PM0089'])),
 ('PM0289',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 雷 ミライドン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ ミライドン'],
  [],
  ('PM0289',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0289/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0289', 'PM0088', 'PM0089']),
  ('PM0289',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0289/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0289', 'PM0088', 'PM0089'])),
 ('PM0290',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 超 ピクシー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ ピクシー'],
  [],
  ('PM0290',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0290/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0290', 'PM0088', 'PM0089']),
  ('PM0290',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0290/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0290', 'PM0088', 'PM0089'])),
 ('PM0291',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 闘 コライドン',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ コライドン'],
  [],
  ('PM0291',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0291/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0291', 'PM0088', 'PM0089']),
  ('PM0291',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0291/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0291', 'PM0088', 'PM0089'])),
 ('PM0292',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 悪 ヘルガー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ ヘルガー'],
  [],
  ('PM0292',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0292/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0292', 'PM0088', 'PM0089']),
  ('PM0292',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0292/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0292', 'PM0088', 'PM0089'])),
 ('PM0293',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 鋼 メルメタル',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ メルメタル'],
  [],
  ('PM0293',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0293/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0293', 'PM0088', 'PM0089']),
  ('PM0293',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0293/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0293', 'PM0088', 'PM0089'])),
 ('PM0294',
  'ポケモンカードゲーム スカーレット＆バイオレット おまかせexスタートデッキ',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['おまかせexスタートデッキ'],
  [],
  ('PM0294',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0294/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0294', 'PM0088', 'PM0089']),
  ('PM0294',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0294/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0294', 'PM0088', 'PM0089'])),
 ('PM0295',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ テラスタル カイリュー',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ テラスタル カイリュー'],
  [],
  ('PM0295',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0295/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0295', 'PM0088', 'PM0089']),
  ('PM0295',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0295/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0295', 'PM0088', 'PM0089'])),
 ('PM0296',
  'ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ テラスタル ヨクバリス',
  '2fe437c0-5a47-4311-9b94-0c107f64adcd',
  ['exスタートデッキ テラスタル ヨクバリス'],
  [],
  ('PM0296',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0296/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0296', 'PM0088', 'PM0089']),
  ('PM0296',
   'WORK:2fe437c0-5a47-4311-9b94-0c107f64adcd|MULTI(PM.PM0296/PM.PM0088/PM.PM0089):要確認',
   False,
   ['PM0296', 'PM0088', 'PM0089']))]

# Candidate dictionaries are test fixtures, not approved production data updates.
SPACE_CANDIDATE_DICTIONARY = {'CSV01': (['スターターセットV 草', 'スターターセットV草'], ['種セット']),
 'CSV02': (['スターターセットV 炎', 'スターターセットV炎'], ['種セット', 'セブン']),
 'CSV03': (['スターターセットV 水', 'スターターセットV水'], ['種セット']),
 'CSV04': (['スターターセットV 雷', 'スターターセットV雷'], ['種セット']),
 'CSV05': (['スターターセットV 闘', 'スターターセットV闘'], ['種セット']),
 'CSV06': (['スターターセットV5 コンプリートバトルボックス', 'スターターセットV5コンプリートバトルボックス'], []),
 'CSV07': (['トイザらス限定 トリプルスターターセットV', 'トイザらス限定トリプルスターターセットV'], []),
 'CSV08': (['セブン-イレブン限定スペシャルセット スターターセットV炎', 'セブン-イレブン限定スペシャルセットスターターセットV炎'], []),
 'CSV09': (['プレミアムトレーナーボックス ソード＆シールド', 'プレミアムトレーナーボックスソード＆シールド'], []),
 'CSV10': (['ザシアン＋ザマゼンタBOX'], []),
 'CSV11': (['スターターセットVMAX リザードン', 'スターターセットVMAXリザードン'], ['種セット']),
 'CSV12': (['スターターセットVMAX オーロンゲ', 'スターターセットVMAXオーロンゲ'], ['種セット']),
 'CSV13': (['Vスタートデッキ草 フシギバナ', 'Vスタートデッキ草フシギバナ'], ['種セット']),
 'CSV14': (['Vスタートデッキ炎 ガオガエン', 'Vスタートデッキ炎ガオガエン'], ['種セット']),
 'CSV15': (['Vスタートデッキ水 ホエルオー', 'Vスタートデッキ水ホエルオー'], ['種セット']),
 'CSV16': (['Vスタートデッキ雷 ピカチュウ', 'Vスタートデッキ雷ピカチュウ'], ['種セット']),
 'CSV17': (['Vスタートデッキ超 ミュウ', 'Vスタートデッキ超ミュウ'], ['種セット']),
 'CSV18': (['Vスタートデッキ闘 ルカリオ', 'Vスタートデッキ闘ルカリオ'], ['種セット']),
 'CSV19': (['Vスタートデッキ悪 ガラルヤドラン', 'Vスタートデッキ悪ガラルヤドラン'], ['種セット']),
 'CSV20': (['Vスタートデッキ鋼 ジュラルドン', 'Vスタートデッキ鋼ジュラルドン'], ['種セット']),
 'CSV21': (['Vスタートデッキ無色 イーブイ', 'Vスタートデッキ無色イーブイ'], ['種セット']),
 'CSV22': (['VMAXスペシャルセット'], ['イーブイヒーローズ']),
 'CSV23': (['スターターセットVMAX フシギバナ', 'スターターセットVMAXフシギバナ'], ['種セット']),
 'CSV24': (['スターターセットVMAX カメックス', 'スターターセットVMAXカメックス'], ['種セット']),
 'CSV25': (['VMAX 対戦トリプルスターターセット', 'VMAX対戦トリプルスターターセット'], []),
 'CSV26': (['プレミアムトレーナーボックス ICHIGEKI', 'プレミアムトレーナーボックスICHIGEKI'], []),
 'CSV27': (['プレミアムトレーナーボックス RENGEKI', 'プレミアムトレーナーボックスRENGEKI'], []),
 'CSV28': (['ジャンボパックセット 白銀のランス＆漆黒のガイスト', 'ジャンボパックセット白銀のランス＆漆黒のガイスト'], []),
 'CSV29': (['VMAXスペシャルセット イーブイヒーローズ', 'VMAXスペシャルセットイーブイヒーローズ'], []),
 'CSV30': (['ファミリーポケモンカードゲーム（ソード＆シールド）'], []),
 'CSV31': (['いつでもどこでもファミリーポケモンカードゲーム'], []),
 'CSV32': (['スペシャルカードセット ミュウツーV-UNION', 'スペシャルカードセットミュウツーV-UNION'], []),
 'CSV33': (['スペシャルカードセット ゲッコウガV-UNION', 'スペシャルカードセットゲッコウガV-UNION'], []),
 'CSV34': (['スペシャルカードセット ザシアンV-UNION', 'スペシャルカードセットザシアンV-UNION'], []),
 'CSV35': (['スペシャルデッキセット ザシアン・ザマゼンタ vs ムゲンダイナ', 'スペシャルデッキセットザシアン・ザマゼンタvsムゲンダイナ'], []),
 'CSV36': (['スタートデッキ100'], ['コロコロ']),
 'CSV37': (['スタートデッキ100 コロコロコミックVer.', 'スタートデッキ100コロコロコミックVer.'], []),
 'CSV38': (['プレミアムトレーナーボックス VSTAR', 'プレミアムトレーナーボックスVSTAR'], []),
 'CSV39': (['スターターセットVSTAR ルカリオ', 'スターターセットVSTARルカリオ'], ['種セット']),
 'CSV40': (['スターターセットVSTAR ダークライ', 'スターターセットVSTARダークライ'], ['種セット']),
 'CSV41': (['VSTAR&VMAX ハイクラスデッキ ゼラオラ', 'VSTAR&VMAXハイクラスデッキゼラオラ'], ['種セット']),
 'CSV42': (['VSTAR&VMAX ハイクラスデッキ デオキシス', 'VSTAR&VMAXハイクラスデッキデオキシス'], ['種セット']),
 'CSV43': (['VSTARスペシャルセット'], []),
 'CSV44': (['スペシャルデッキセット リザードンVSTAR vs レックウザVMAX', 'スペシャルデッキセットリザードンVSTARvsレックウザVMAX'], [])}

SPACE_DESIGN_OVERRIDES = {'PM0048': (['シールド'], ['プレシャス', 'プレミアムトレーナーボックス', 'ファミリーポケモンカードゲーム']),
 'PM0060': (['白銀'], ['ジャンボパックセット']),
 'PM0061': (['漆黒'], ['ジャンボパックセット']),
 'PM0062': (['イーブイヒーローズ'], ['イーブイズセット', 'VMAXスペシャルセット']),
 'PM0074': (['VMAXクライマックス', 'VMAX クライマックス'], []),
 'PM0087': (['VSTARユニバース', 'VSTAR ユニバース'], []),
 'PM0126': (['いつでもどこでもバトルアカデミー', 'いつでもどこでも バトルアカデミー'], []),
 'PM0200': (['MEGAスタートデッキ',
             'MEGA スタートデッキ100',
             'MEGAスタートデッキ100',
             'MEGA バトルコレクション',
             'メガ スタートデッキ100',
             'メガスタートデッキ100'],
            ['ex', 'Generations', 'コロ', 'コロコロ', 'コロちゃお', 'コロチャオ']),
 'CSV01': (['スターターセットV草'], ['種セット', 'VMAX', 'VSTAR', 'スターターセットV5']),
 'CSV02': (['スターターセットV炎'], ['種セット', 'セブン', 'VMAX', 'VSTAR', 'スターターセットV5']),
 'CSV03': (['スターターセットV水'], ['種セット', 'VMAX', 'VSTAR', 'スターターセットV5']),
 'CSV04': (['スターターセットV雷'], ['種セット', 'VMAX', 'VSTAR', 'スターターセットV5']),
 'CSV05': (['スターターセットV闘'], ['種セット', 'VMAX', 'VSTAR', 'スターターセットV5']),
 'CSV36': (['スタートデッキ100 2021'], ['コロコロ', 'MEGA', 'メガ', 'バトルコレクション']),
 'CSV35': (['スペシャルデッキセットザシアン・ザマゼンタvsムゲンダイナ'], []),
 'CSV44': (['スペシャルデッキセットリザードンVSTARvsレックウザVMAX'], [])}

SPACE_DESIGN_CASES = [('candidate_title', '', 'スターターセットV 草', 'CSV01'),
 ('candidate_title', '', 'スターターセットV 炎', 'CSV02'),
 ('candidate_title', '', 'スターターセットV 水', 'CSV03'),
 ('candidate_title', '', 'スターターセットV 雷', 'CSV04'),
 ('candidate_title', '', 'スターターセットV 闘', 'CSV05'),
 ('candidate_title', '', 'スターターセットV5 コンプリートバトルボックス', 'CSV06'),
 ('candidate_title', '', 'トイザらス限定 トリプルスターターセットV', 'CSV07'),
 ('candidate_title', '', 'セブン-イレブン限定スペシャルセット スターターセットV炎', 'CSV08'),
 ('candidate_title', '', 'プレミアムトレーナーボックス ソード＆シールド', 'CSV09'),
 ('candidate_title', '', 'ザシアン＋ザマゼンタBOX', 'CSV10'),
 ('candidate_title', '', 'スターターセットVMAX リザードン', 'CSV11'),
 ('candidate_title', '', 'スターターセットVMAX オーロンゲ', 'CSV12'),
 ('candidate_title', '', 'Vスタートデッキ草 フシギバナ', 'CSV13'),
 ('candidate_title', '', 'Vスタートデッキ炎 ガオガエン', 'CSV14'),
 ('candidate_title', '', 'Vスタートデッキ水 ホエルオー', 'CSV15'),
 ('candidate_title', '', 'Vスタートデッキ雷 ピカチュウ', 'CSV16'),
 ('candidate_title', '', 'Vスタートデッキ超 ミュウ', 'CSV17'),
 ('candidate_title', '', 'Vスタートデッキ闘 ルカリオ', 'CSV18'),
 ('candidate_title', '', 'Vスタートデッキ悪 ガラルヤドラン', 'CSV19'),
 ('candidate_title', '', 'Vスタートデッキ鋼 ジュラルドン', 'CSV20'),
 ('candidate_title', '', 'Vスタートデッキ無色 イーブイ', 'CSV21'),
 ('candidate_title', '', 'VMAXスペシャルセット', 'CSV22'),
 ('candidate_title', '', 'スターターセットVMAX フシギバナ', 'CSV23'),
 ('candidate_title', '', 'スターターセットVMAX カメックス', 'CSV24'),
 ('candidate_title', '', 'VMAX 対戦トリプルスターターセット', 'CSV25'),
 ('candidate_title', '', 'プレミアムトレーナーボックス ICHIGEKI', 'CSV26'),
 ('candidate_title', '', 'プレミアムトレーナーボックス RENGEKI', 'CSV27'),
 ('candidate_title', '', 'ジャンボパックセット 白銀のランス＆漆黒のガイスト', 'CSV28'),
 ('candidate_title', '', 'VMAXスペシャルセット イーブイヒーローズ', 'CSV29'),
 ('candidate_title', '', 'ファミリーポケモンカードゲーム（ソード＆シールド）', 'CSV30'),
 ('candidate_title', '', 'いつでもどこでもファミリーポケモンカードゲーム', 'CSV31'),
 ('candidate_title', '', 'スペシャルカードセット ミュウツーV-UNION', 'CSV32'),
 ('candidate_title', '', 'スペシャルカードセット ゲッコウガV-UNION', 'CSV33'),
 ('candidate_title', '', 'スペシャルカードセット ザシアンV-UNION', 'CSV34'),
 ('candidate_title', '', 'スペシャルデッキセット ザシアン・ザマゼンタ vs ムゲンダイナ', 'CSV35'),
 ('candidate_title', '', 'スタートデッキ100', None),
 ('candidate_title', '', 'スタートデッキ100 コロコロコミックVer.', 'CSV37'),
 ('candidate_title', '', 'プレミアムトレーナーボックス VSTAR', 'CSV38'),
 ('candidate_title', '', 'スターターセットVSTAR ルカリオ', 'CSV39'),
 ('candidate_title', '', 'スターターセットVSTAR ダークライ', 'CSV40'),
 ('candidate_title', '', 'VSTAR&VMAX ハイクラスデッキ ゼラオラ', 'CSV41'),
 ('candidate_title', '', 'VSTAR&VMAX ハイクラスデッキ デオキシス', 'CSV42'),
 ('candidate_title', '', 'VSTARスペシャルセット', 'CSV43'),
 ('candidate_title', '', 'スペシャルデッキセット リザードンVSTAR vs レックウザVMAX', 'CSV44'),
 ('designed_example', '', '2021 スタートデッキ100', 'CSV36'),
 ('designed_example', '', 'スタートデッキ100 2021', 'CSV36'),
 ('designed_example', '', 'MEGA スタートデッキ100', 'PM0200'),
 ('designed_example', '', 'スタートデッキ100', None),
 ('designed_example', '', 'VMAX', None),
 ('designed_example', '', 'VSTAR', None),
 ('designed_example', '', 'いつでもどこでも', None),
 ('designed_example', '', 'スターターセットVMAX 草', None),
 ('designed_example', '', 'スターターセットVMAX 炎', None),
 ('designed_example', '', 'スターターセットVMAX 水', None),
 ('designed_example', '', 'スターターセットVMAX 雷', None),
 ('designed_example', '', 'スターターセットVMAX 闘', None),
 ('space_boundary', 'plain', 'スターターセットV 草', 'CSV01'),
 ('space_boundary', 'joined', 'スターターセットV草', 'CSV01'),
 ('space_boundary', 'wide_space', 'スターターセットV\u3000草', 'CSV01'),
 ('space_boundary', 'repeated_space', 'スターターセットV  草', 'CSV01'),
 ('space_boundary', 'wrong_work', 'スターターセットV 草', None),
 ('space_boundary', 'extra_qty', 'スターターセットV 草 10箱', None),
 ('space_boundary', 'newline', 'スターターセットV\n草', None),
 ('space_boundary', 'tab', 'スターターセットV\t草', None),
 ('space_boundary', 'plain', 'スターターセットV 炎', 'CSV02'),
 ('space_boundary', 'joined', 'スターターセットV炎', 'CSV02'),
 ('space_boundary', 'wide_space', 'スターターセットV\u3000炎', 'CSV02'),
 ('space_boundary', 'repeated_space', 'スターターセットV  炎', 'CSV02'),
 ('space_boundary', 'wrong_work', 'スターターセットV 炎', None),
 ('space_boundary', 'extra_qty', 'スターターセットV 炎 10箱', None),
 ('space_boundary', 'newline', 'スターターセットV\n炎', None),
 ('space_boundary', 'tab', 'スターターセットV\t炎', None),
 ('space_boundary', 'plain', 'スターターセットV 水', 'CSV03'),
 ('space_boundary', 'joined', 'スターターセットV水', 'CSV03'),
 ('space_boundary', 'wide_space', 'スターターセットV\u3000水', 'CSV03'),
 ('space_boundary', 'repeated_space', 'スターターセットV  水', 'CSV03'),
 ('space_boundary', 'wrong_work', 'スターターセットV 水', None),
 ('space_boundary', 'extra_qty', 'スターターセットV 水 10箱', None),
 ('space_boundary', 'newline', 'スターターセットV\n水', None),
 ('space_boundary', 'tab', 'スターターセットV\t水', None),
 ('space_boundary', 'plain', 'スターターセットV 雷', 'CSV04'),
 ('space_boundary', 'joined', 'スターターセットV雷', 'CSV04'),
 ('space_boundary', 'wide_space', 'スターターセットV\u3000雷', 'CSV04'),
 ('space_boundary', 'repeated_space', 'スターターセットV  雷', 'CSV04'),
 ('space_boundary', 'wrong_work', 'スターターセットV 雷', None),
 ('space_boundary', 'extra_qty', 'スターターセットV 雷 10箱', None),
 ('space_boundary', 'newline', 'スターターセットV\n雷', None),
 ('space_boundary', 'tab', 'スターターセットV\t雷', None),
 ('space_boundary', 'plain', 'スターターセットV 闘', 'CSV05'),
 ('space_boundary', 'joined', 'スターターセットV闘', 'CSV05'),
 ('space_boundary', 'wide_space', 'スターターセットV\u3000闘', 'CSV05'),
 ('space_boundary', 'repeated_space', 'スターターセットV  闘', 'CSV05'),
 ('space_boundary', 'wrong_work', 'スターターセットV 闘', None),
 ('space_boundary', 'extra_qty', 'スターターセットV 闘 10箱', None),
 ('space_boundary', 'newline', 'スターターセットV\n闘', None),
 ('space_boundary', 'tab', 'スターターセットV\t闘', None)]



def space_saved_dictionary():
    return (
        {r[0]: list(r[3]) for r in SPACE_SAVED_PRODUCTS},
        {r[0]: list(r[4]) for r in SPACE_SAVED_PRODUCTS},
        {r[0]: r[2] for r in SPACE_SAVED_PRODUCTS},
    )


@pytest.mark.parametrize("code,title,work,search,exclude,before,expected", SPACE_SAVED_PRODUCTS)
def test_space_existing_293_full_tuples(code, title, work, search, exclude, before, expected):
    sk, ex, works = space_saved_dictionary()
    actual = match_pid_with_work(title, list(sk), sk, ex, work_id=work, product_work_ids=works)
    assert actual == expected
    if before != expected:
        assert code == "PM0191" and before == (None, "NONE", False, [])
        assert actual[0] == code and actual[2]
    else:
        assert actual == before


def test_space_existing_fixture_coverage():
    assert len(SPACE_SAVED_PRODUCTS) == 293
    assert sum(r[5][2] and r[5][0] == r[0] for r in SPACE_SAVED_PRODUCTS) == 256
    assert [r[0] for r in SPACE_SAVED_PRODUCTS if r[5] != r[6]] == ["PM0191"]
    assert {g: sum(row[0] == g for row in SPACE_DESIGN_CASES) for g in
            ("candidate_title", "space_boundary", "designed_example")} == {
                "candidate_title": 44, "space_boundary": 40, "designed_example": 12}


@pytest.mark.parametrize("group,variant,name,expected", SPACE_DESIGN_CASES)
def test_space_96_designed_inputs(group, variant, name, expected):
    sk, ex, works = space_saved_dictionary()
    pokemon = works["PM0048"]
    assert pokemon == works["PM0200"]
    for code, (search, exclude) in SPACE_CANDIDATE_DICTIONARY.items():
        sk[code], ex[code], works[code] = list(search), list(exclude), pokemon
    for code, (search, exclude) in SPACE_DESIGN_OVERRIDES.items():
        sk[code], ex[code] = list(search), list(exclude)
    actual = match_pid_with_work(name, list(sk), sk, ex,
                                 work_id="other-work" if variant == "wrong_work" else pokemon,
                                 product_work_ids=works)
    if expected is None:
        assert not actual[2]
    else:
        assert actual[0] == expected and actual[2] and actual[3] == [expected]


@pytest.mark.parametrize("keyword,name,expected", [
    ("スターターセットV草", "スターターセットV 草", True),
    ("スターターセットV草", "スターターセットＶ　草", True),
    ("スターターセットV草", "スターターセットV  草", True),
    ("商品漢字", "商品 漢字", True),
    ("商品㐀", "商品 㐀", True),
    ("スターターセットV草", "スターターセットV\n草", False),
    ("スターターセットV草", "スターターセットV\r草", False),
    ("スターターセットV草", "スターターセットV\t草", False),
    ("スターターセットV草", "スターターセットV\u00a0草", False),
    ("スターターセットV草", "スターターセットV 草 10箱", False),
    ("スターターセットV草", "草 スターターセットV", False),
    ("スターターセットV草", "限定スターターセットV 草", False),
    ("スターターセットV 草", "スターターセットV 草", False),
    ("スターターセットV　草", "スターターセットV 草", False),
    ("スターターセットV\t草", "スターターセットV 草", False),
    ("EB01", "EB 01", False),
    ("ＥＢ０１", "ＥＢ ０１", False),
    ("", "", False),
])
def test_space_search_only_predicate(keyword, name, expected):
    from app.services.tcg_analyzer_svc import match_product_name_space

    assert match_product_name_space(keyword, normalize_en(name)) is expected


@pytest.mark.parametrize("state,memo,work,category,expected", [
    ("", "", "pokemon", "Box", True),
    ("", "", None, "Box", True),
    ("", "", "onepiece", "Box", False),
    ("PSA10", "", "pokemon", "Box", False),
    ("", "SAR", "pokemon", "Case", False),
    ("限定", "", "pokemon", "Box", False),
    ("", "限定", "pokemon", "Box", False),
    ("限", "定", "pokemon", "Box", True),
])
def test_space_work_category_and_exclusion_guards(state, memo, work, category, expected):
    actual = match_pid_with_work("スターターセットV 草", ["A"], {"A": ["スターターセットV草"]},
                                 {"A": ["限定"]}, work_id=work, product_work_ids={"A": "pokemon"},
                                 raw_state=state, raw_memo=memo, product_category_classes={"A": category})
    assert actual[2] is expected


@pytest.mark.parametrize("name,state,memo", [
    ("別商品", "スターターセットV 草", ""),
    ("別商品", "", "スターターセットV 草"),
    ("スターターセットV", "草", ""),
    ("スターターセットV", "", "草"),
])
def test_space_never_uses_state_or_memo_as_search(name, state, memo):
    assert match_pid_with_work(name, ["A"], {"A": ["スターターセットV草"]}, {},
                               work_id=None, product_work_ids={"A": "pokemon"},
                               raw_state=state, raw_memo=memo) == (None, "NONE", False, [])


def test_space_ordinary_match_precedes_longer_additional_keyword():
    for keywords in [["スターターセットV草", "スターターセット"],
                     ["スターターセット", "スターターセットV草"]]:
        assert match_pid_with_work("スターターセットV 草", ["A"], {"A": keywords}, {},
                                   work_id=None, product_work_ids={"A": "pokemon"}) == (
                                       "A", "WORK:UNKNOWN|SK:スターターセット", True, ["A"])


def test_space_normal_priority_is_per_product_not_global():
    actual = match_pid_with_work("スターターセットV 草", ["normal", "space"],
                                 {"normal": ["スターターセット"], "space": ["スターターセットV草"]}, {},
                                 work_id=None, product_work_ids={})
    assert actual == ("space", "WORK:UNKNOWN|MULTI(PM.space/PM.normal):要確認", False, ["space", "normal"])


@pytest.mark.parametrize("name,codes,search,exclude,expected", [
    ("商品", [], {}, {}, (None, "NONE", False, [])),
    ("商品", ["A"], {"A": ["別"]}, {}, (None, "NONE", False, [])),
    ("商品", ["A"], {"A": ["商品"]}, {"A": ["商品"]}, (None, "NONE", False, [])),
    ("商品甲", ["A"], {"A": ["商品", "商品甲"]}, {}, ("A", "SK:商品", True, ["A"])),
    ("商品甲", ["B", "A"], {"A": ["商品"], "B": ["商品"]}, {},
     ("B", "MULTI(PM.B/PM.A):要確認", False, ["B", "A"])),
    ("商品甲", ["A", "B"], {"A": ["商品"], "B": ["商品甲"]}, {},
     ("B", "MULTI(PM.B/PM.A):要確認", False, ["B", "A"])),
    ("商" * 120, ["A"], {"A": ["商" * 120]}, {}, ("A", "SK:" + "商" * 97, True, ["A"])),
    ("商品", ["A", "B", "C", "D", "E", "F"], {c: ["商品"] for c in "ABCDEF"}, {},
     ("A", "MULTI(PM.A/PM.B/PM.C/PM.D/PM.E):要確認", False, list("ABCDEF"))),
    ("商品", ["A" * 110, "B"], {"A" * 110: ["商品"], "B": ["商品"]}, {},
     ("A" * 110, "MULTI(PM." + "A" * 91, False, ["A" * 110, "B"])),
])
def test_space_legacy_reducer_full_tuple_contract(name, codes, search, exclude, expected):
    assert match_pid_name_first(name, codes, search, exclude) == expected
