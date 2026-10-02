"""offer_type_ship_timing.extract_offer_type_ship_timing の単体テスト。

ADR-093 Phase 3b: 区分(在庫/予約) / 発送日(ship_timing) の行内自動判定。

2026-10-02: Discord 在庫取り込み機能（inventory_parser.py）削除に伴い、
backend/app/services/offer_type_ship_timing.py へ移設した
extract_offer_type_ship_timing（旧 _extract_offer_type_ship_timing）のテストを
backend/tests/test_inventory_parser_rule.py（削除済み）から移設した。
経緯: docs/handoff/remove-discord-inventory-parse/design.md
"""
from __future__ import annotations

from app.services.offer_type_ship_timing import extract_offer_type_ship_timing


class TestOfferTypeShipTimingDetection:
    """`extract_offer_type_ship_timing` (pure function) の検出ルール。"""

    def test_in_stock_default_none(self):
        """予約/発送日キーワードが無ければ (None, None) = 在庫扱い。"""
        assert extract_offer_type_ship_timing("ニンジャスピナー 50BOX@11,900円") == (None, None)

    def test_preorder_keyword_without_timing_is_other(self):
        """予約語のみ（発送日不明）→ pre_order / other。"""
        assert extract_offer_type_ship_timing("【予約】新弾BOX @12,000") == ("pre_order", "other")

    def test_preorder_on_release(self):
        assert extract_offer_type_ship_timing("予約 発売日発送 BOX") == ("pre_order", "on_release")

    def test_ship_timing_1day_before(self):
        assert extract_offer_type_ship_timing("予約商品 発売1日前発送") == ("pre_order", "1day_before")

    def test_ship_timing_2day_before_takes_priority(self):
        """「2日前」は「1日前」より優先して判定される。"""
        assert extract_offer_type_ship_timing("予約 発売2日前発送") == ("pre_order", "2day_before")

    def test_ship_timing_implies_preorder(self):
        """発送日指定だけでも予約品とみなす。"""
        assert extract_offer_type_ship_timing("発売日発送 BOX @10,000") == ("pre_order", "on_release")

    def test_digit_boundary_no_false_match(self):
        """数字境界: 「発売12日前」の末尾 '2日前' を ship_timing に誤判定しない（Reviewer PR#1445）。"""
        assert extract_offer_type_ship_timing("発売12日前発送 BOX @10,000") == (None, None)
