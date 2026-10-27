#!/usr/bin/env python3
"""scripts/ci/check_rule_registry.py の試験（標準ライブラリのみ・一時フォルダで完結）。

実行: python3 scripts/tests/test_check_rule_registry.py -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ci", "check_rule_registry.py")

DOC = "禁止の決まりその1\n普通の説明\n必ず守る決まりその2\n"


def _item(id_, anchor, kind="gate", check="chk-a", extra=""):
    return (
        f'  - id: {id_}\n    source: docs/a.md\n    anchor: "{anchor}"\n    kind: {kind}\n'
        f'    check: "{check}"\n    when: ci\n    fixture: ""\n    evidence: "R2 で見本を置く"\n'
        f'    reason: ""\n{extra}'
    )


def _registry(items, not_rules=""):
    body = "words: 禁止|必ず\n\nrules:\n" + "".join(items) if items else "words: 禁止|必ず\n\nrules: []\n"
    return body + "\n" + (not_rules or "not_rules: []\n")


class RegistryCheck(unittest.TestCase):
    def _run(self, registry, doc=DOC, checks="chk-a\t15368\n", docs_list="docs/a.md\n"):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "docs", "specs", "rule-enforcement")
            os.makedirs(base)
            os.makedirs(os.path.join(d, "docs"), exist_ok=True)
            with open(os.path.join(d, "docs", "a.md"), "w", encoding="utf-8") as f:
                f.write(doc)
            for name, text in (("rules.yml", registry), ("rule-docs.txt", docs_list), ("required-checks.txt", checks)):
                with open(os.path.join(base, name), "w", encoding="utf-8") as f:
                    f.write(text)
            p = subprocess.run(
                [sys.executable, "-I", CHECK, "--root", d, "--json"],
                capture_output=True, text=True,
            )
            try:
                data = json.loads(p.stdout)
            except ValueError:
                data = None
            return p.returncode, data, p.stdout + p.stderr

    def _codes(self, data):
        return sorted({f["check"] for f in data["findings"] if f.get("severity") != "warn"})

    def test_pass(self):
        reg = _registry([_item("T1", "禁止の決まりその1"), _item("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 0, out)
        self.assertTrue(data["ok"])

    def test_unsorted_line_fails(self):
        reg = _registry([_item("T1", "禁止の決まりその1")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C1", self._codes(data))
        self.assertTrue(any(f.get("check") == "C1" and f.get("file") == "docs/a.md" and f.get("line") == 3 for f in data["findings"]))

    def test_vanished_anchor_fails(self):
        reg = _registry([_item("T1", "禁止の決まりその1"), _item("T2", "消えた文言")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C2", self._codes(data))

    def test_missing_field_fails(self):
        item = _item("T1", "禁止の決まりその1").replace('    check: "chk-a"\n', "")
        reg = _registry([item, _item("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C3", self._codes(data))

    def test_nonexistent_check_fails(self):
        reg = _registry([_item("T1", "禁止の決まりその1", check="chk-x"), _item("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C4", self._codes(data))

    def test_overlap_fails(self):
        reg = _registry([_item("T1", "禁止の決まり"), _item("T2", "禁止の決まりその1"), _item("T3", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C5", self._codes(data))


def _review(id_, anchor, kind="review", reason="人が見る", extra=""):
    r = f'    reason: "{reason}"\n' if reason is not None else ""
    return f'  - id: {id_}\n    source: docs/a.md\n    anchor: "{anchor}"\n    kind: {kind}\n{r}{extra}'


class RegistryCheckMore(unittest.TestCase):
    """台帳の読み込み・突き合わせの追加の試験（_run と _codes は上の RegistryCheck と同じ）。"""

    _run = RegistryCheck._run
    _codes = RegistryCheck._codes

    def test_anchors_list_covers_lines(self):
        reg = _registry(
            [
                "  - id: T1\n    source: docs/a.md\n    kind: review\n    reason: \"人が見る\"\n"
                "    anchors:\n      - \"禁止の決まりその1\"\n      - \"必ず守る決まりその2\"\n"
            ]
        )
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 0, out)
        self.assertEqual(data["totals"]["unsorted"], 0)

    def test_anchors_list_missing_line_fails(self):
        reg = _registry(
            [
                "  - id: T1\n    source: docs/a.md\n    kind: review\n    reason: \"人が見る\"\n"
                "    anchors:\n      - \"禁止の決まりその1\"\n      - \"どこにも無い文言\"\n"
            ]
        )
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C2", self._codes(data))

    def test_anchor_matching_many_lines_warns(self):
        reg = _registry([_review("T1", "決まり")])
        rc, data, out = self._run(reg)
        self.assertTrue(any(f["check"] == "C2" and f["severity"] == "warn" for f in data["findings"]), out)

    def test_not_rules_cover_lines(self):
        reg = _registry(
            [_review("T1", "禁止の決まりその1")],
            not_rules='not_rules:\n  - source: docs/a.md\n    anchor: "必ず守る決まりその2"\n    reason: "記録行"\n',
        )
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 0, out)
        self.assertEqual(data["totals"]["not_rules"], 1)
        self.assertEqual(data["per_doc"]["docs/a.md"]["in_not_rules"], 1)

    def test_not_rules_anchors_list(self):
        reg = _registry(
            [],
            not_rules='not_rules:\n  - source: docs/a.md\n    reason: "記録行"\n    anchors:\n'
            '      - "禁止の決まりその1"\n      - "必ず守る決まりその2"\n',
        )
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 0, out)
        self.assertEqual(data["per_doc"]["docs/a.md"]["in_not_rules"], 2)

    def test_not_rules_without_reason_fails(self):
        reg = _registry(
            [_review("T1", "禁止の決まりその1")],
            not_rules='not_rules:\n  - source: docs/a.md\n    anchor: "必ず守る決まりその2"\n',
        )
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C3", self._codes(data))

    def test_not_rules_overlapping_rules_fails(self):
        reg = _registry(
            [_review("T1", "禁止の決まりその1"), _review("T2", "必ず守る決まりその2")],
            not_rules='not_rules:\n  - source: docs/a.md\n    anchor: "必ず守る"\n    reason: "記録行"\n',
        )
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C5", self._codes(data))

    def test_review_without_reason_fails(self):
        reg = _registry([_review("T1", "禁止の決まりその1", reason=None), _review("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C3", self._codes(data))

    def test_exempt_without_reason_fails(self):
        reg = _registry([_review("T1", "禁止の決まりその1", kind="exempt", reason=""), _review("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C3", self._codes(data))

    def test_review_with_check_fails(self):
        extra = '    check: "chk-a"\n'
        reg = _registry([_review("T1", "禁止の決まりその1", extra=extra), _review("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertTrue(any(f["check"] == "C3" and "gate だけ" in f["message"] for f in data["findings"]), out)

    def test_exempt_with_check_fails(self):
        extra = '    check: "chk-a"\n'
        reg = _registry([_review("T1", "禁止の決まりその1", kind="exempt", extra=extra), _review("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C3", self._codes(data))

    def test_duplicate_id_fails(self):
        reg = _registry([_review("T1", "禁止の決まりその1"), _review("T1", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertTrue(any(f["check"] == "C5" and "重複" in f["message"] for f in data["findings"]), out)

    def test_wrong_when_fails(self):
        bad = _item("T1", "禁止の決まりその1").replace("when: ci", "when: sometime")
        reg = _registry([bad, _item("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertTrue(any(f["check"] == "C3" and "when" in f["message"] for f in data["findings"]), out)

    def test_missing_fixture_path_fails(self):
        bad = _item("T1", "禁止の決まりその1").replace('fixture: ""', 'fixture: "no/such/file.txt"')
        reg = _registry([bad, _item("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertTrue(any(f["check"] == "C3" and "fixture" in f["message"] for f in data["findings"]), out)

    def test_unknown_kind_fails(self):
        reg = _registry([_review("T1", "禁止の決まりその1", kind="gate候補"), _review("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg)
        self.assertEqual(rc, 1, out)
        self.assertIn("C3", self._codes(data))

    def test_c0_registry_unreadable(self):
        rc, data, out = self._run("words: 禁止\nrules:\n\t- id: T1\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("C0", self._codes(data))

    def test_c0_missing_words(self):
        rc, data, out = self._run("rules: []\nnot_rules: []\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("C0", self._codes(data))

    def test_c0_bad_required_checks(self):
        reg = _registry([_item("T1", "禁止の決まりその1"), _item("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg, checks="chk-a without tab\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("C0", self._codes(data))

    def test_c0_missing_rule_doc(self):
        reg = _registry([_item("T1", "禁止の決まりその1"), _item("T2", "必ず守る決まりその2")])
        rc, data, out = self._run(reg, docs_list="docs/a.md\ndocs/nothing.md\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("C0", self._codes(data))

    def test_c0_missing_registry_file(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "docs", "specs", "rule-enforcement")
            os.makedirs(base)
            with open(os.path.join(base, "rule-docs.txt"), "w", encoding="utf-8") as f:
                f.write("")
            with open(os.path.join(base, "required-checks.txt"), "w", encoding="utf-8") as f:
                f.write("")
            p = subprocess.run([sys.executable, "-I", CHECK, "--root", d, "--json"], capture_output=True, text=True)
            data = json.loads(p.stdout)
            self.assertEqual(p.returncode, 1)
            self.assertIn("C0", self._codes(data))


if __name__ == "__main__":
    unittest.main()
