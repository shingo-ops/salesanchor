#!/usr/bin/env python3
"""requirement-context.py の試験。実行: python3 -I .claude/hooks/test_requirement_context.py

PostToolUse の入力は公式 hooks 説明（https://code.claude.com/docs/en/hooks）の session_id・tool_name・tool_input.file_path。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
HOOK_SRC = os.path.join(HERE, "requirement-context.py")
LIB_SRC = os.path.join(ROOT, "scripts", "ci", "feature_index_lib.py")

INDEX = """# 索引

| 機能キーワード | 正準 ADR | 設計書 | コードの場所 | 補足 |
|---|---|---|---|---|
| 見本機能 | **ADR-097** ／ ADR-1076 | [見本](../specs/sample/design.md) | backend/app/x.py、backend/app/sub/** | 補足 |
"""


class Test(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.repo = os.path.join(self._td.name, "repo")
        self.tmp = os.path.join(self._td.name, "tmp")
        os.makedirs(self.tmp)
        for d in ("docs/adr", ".claude/hooks", "scripts/ci", "backend/app"):
            os.makedirs(os.path.join(self.repo, d))
        with open(os.path.join(self.repo, "docs/adr/FEATURE-INDEX.md"), "w", encoding="utf-8") as f:
            f.write(INDEX)
        shutil.copy(HOOK_SRC, os.path.join(self.repo, ".claude/hooks/requirement-context.py"))
        shutil.copy(LIB_SRC, os.path.join(self.repo, "scripts/ci/feature_index_lib.py"))
        for n in ("x.py", "y.py"):
            open(os.path.join(self.repo, "backend/app", n), "w").close()
        subprocess.run(["git", "init", "-q", self.repo], check=True)

    def run_hook(self, stdin):
        env = dict(os.environ, TMPDIR=self.tmp)
        return subprocess.run(
            [sys.executable, "-I", os.path.join(self.repo, ".claude/hooks/requirement-context.py")],
            input=stdin, capture_output=True, text=True, env=env, timeout=20)

    def payload(self, path, sid="s1"):
        return json.dumps({"session_id": sid, "tool_name": "Read", "tool_input": {"file_path": path}})

    def test_match(self):
        p = self.run_hook(self.payload(os.path.join(self.repo, "backend/app/x.py")))
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PostToolUse")
        self.assertIn("ADR-097・ADR-1076", out["additionalContext"])
        self.assertIn("docs/specs/sample/design.md", out["additionalContext"])

    def test_no_match(self):
        p = self.run_hook(self.payload(os.path.join(self.repo, "backend/app/y.py")))
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_second_time_silent(self):
        path = os.path.join(self.repo, "backend/app/x.py")
        self.assertNotEqual(self.run_hook(self.payload(path)).stdout, "")
        p = self.run_hook(self.payload(path))
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_broken_input(self):
        for raw in ("not json", "", "{}", '{"session_id": "s"}'):
            p = self.run_hook(raw)
            self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_outside_repo(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "x.py")
            open(f, "w").close()
            p = self.run_hook(self.payload(f))
            self.assertEqual((p.returncode, p.stdout), (0, ""))

    def bash_payload(self, command, sid="b1"):
        return json.dumps({"session_id": sid, "cwd": self.repo, "tool_name": "Bash",
                           "tool_input": {"command": command}})

    def test_bash_sed_relative(self):
        p = self.run_hook(self.bash_payload("sed -n 1,5p backend/app/x.py"))
        self.assertEqual(p.returncode, 0)
        self.assertIn("ADR-097", json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_bash_glob(self):
        p = self.run_hook(self.bash_payload("cat backend/app/*.py"))
        self.assertEqual(p.returncode, 0)
        self.assertIn("ADR-097", json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_bash_directory_only(self):
        p = self.run_hook(self.bash_payload("grep -rn foo backend/app"))
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_bash_nonexistent_file(self):
        p = self.run_hook(self.bash_payload('grep -n "backend/app/nothing.py" backend/app/missing.py'))
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_bash_unclosed_quote(self):
        p = self.run_hook(self.bash_payload("sed -n 1p 'backend/app/x.py"))
        self.assertEqual(p.returncode, 0)

    def _write_index(self, note):
        with open(os.path.join(self.repo, "docs/adr/FEATURE-INDEX.md"), "w", encoding="utf-8") as f:
            f.write(INDEX.replace("| 補足 |", "| " + note + " |"))

    def test_note_in_sentence(self):
        p = self.run_hook(self.payload(os.path.join(self.repo, "backend/app/x.py")))
        ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("決まりの要旨: 補足。", ctx)
        self.assertNotIn("見本機能", ctx)

    def test_note_dash_omitted(self):
        self._write_index("-")
        p = self.run_hook(self.payload(os.path.join(self.repo, "backend/app/x.py")))
        ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("決まりの要旨", ctx)

    def test_note_truncated_400(self):
        self._write_index("あ" * 401)
        p = self.run_hook(self.payload(os.path.join(self.repo, "backend/app/x.py")))
        ctx = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("あ" * 400 + "…", ctx)
        self.assertNotIn("あ" * 401, ctx)


if __name__ == "__main__":
    unittest.main()
