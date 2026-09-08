"""
キーワード品質検査（R1〜R7）の単体テスト。DB接続不要。

設計: docs/handoff/tcg-keyword-quality/design.md
recon: docs/handoff/tcg-keyword-quality/recon.md
対象ADR: ADR-154

入力は load_product_keywords が返すのと同じ形の辞書2つと、有効商品コードの集合。
"""
from __future__ import annotations

from app.services.tcg_keyword_lint import (
    STOP,
    WARN,
    check_r1_empty_search,
    check_r2_short_tokens,
    check_r3_shared_kw,
    check_r4_self_kill,
    check_r5_piggyback,
    check_r6_dup_in_product,
    check_r7_spaced_ja,
    run_all,
)


class TestR1EmptySearch:
    """R1: 有効商品に検索語が1つも無い（停止）"""

    def test_detects_product_without_keywords(self):
        assert check_r1_empty_search(["PM0001", "PM0002"], {"PM0001": ["ポケモン"]}) == ["PM0002"]

    def test_clean_when_all_have_keywords(self):
        assert check_r1_empty_search(["PM0001"], {"PM0001": ["ポケモン"]}) == []


class TestR2ShortTokens:
    """R2: 日本語混じり語のトークン長（1文字=停止・2文字=警告）"""

    def test_one_char_japanese_is_stop(self):
        stop, warn = check_r2_short_tokens({"PM0201": ["枕"]})
        assert stop == ["PM0201:枕"]
        assert warn == []

    def test_two_char_japanese_is_warn(self):
        stop, warn = check_r2_short_tokens({"PM0060": ["白銀"]})
        assert stop == []
        assert warn == ["PM0060:白銀"]

    def test_ascii_short_is_not_flagged(self):
        stop, warn = check_r2_short_tokens({"PM0007": ["AR"]})
        assert stop == []
        assert warn == []

    def test_long_japanese_is_clean(self):
        stop, warn = check_r2_short_tokens({"PM0098": ["クレイバースト"]})
        assert stop == []
        assert warn == []


class TestR3SharedKw:
    """R3: 同じ語が2商品以上（停止）"""

    def test_detects_shared_keyword(self):
        out = check_r3_shared_kw({"PM0007": ["AR"], "PM0008": ["ar"], "PM0009": ["AR"]})
        assert len(out) == 1
        assert "PM0007" in out[0] and "PM0008" in out[0] and "PM0009" in out[0]

    def test_clean_when_unique(self):
        assert check_r3_shared_kw({"PM0007": ["AR"], "PM0008": ["SR"]}) == []


class TestR4SelfKill:
    """R4: 除外語が自商品の検索語を殺す（停止）"""

    def test_detects_self_kill(self):
        out = check_r4_self_kill(
            {"PM0159": ["熱風のアリーナ プロモ"]}, {"PM0159": ["熱風のアリーナ"]}
        )
        assert len(out) == 1
        assert "PM0159" in out[0]

    def test_clean_when_exclude_does_not_match(self):
        out = check_r4_self_kill({"PM0159": ["熱風のアリーナ"]}, {"PM0159": ["白銀のランス"]})
        assert out == []


class TestR5Piggyback:
    """R5: 相乗り（警告）"""

    def test_detects_unguarded_piggyback(self):
        out = check_r5_piggyback(
            {"PM0047": ["ソード"], "PM0048": ["ソードとシールド"]}, {}
        )
        assert len(out) == 1
        assert "PM0047" in out[0]

    def test_guarded_by_exclude_is_clean(self):
        out = check_r5_piggyback(
            {"PM0047": ["ソード"], "PM0048": ["ソードとシールド"]},
            {"PM0047": ["シールド"]},
        )
        assert out == []


class TestR6DupInProduct:
    """R6: 同一商品内の重複（停止）"""

    def test_detects_case_only_difference(self):
        out = check_r6_dup_in_product({"PM0069": ["切手Box", "切手BOX"]})
        assert len(out) == 1
        assert "PM0069" in out[0]

    def test_clean_when_distinct(self):
        assert check_r6_dup_in_product({"PM0069": ["切手Box", "切手カートン"]}) == []


class TestR7SpacedJa:
    """R7: 空白を含む日本語混じり語（情報）"""

    def test_detects_spaced_japanese(self):
        assert check_r7_spaced_ja({"PM0003": ["RRR バルク"]}) == ["PM0003:RRR バルク"]

    def test_no_space_is_clean(self):
        assert check_r7_spaced_ja({"PM0003": ["RRRバルク"]}) == []


class TestRunAll:
    """run_all: 停止規則があれば exit_code=1、警告だけなら 0"""

    def test_stop_when_r1_violated(self):
        res = run_all(["PM0001"], {}, {})
        assert res["exit_code"] == 1
        assert "R1" in res["stop_rules"]

    def test_warn_only_does_not_stop(self):
        res = run_all(["PM0060"], {"PM0060": ["白銀"]}, {})
        assert res["exit_code"] == 0
        assert res["stop_rules"] == []
        assert res["findings"]["R2-warn"][0] == WARN

    def test_clean_input_exits_zero(self):
        res = run_all(["PM0098"], {"PM0098": ["クレイバースト"]}, {})
        assert res["exit_code"] == 0
        assert res["findings"]["R1"][0] == STOP
