"""Anonymous fixed acceptance cases from reviewed design section 19.7."""
import pytest

from app.services.tcg_empty_box_rules import classify_empty_box

CASES = [
    (("ポケモンカートンの空箱", "", ""), "positive"),
    (("25thアニバーサリー 空箱", "", ""), "positive"),
    (("空箱のみ", "", ""), "positive"), ((" 空箱 ", "", ""), "positive"),
    *((((value, "", ""), "none")) for value in ("空箱ではない", "空箱ではありません", "空箱なし", "空箱無し")),
    *((((value, "", ""), "ambiguous")) for value in (
        "空箱ではないか", "空箱ではないとは言えない", "おそらく空箱ではない", "空箱かもしれない",
        "空箱も付属", "空箱と中身入り", "空箱付き", "空箱あります", "空箱あり", "空箱と空箱")),
    *((((value, "", ""), "none")) for value in ("通常品", "ダメージ品", "残り8箱のみ", "箱のみ本無し", "サプライのみ")),
    (("空箱", "空箱ではない", ""), "ambiguous"),
    (("通常商品", "", "空箱"), "positive"),
    (("通常商品", "空箱", "プロモ同梱説明"), "positive"),
]


@pytest.mark.parametrize("values, expected", CASES)
def test_fixed_classification(values, expected):
    assert classify_empty_box(*values) == expected
