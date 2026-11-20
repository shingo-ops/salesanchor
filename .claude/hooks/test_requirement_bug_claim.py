#!/usr/bin/env python3
"""requirement-bug-claim.py の試験。実行: python3 -I .claude/hooks/test_requirement_bug_claim.py

transcript の見本の形: Claude Code が書く JSONL。1行 = {"type": "assistant", "message": {"content": [...]}}。
content の要素は {"type": "text", "text": ...} か {"type": "tool_use", "name": ..., "input": {...}}。
Stop の入力は公式 hooks 説明（https://code.claude.com/docs/en/hooks Stop input）の session_id・transcript_path・stop_hook_active。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirement-bug-claim.py")


def line(blocks, typ="assistant"):
    return json.dumps({"type": typ, "message": {"content": blocks}}, ensure_ascii=False)


def text(s):
    return {"type": "text", "text": s}


def read_tool(path):
    return {"type": "tool_use", "name": "Read", "input": {"file_path": path}}


class Test(unittest.TestCase):
    def run_hook(self, lines, active=False, raw=None):
        with tempfile.TemporaryDirectory() as d:
            tp = os.path.join(d, "t.jsonl")
            with open(tp, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            log = os.path.join(d, "sub", "bug-claims.log")
            env = dict(os.environ, REQUIREMENT_LIBRARY_LOG=log)
            stdin = raw if raw is not None else json.dumps(
                {"session_id": "s1", "transcript_path": tp, "stop_hook_active": active})
            p = subprocess.run([sys.executable, "-I", HOOK], input=stdin, capture_output=True,
                               text=True, env=env, timeout=20)
            logged = open(log, encoding="utf-8").read().splitlines() if os.path.exists(log) else []
            return p, logged

    def test_block_without_read(self):
        p, logged = self.run_hook([line([text("これは不具合です")])])
        self.assertEqual(p.returncode, 0)
        out = json.loads(p.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertEqual(len(logged), 1)
        parts = logged[0].split("\t")
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[1], "s1")

    def test_no_block_after_read(self):
        p, logged = self.run_hook([line([read_tool("docs/adr/ADR-097-x.md")]), line([text("不具合です")])])
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout.strip(), "")
        self.assertEqual(logged, [])

    def test_stop_hook_active(self):
        p, logged = self.run_hook([line([text("バグです")])], active=True)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout.strip(), "")
        self.assertEqual(logged, [])

    def test_broken_input(self):
        p, logged = self.run_hook([line([text("バグ")])], raw="not json")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout.strip(), "")
        self.assertEqual(logged, [])


if __name__ == "__main__":
    unittest.main()
