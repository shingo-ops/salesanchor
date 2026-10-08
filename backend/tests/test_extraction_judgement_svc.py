"""extraction_judgement_svc の単体テスト（純粋関数・DB/LLM 非依存）。

設計: docs/handoff/gemini-extract-role-split/design.md §4・§5
"""
from app.services.extraction_judgement_svc import (
    MatchResult,
    ProductEntry,
    block_text,
    match_product,
    normalize_for_match,
    product_match_text,
    ship_timing,
    verify_copied,
)


class TestNormalizeForMatch:
    def test_fullwidth_alnum_becomes_halfwidth(self):
        # Arrange
        text = "ＡＢ１２"
        # Act
        result = normalize_for_match(text)
        # Assert
        assert result == "ab12"

    def test_uppercase_becomes_lowercase(self):
        # Arrange
        text = "PSA10"
        # Act
        result = normalize_for_match(text)
        # Assert
        assert result == "psa10"

    def test_katakana_becomes_hiragana(self):
        # Arrange
        text = "ワンピース"
        # Act
        result = normalize_for_match(text)
        # Assert
        assert result == "わんぴーす"

    def test_whitespace_removed(self):
        # Arrange
        text = "ワン ピース\tBOX　カートン"
        # Act
        result = normalize_for_match(text)
        # Assert
        assert result == "わんぴーすboxかーとん"

    def test_punctuation_and_symbols_removed(self):
        # Arrange
        text = "【ワンピース】BOX@10,000円!"
        # Act
        result = normalize_for_match(text)
        # Assert
        assert result == "わんぴーすbox10000円"

    def test_digits_and_letters_kept(self):
        # Arrange
        text = "OP-01 BOX123"
        # Act
        result = normalize_for_match(text)
        # Assert
        assert result == "op01box123"


class TestBlockText:
    def test_within_range_returns_joined_lines(self):
        # Arrange
        raw_text = "line1\nline2\nline3\nline4"
        # Act
        result = block_text(raw_text, 2, 3)
        # Assert
        assert result == "line2\nline3"

    def test_single_line_range(self):
        # Arrange
        raw_text = "line1\nline2\nline3"
        # Act
        result = block_text(raw_text, 1, 1)
        # Assert
        assert result == "line1"

    def test_out_of_range_start_below_1_returns_empty(self):
        # Arrange
        raw_text = "line1\nline2"
        # Act
        result = block_text(raw_text, 0, 1)
        # Assert
        assert result == ""

    def test_out_of_range_end_beyond_length_returns_empty(self):
        # Arrange
        raw_text = "line1\nline2"
        # Act
        result = block_text(raw_text, 1, 3)
        # Assert
        assert result == ""

    def test_start_greater_than_end_returns_empty(self):
        # Arrange
        raw_text = "line1\nline2\nline3"
        # Act
        result = block_text(raw_text, 3, 2)
        # Assert
        assert result == ""


def _product(
    id_=1,
    product_code=None,
    mark=None,
    work_id=None,
    search_keywords=(),
    exclude_keywords=(),
):
    return ProductEntry(
        id=id_,
        product_code=product_code,
        mark=mark,
        work_id=work_id,
        search_keywords=tuple(search_keywords),
        exclude_keywords=tuple(exclude_keywords),
    )


class TestMatchProductKeywordAnd:
    def test_all_words_present_matches(self):
        # Arrange
        product = _product(id_=1, work_id=10, search_keywords=("ワンピース BOX",))
        block = "ワンピース BOX 新品未開封"
        # Act
        result = match_product(block, [product])
        # Assert
        assert result.status == "matched"
        assert result.product_id == 1
        assert result.work_id == 10
        assert result.basis == "SK:ワンピース BOX"

    def test_missing_one_word_does_not_match(self):
        # Arrange
        product = _product(id_=1, search_keywords=("ワンピース BOX",))
        block = "ワンピース 新品未開封"
        # Act
        result = match_product(block, [product])
        # Assert
        assert result.status == "unmatched"
        assert result.product_id is None


class TestMatchProductExclude:
    def test_exclude_keyword_removes_candidate_and_is_recorded(self):
        # Arrange
        product = _product(
            id_=1,
            search_keywords=("ワンピース BOX",),
            exclude_keywords=("シュリ無",),
        )
        block = "ワンピース BOX シュリ無"
        # Act
        result = match_product(block, [product])
        # Assert
        assert result.status == "unmatched"
        assert result.excluded_by[1] == ("シュリ無",)


class TestMatchProductCode:
    def test_matches_by_product_code(self):
        # Arrange
        product = _product(id_=1, product_code="OP-01", work_id=5)
        block = "OP-01 新品未開封 BOX"
        # Act
        result = match_product(block, [product])
        # Assert
        assert result.status == "matched"
        assert result.product_id == 1
        assert result.work_id == 5
        assert result.basis == "RAWCODE"

    def test_matches_by_mark(self):
        # Arrange
        product = _product(id_=2, mark="ONP01", work_id=7)
        block = "ONP01BOX 新品未開封"
        # Act
        result = match_product(block, [product])
        # Assert
        assert result.status == "matched"
        assert result.product_id == 2
        assert result.work_id == 7
        assert result.basis == "RAWCODE"


class TestMatchProductCandidateCount:
    def test_zero_candidates_is_unmatched(self):
        # Arrange
        product = _product(id_=1, search_keywords=("該当しないワード",))
        block = "無関係なテキスト"
        # Act
        result = match_product(block, [product])
        # Assert
        assert result.status == "unmatched"
        assert result.candidates == ()
        assert "一致する検索ワード・品番がない" in result.reason

    def test_two_candidates_is_ambiguous_without_longest_match_tiebreak(self):
        # Arrange
        short_product = _product(id_=1, search_keywords=("ワンピース",))
        long_product = _product(id_=2, search_keywords=("ワンピース BOX 新品",))
        block = "ワンピース BOX 新品未開封"
        # Act
        result = match_product(block, [short_product, long_product])
        # Assert
        assert result.status == "ambiguous"
        assert result.product_id is None
        assert set(result.candidates) == {1, 2}
        assert "候補2件" in result.reason
        assert "1" in result.reason and "2" in result.reason


class TestVerifyCopied:
    def test_value_none_literal_is_true(self):
        # Arrange / Act / Assert
        assert verify_copied("none", "ブロック本文") is True
        assert verify_copied("None", "ブロック本文") is True
        assert verify_copied("NONE", "ブロック本文") is True

    def test_empty_value_is_true(self):
        # Arrange / Act / Assert
        assert verify_copied("", "ブロック本文") is True

    def test_normalized_substring_match_is_true(self):
        # Arrange
        value = "新品"
        block = "【ワンピース】新品未開封 BOX"
        # Act / Assert
        assert verify_copied(value, block) is True

    def test_digits_only_match_is_true(self):
        # Arrange
        value = "価格:10,000円"
        block = "ワンピースBOX@10000円"
        # Act / Assert
        assert verify_copied(value, block) is True

    def test_no_match_is_false(self):
        # Arrange
        value = "ヴァイスシュヴァルツ"
        block = "ワンピース BOX 新品未開封"
        # Act / Assert
        assert verify_copied(value, block) is False


class TestShipTiming:
    def test_uses_inventory_parser_and_returns_first_non_none_result(self):
        # Arrange: inventory_parser.test_inventory_parser_rule.py の既存ケースと同じ結果になること
        # (予約商品 発売1日前発送) -> ("pre_order", "1day_before")
        block = "在庫あり 通常品\n予約商品 発売1日前発送\n次の行は読まれない"
        # Act
        result = ship_timing(block)
        # Assert
        assert result == ("pre_order", "1day_before")

    def test_returns_none_none_when_no_line_matches(self):
        # Arrange
        block = "在庫あり 通常品\n何もない行"
        # Act
        result = ship_timing(block)
        # Assert
        assert result == (None, None)


def test_match_result_is_frozen():
    # Arrange
    result = MatchResult(
        status="unmatched",
        product_id=None,
        work_id=None,
        candidates=(),
        matched_keywords={},
        excluded_by={},
        basis="",
        reason="",
    )
    # Act / Assert
    try:
        result.status = "matched"  # type: ignore[misc]
        assert False, "frozen dataclass のはずが変更できた"
    except AttributeError:
        pass


def test_product_entry_is_frozen():
    # Arrange
    product = _product(id_=1)
    # Act / Assert
    try:
        product.id = 2  # type: ignore[misc]
        assert False, "frozen dataclass のはずが変更できた"
    except AttributeError:
        pass


# ---------------------------------------------------------------------------
# 価格・数量の決定（design price-qty-resolver-design.md §4・§5・§10）
# ---------------------------------------------------------------------------

import pytest  # noqa: E402

from app.services.extraction_judgement_svc import (  # noqa: E402
    PriceQtyResult,
    order_from_pattern,
    resolve_price_quantity,
)

# 本番 public.units / public.unit_aliases の読み取り結果（2026-09-30, canonical と alias_text の和集合・45語）。
_UNIT_ALIASES = (
    "BOX",
    "Booklet",
    "Box",
    "CARTON",
    "CASE",
    "CT",
    "Carton",
    "Case",
    "Ct",
    "MasterCarton",
    "OX",
    "PACK",
    "PCS",
    "PIECE",
    "Pack",
    "Pcs",
    "Piece",
    "SET",
    "Set",
    "box",
    "carton",
    "case",
    "ct",
    "pack",
    "pcs",
    "piece",
    "set",
    "カートン",
    "ケース",
    "セット",
    "パック",
    "ボックス",
    "マスターカートン",
    "個",
    "冊",
    "本",
    "枚",
    "点",
    "箱",
    "ｶートン",
    "ｹース",
    "ｾｯﾄ",
    "ﾊﾟｯｸ",
    "ﾎﾞｯｸｽ",
    "ﾏｽﾀｰｶｰﾄﾝ",
)

# (block, gemini_price, gemini_quantity, order, price, quantity, basis, reasons, product_name)
_PRICE_QTY_CASES = [
    ("27,500×18BOX", "27,500", "18BOX", None, 27500, 18, "marker", (), None),
    ("40個＠27500円", "27500円", "40個", None, 27500, 40, "marker", (), None),
    ("在庫50/13500円", "13500円", "50", None, 13500, 50, "marker", (), None),
    ("@19,000円/在庫15※潰れ破れなどあり", "19,000円", "15", None, 19000, 15, "marker", (), None),
    ("15BOX：19,500", "19,500", "15BOX", None, 19500, 15, "marker", (), None),
    ("■単価（税込）：￥27,500\n■在庫数：17", "￥27,500", "17", None, 27500, 17, "marker", (), None),
    ("ボックス/¥25,000\n残り200", "¥25,000", "200", None, 25000, 200, "marker", (), None),
    ("10900@152", "10900", "152", "price_first", 10900, 152, "rule", (), None),
    ("ストームエメラルダ 100@11300", "11300", "100", "quantity_first", 11300, 100, "rule", (), None),
    ("400＠518", "400", "518", "price_first", 400, 518, "rule", (), None),
    ("24万　在庫20", "24万", "20", None, 240000, 20, "marker", (), None),
    ("30円×3,000枚", "30円", "3,000枚", None, 30, 3000, "marker", (), None),
    ("¥4,0000/冊\n15冊", "¥4,0000", "15冊", None, 40000, 15, "marker", ("irregular_comma",), None),
    ("12,000円 10月入荷", "12,000円", None, None, 12000, None, "marker", (), None),
    ("12,000円 3営業日", "12,000円", "none", None, 12000, None, "marker", (), None),
    ("12,000円 在庫50", "12,000円", "none", None, 12000, 50, "marker", ("gemini_disagrees",), None),
    ("27,500x18BOX", "27,500", "18BOX", None, 27500, 18, "marker", (), None),
    ("12,000円 2025年", "12,000円", "2025", None, 12000, 2025, "marker", ("quantity_unmarked",), None),
    ("@11,500円 36", "11,500円", "36", None, 11500, 36, "marker", ("quantity_unmarked",), None),
    ("27,500x18", "27,500", "18", "price_first", 27500, 18, "rule", (), None),
    (
        "@150,000円/在庫2\n@12,100円/在庫48",
        "150,000円／12,100円", "2／48", None, None, None, "none", ("multiple_values",), None,
    ),
    ("10900@152", "10900", "152", None, None, None, "none", ("no_order_rule",), None),
    ("OP-17\n12,000×11BOX", "12,000", "11BOX", None, 12000, 11, "marker", (), None),
    ("23500円/ 1BOX\n60点", "23500円", "60点", None, 23500, 60, "marker", (), None),
    ("¥280,000/1ケース\n5カートン", "¥280,000", "5カートン", None, 280000, 5, "marker", (), None),
    (
        "ARバルク、100枚セット\n@13000円 在庫1", "13000円", "1", None, 13000, 1, "marker", (),
        "ARバルク、100枚セット",
    ),
    ("●アビスアイ　¥8,500　在庫38個", "¥8,500", "38個", None, 8500, 38, "marker", (), "アビスアイ"),
    (
        "ストームエメラルダ 100@11300", "11300", "100", "quantity_first", 11300, 100, "rule", (),
        "ストームエメラルダ",
    ),
    ("500packs/330円（未サーチ）", "330円", "500packs", None, 330, None, "marker", ("unresolved",), None),

]


@pytest.mark.parametrize(
    "block,g_price,g_qty,order,price,quantity,basis,reasons,product_name", _PRICE_QTY_CASES
)
def test_resolve_price_quantity_design_table(
    block, g_price, g_qty, order, price, quantity, basis, reasons, product_name
):
    # Act
    result = resolve_price_quantity(
        block, gemini_price=g_price, gemini_quantity=g_qty, unit_aliases=_UNIT_ALIASES, order=order,
        gemini_product_name=product_name,
    )

    # Assert
    assert result.price == price
    assert result.quantity == quantity
    assert result.basis == basis
    assert result.reasons == reasons
    assert result.needs_review is bool(reasons)


def test_resolve_price_quantity_does_not_join_digits_of_multiple_values():
    result = resolve_price_quantity(
        "10,000／12,100", gemini_price="10,000／12,100", gemini_quantity=None,
        unit_aliases=_UNIT_ALIASES, order=None,
    )
    assert result.price != 1000012100
    assert isinstance(result, PriceQtyResult)


def test_resolve_price_quantity_none_when_gemini_has_no_values():
    result = resolve_price_quantity(
        "完売", gemini_price="none", gemini_quantity=None, unit_aliases=_UNIT_ALIASES, order=None
    )
    assert (result.price, result.quantity, result.basis, result.reasons) == (None, None, "none", ())
    assert result.needs_review is False


def test_resolve_price_quantity_reports_gemini_disagreement():
    result = resolve_price_quantity(
        "27,500円 18BOX", gemini_price="27,000", gemini_quantity="18BOX",
        unit_aliases=_UNIT_ALIASES, order=None,
    )
    assert "gemini_disagrees" in result.reasons


def test_resolve_price_quantity_flags_rule_vs_shape():
    result = resolve_price_quantity(
        "152@10,900", gemini_price="152", gemini_quantity="10,900",
        unit_aliases=_UNIT_ALIASES, order="price_first",
    )
    assert result.basis == "rule"
    assert "rule_vs_shape" in result.reasons


def test_resolve_price_quantity_unresolved_when_no_candidate():
    result = resolve_price_quantity(
        "商品 1500", gemini_price="1500", gemini_quantity=None, unit_aliases=_UNIT_ALIASES, order=None
    )
    assert result.reasons == ("unresolved",)


def test_resolve_price_quantity_unit_words_come_only_from_argument():
    block = "18BOX 27,500円"
    with_alias = resolve_price_quantity(
        block, gemini_price="27,500円", gemini_quantity="18", unit_aliases=("BOX",), order=None
    )
    without_alias = resolve_price_quantity(
        block, gemini_price="27,500円", gemini_quantity="18", unit_aliases=(), order=None
    )
    assert with_alias.quantity == 18
    assert without_alias.quantity != 18


@pytest.mark.parametrize(
    "pattern,expected",
    [
        ('["price","@","quantity"]', "price_first"),
        ('["quantity","@","price"]', "quantity_first"),
        ('["price","yen"]', None),
        ("price_at_qty", None),
        ("", None),
        (None, None),
        ('{"a":1}', None),
    ],
)
def test_order_from_pattern(pattern, expected):
    assert order_from_pattern(pattern) == expected


class TestProductMatchText:
    def test_name_in_block_is_appended_with_block_source(self):
        # Arrange
        block = "スノーハザード 3BOX@13,300円"
        # Act
        text, source = product_match_text(block, "■見出し", "スノーハザード")
        # Assert
        assert (text, source) == (block + "\nスノーハザード", "BLOCK")

    def test_name_only_in_heading_is_appended_with_heading_source(self):
        # Arrange
        block = "3BOX@13,300円[通常品]"
        heading = "■拡張パック「スノーハザード」(SV2P)"
        # Act
        text, source = product_match_text(block, heading, "拡張パック「スノーハザード」(SV2P)")
        # Assert
        assert (text, source) == (block + "\n拡張パック「スノーハザード」(SV2P)", "HEADING")

    def test_name_absent_from_both_is_not_added(self):
        # Arrange
        block = "3BOX@13,300円"
        # Act
        text, source = product_match_text(block, "■見出し", "作り話の商品名")
        # Assert
        assert (text, source) == (block, "NONE")

    @pytest.mark.parametrize("name", [None, "", "none", "None", "NONE", "  ", "「」"])
    def test_empty_or_none_name_returns_none_source(self, name):
        # Arrange
        block = "3BOX@13,300円"
        # Act
        text, source = product_match_text(block, "■見出し", name)
        # Assert
        assert (text, source) == (block, "NONE")

    def test_fullwidth_and_space_differences_still_match(self):
        # Arrange
        block = "ＳＶ２Ｐ　スノー ハザード 3BOX"
        # Act
        text, source = product_match_text(block, "", "sv2p スノーハザード")
        # Assert
        assert source == "BLOCK"
        assert text.endswith("\nsv2p スノーハザード")


class TestMatchProductShortBoundary:
    """短い値（2文字以下）・数字だけの値は、語の境界があるときだけ当たる（PR-3b）。"""

    def test_short_mark_does_not_hit_inside_english_word(self):
        # Arrange
        product = _product(id_=1, mark="M")
        # Act
        result = match_product("MEGA スペシャルセット 3BOX", [product])
        # Assert
        assert result.status == "unmatched"
        assert result.boundary_dropped == (1,)

    def test_short_mark_does_not_hit_inside_katakana_word(self):
        product = _product(id_=1, mark="M")
        # カタカナ語に英字の M は無いので、別の語中の m で確かめる
        result = match_product("アーセナルベース (mint)", [product])
        assert result.status == "unmatched"
        assert result.boundary_dropped == (1,)

    def test_short_keyword_token_does_not_hit_inside_word(self):
        product = _product(id_=2, search_keywords=("PP",))
        result = match_product("CHOPPER's フィギュア", [product])
        assert result.status == "unmatched"
        assert result.boundary_dropped == (2,)

    def test_digits_only_code_does_not_hit_inside_price(self):
        product = _product(id_=3, product_code="151")
        for block in ("151BOX 15,100円", "新品 15100"):
            result = match_product(block, [product])
            assert result.status == "unmatched"
            assert result.boundary_dropped == (3,)

    def test_short_mark_hits_when_delimited(self):
        product = _product(id_=1, mark="M")
        for block in ("[M] 新品", "M 新品", "新品 M"):
            result = match_product(block, [product])
            assert result.status == "matched"
            assert result.basis == "RAWCODE"
            assert result.boundary_dropped == ()

    def test_digits_code_hits_with_boundary(self):
        product = _product(id_=3, product_code="151")
        for block in ("151 カートン", "◆151", "151カートン"):
            result = match_product(block, [product])
            assert result.status == "matched"
            assert result.boundary_dropped == ()

    def test_long_alnum_code_keeps_substring_match(self):
        product = _product(id_=2, product_code="ONP01")
        result = match_product("ONP01BOX 新品", [product])
        assert result.status == "matched"
        assert result.boundary_dropped == ()

    def test_long_keyword_token_keeps_substring_match(self):
        product = _product(id_=2, search_keywords=("スノーハザード",))
        result = match_product("スノーハザードBOX", [product])
        assert result.status == "matched"
        assert result.boundary_dropped == ()

    def test_boundary_uses_nfkc_lowercase_and_hiragana(self):
        # 全角・大文字でも、値の前後が英数字でなければ境界あり
        product = _product(id_=1, mark="ｍ")
        assert match_product("（Ｍ）新品", [product]).status == "matched"
        assert match_product("ＭＥＧＡ", [product]).status == "unmatched"

    def test_whitespace_and_symbols_are_kept_for_boundary(self):
        # 空白・記号は消さない: 「1 5 1」「15-1」を 151 とみなさない
        product = _product(id_=3, product_code="151")
        assert match_product("15 1", [product]).status == "unmatched"

    def test_boundary_dropped_lists_only_products_dropped_by_boundary(self):
        short = _product(id_=1, mark="M")
        long_ = _product(id_=2, search_keywords=("スノーハザード",))
        result = match_product("スノーハザード MEGA", [short, long_])
        assert result.status == "matched"
        assert result.product_id == 2
        assert result.boundary_dropped == (1,)

    def test_boundary_dropped_empty_by_default(self):
        result = match_product("何もない", [_product(id_=1, mark="ZZ9")])
        assert result.boundary_dropped == ()

    def test_excluded_product_not_listed_in_boundary_dropped_when_it_would_be_excluded(self):
        # 境界が無くても除外ワードで落ちる商品は、境界のせいで外れたとは言えない
        short = _product(id_=1, mark="M", exclude_keywords=("MEGA",))
        result = match_product("MEGA", [short])
        assert result.boundary_dropped == ()


class TestMatchProductStrictCodes:
    """strict_codes=True：品番らしい値は、原文の書き方のまま前後が区切られているときだけ当たり。"""

    @staticmethod
    def _hits(text, products, **kwargs):
        return match_product(text, products, **kwargs).candidates

    def test_ex10_does_not_hit_inside_100_price(self):
        ex10 = _product(id_=1, mark="EX10")
        assert self._hits("バイオレットex 100@10700", [ex10], strict_codes=True) == ()
        assert self._hits("バイオレットex 100@10700", [ex10]) == (1,)

    def test_ex12_does_not_hit_across_line_break(self):
        ex12 = _product(id_=1, mark="EX12")
        text = "◆バイオレットex\n12BOX@11,300円"
        assert self._hits(text, [ex12], strict_codes=True) == ()
        assert self._hits(text, [ex12]) == (1,)

    def test_sv7_does_not_hit_sv7a_but_sv7a_does(self):
        sv7 = _product(id_=1, product_code="SV7")
        sv7a = _product(id_=2, product_code="SV7a")
        text = "◉ 楽園ドラゴーナ [SV7a]"
        assert self._hits(text, [sv7, sv7a], strict_codes=True) == (2,)
        assert self._hits(text, [sv7, sv7a]) == (1, 2)

    def test_ard_does_not_hit_inside_card(self):
        ard = _product(id_=1, mark="ARD")
        text = "ONE PIECE CARD THE BEST"
        assert self._hits(text, [ard], strict_codes=True) == ()
        assert self._hits(text, [ard]) == (1,)

    def test_rb01_does_not_hit_prb01_but_prb01_forms_do(self):
        rb01 = _product(id_=1, product_code="RB01")
        prb_dash = _product(id_=2, product_code="PRB-01")
        prb = _product(id_=3, product_code="PRB01")
        result = self._hits("◆PRB-01", [rb01, prb_dash, prb], strict_codes=True)
        assert result == (2, 3)

    def test_hyphen_and_no_hyphen_both_hit_either_form(self):
        dash = _product(id_=1, product_code="EB-01")
        plain = _product(id_=2, product_code="EB01")
        for text in ("◆EB-01", "EB01 メモリアル"):
            assert self._hits(text, [dash, plain], strict_codes=True) == (1, 2)

    def test_apostrophe_variants_hit(self):
        day = _product(id_=1, search_keywords=("DAY'25",))
        assert self._hits("DAY’25", [day], strict_codes=True) == (1,)

    def test_keyword_with_kana_keeps_existing_rule(self):
        title = _product(id_=1, search_keywords=("「Re:ゼロから始める異世界生活」Vol.4",))
        text = "Re:ゼロから始める異世界生活 Vol.4"
        assert self._hits(text, [title], strict_codes=True) == (1,)
        assert self._hits(text, [title]) == (1,)

    def test_short_and_digit_only_values_keep_existing_rule(self):
        short = _product(id_=1, mark="EX")
        digits = _product(id_=2, mark="2025")
        text = "EX 12025x"
        assert self._hits(text, [short, digits], strict_codes=True) == self._hits(text, [short, digits])

    def test_symbol_in_value_is_not_in_pattern_and_boundary_is_checked(self):
        sm5 = _product(id_=1, mark="SM5+")
        assert self._hits("SM5S", [sm5], strict_codes=True) == ()
        assert self._hits("SM5S", [sm5]) == (1,)

    def test_symbol_value_hits_when_written_with_plus(self):
        sm5 = _product(id_=1, mark="SM5+")
        assert self._hits("SM5+", [sm5], strict_codes=True) == (1,)
        assert self._hits("SM5＋", [sm5], strict_codes=True) == (1,)

    def test_default_output_is_identical_without_strict_codes(self):
        products = [
            _product(id_=1, mark="EX10"),
            _product(id_=2, product_code="RB01", search_keywords=("ワンピース BOX",)),
            _product(id_=3, mark="M"),
        ]
        text = "バイオレットex 100@10700 PRB-01 ワンピース BOX M"
        assert match_product(text, products) == match_product(text, products, strict_codes=False)
        assert match_product(text, products).candidates == (1, 2, 3)
