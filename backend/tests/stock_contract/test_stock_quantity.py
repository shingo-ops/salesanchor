"""Contract examples for the unconnected quantity component."""

import unittest
from decimal import Decimal

from app.services.tcg_stock_quantity import parse_stock_quantity


class StockQuantityTests(unittest.TestCase):
    def test_quantity_preservation(self):
        aliases = frozenset({"BOX", "カートン"})
        for raw, expected, unit in [
            ("", None, None), (" \t", None, None), ("0", "0", None),
            ("①", "1", None), ("残①カートン", "1", "カートン"),
            ("1,000", "1000", None), ("１２．５０", "12.50", None),
            ("残り 3 BOX", "3", "BOX"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(parse_stock_quantity(raw, aliases), {
                    "presence": "absent" if expected is None else "value",
                    "value": None if expected is None else Decimal(expected),
                    "unit_alias": unit, "review_reason": None,
                })

    def test_unsupported_quantities(self):
        for raw in [
            "10→残3", "1〜3", "1+2", "①②", "-1", "1e3", "1,00",
            "1.234", "1000000000000", "発送分①", "3未知単位",
            "+1", ".5", "1.", "1 000", "1①", "㉑", "NaN", "Infinity",
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(parse_stock_quantity(raw, frozenset({"BOX"})), {
                    "presence": "review", "value": None, "unit_alias": None,
                    "review_reason": "unsupported_quantity",
                })

    def test_boundaries_and_purity(self):
        aliases = frozenset({"BOX", "X", "ＢＯＸ"})
        original = aliases
        raw = "999999999999.99"
        first = parse_stock_quantity(raw, aliases)
        self.assertEqual(first["value"], Decimal(raw))
        self.assertEqual(first, parse_stock_quantity(raw, aliases))
        self.assertEqual(raw, "999999999999.99")
        self.assertEqual(aliases, original)
        self.assertEqual(parse_stock_quantity("1000000000000.00", aliases)["presence"], "review")
        self.assertEqual(parse_stock_quantity("3BOX", aliases)["unit_alias"], "BOX")
        self.assertEqual(parse_stock_quantity("３ＢＯＸ", aliases)["unit_alias"], "ＢＯＸ")
        self.assertEqual(parse_stock_quantity("⑳", aliases)["value"], Decimal(20))
        with self.assertRaises(ValueError):
            parse_stock_quantity("", frozenset({""}))
