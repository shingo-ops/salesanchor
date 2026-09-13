"""Offline guard contracts. No database or network clients are imported."""
import ast
import importlib.util
import re
import unittest
from pathlib import Path
from typing import Optional

spec = importlib.util.spec_from_file_location(
    "guards", Path(__file__).parents[1] / "app/services/tcg_product_guards.py")
assert spec and spec.loader
guards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guards)
WORKS = [
    dict(id="onepiece", display_name="One Piece", alt_name="ワンピース"),
    dict(id="pokemon", display_name="Pokemon", alt_name="ポケモン"),
    dict(id="gundam", display_name="GUNDAM", alt_name="ガンダム"),
    dict(id="dragon", display_name="Dragon Ball", alt_name="ドラゴンボール"),
]


class ProductGuardTests(unittest.TestCase):
    def test_single_markers(self):
        for text in ["SAR", "ARカード", "PSA10", "PSA 9", "ＰＳＡ１０", "PSA7", "PSA8", "PSA6", "ＡＲ", "PSA-10", "PSA9.5"]:
            with self.subTest(text=text):
                self.assertIsNotNone(guards.single_card_marker(text))

    def test_normal_names_are_not_single_markers(self):
        for text in ["VSTARユニバース", "STAR", "SARAH", "CHARIZARD", "HARUKAZE", "通常BOX", "ARCADE"]:
            with self.subTest(text=text):
                self.assertIsNone(guards.single_card_marker(text))
        self.assertIsNone(guards.single_card_marker("S", "ARCADE"))

    def test_fields_independent(self):
        self.assertIsNotNone(guards.single_card_marker("商品", "", "PSA10"))
        self.assertIsNone(guards.single_card_marker("P", "SA", "10"))

    def test_observed_headings(self):
        for text in ["【ワンピース】", "【ワンピ在庫商品】", "🟡ONE PIECE在庫🟡", "ワンピースBOX カートン", "【ワンピースカードゲーム】"]:
            with self.subTest(text=text):
                self.assertEqual(guards.work_heading_evidence(text+"\nOP-13", 2, 2, WORKS), ("onepiece", 1))

    def test_new_work_ends_scope(self):
        self.assertEqual(guards.work_heading_evidence("ワンピース\n【ガンダム】\nEB01", 3, 3, WORKS), ("gundam", 2))

    def test_unknown_and_mixed_sections_end_scope(self):
        for text in ["【その他】", "【未知作品】", "ワンピース・ガンダム", "✨未知作品✨"]:
            with self.subTest(text=text):
                self.assertIsNone(guards.work_heading_evidence("ワンピース\n"+text+"\nEB01", 3, 3, WORKS))

    def test_product_is_not_heading(self):
        for text in ["ワンピース OP-13", "ワンピース 1000円", "ワンピース/ガンダム", "OP-13"]:
            self.assertIsNone(guards.work_heading_evidence(text+"\nEB01", 2, 2, WORKS))

    def test_future_or_invalid_heading(self):
        self.assertIsNone(guards.work_heading_evidence("OP13\nワンピース", 1, 1, WORKS))
        self.assertIsNone(guards.work_heading_evidence("ワンピース\nOP13", 0, 2, WORKS))
        self.assertIsNone(guards.work_heading_evidence("ワンピース\nOP13", 2, 3, WORKS))

    def test_ambiguous_work_master(self):
        works = WORKS + [dict(id="other", display_name="ワンピース", alt_name=None)]
        self.assertIsNone(guards.work_heading_evidence("ワンピース\nOP13", 2, 2, works))


def load_matching_functions():
    """Execute production pure functions without importing the DB service."""
    source = (Path(__file__).parents[1] / "app/services/tcg_analyzer_svc.py").read_text()
    names = {"normalize_en", "token_and_match", "match_one_kw", "match_keyword",
             "match_pid_name_first", "is_model_keyword", "match_pid_with_work",
             "resolve_work_evidence", "match_product_keyword",
             "select_product_candidates", "match_product_name_space", "collapse_product_spaces"}
    nodes = [n for n in ast.parse(source).body
             if isinstance(n, ast.FunctionDef) and n.name in names]
    namespace = dict(re=re, Optional=Optional, _FULLWIDTH_OFFSET=0xFEE0,
                     _RE_PURE_ASCII=re.compile(r"^[\x20-\x7e]+$"),
                     _RE_WORD_BOUNDARY_TEMPLATE=r"(?<![a-z]){word}(?![a-z])",
                     _MODEL_KEYWORD_RE=re.compile(r"[a-z0-9]+(?:\s*[-/]\s*[a-z0-9]+)*"),
                     single_card_marker=guards.single_card_marker,
                     work_heading_evidence=guards.work_heading_evidence)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "production-pure-functions", "exec"), namespace)
    return namespace


class MatchingConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.functions = load_matching_functions()

    def test_legacy_and_empty_evidence_use_heading(self):
        f = self.functions["resolve_work_evidence"]
        for work, span in [(None, None), ("", "")]:
            self.assertEqual(f("EB01", "ワンピース\nEB01", 2, 2, work, span, WORKS), "onepiece")

    def test_invalid_citations_not_repaired(self):
        f = self.functions["resolve_work_evidence"]
        for work, span in [(None, ""), ("", None), ("ワンピース", ""),
                           ("", "L1"), ("ワンピース", "L999"), ("ガンダム", "L1")]:
            with self.subTest(work=work, span=span):
                self.assertIsNone(f("EB01", "ワンピース\nEB01", 2, 2, work, span, WORKS))

    def test_work_and_box_filters_connected(self):
        f = self.functions["match_pid_with_work"]
        kws = {"box": ["EB01", "タイトル"], "single": ["カード"]}
        common = dict(work_id="onepiece", product_work_ids={"box": "onepiece", "single": "onepiece"},
                      product_category_classes={"box": "Box", "single": "Single"})
        self.assertTrue(f("EB01", list(kws), kws, {}, **common)[2])
        for word in ["SAR", "AR", "PSA10", "PSA7"]:
            for field in ["raw_state", "raw_memo"]:
                self.assertFalse(f("EB01", list(kws), kws, {}, **common, **{field: word})[2])
            self.assertFalse(f("タイトル " + word, list(kws), kws, {}, **common)[2])
        self.assertEqual(f("カード PSA10", list(kws), kws, {}, **common)[0], "single")
        common["work_id"] = "gundam"
        self.assertFalse(f("EB01", list(kws), kws, {}, **common)[2])
        common["work_id"] = None
        self.assertFalse(f("EB01", list(kws), kws, {}, **common)[2])


if __name__ == "__main__":
    unittest.main()
