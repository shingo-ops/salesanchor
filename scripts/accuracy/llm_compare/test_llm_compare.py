"""llm_compare の単体試験（design.md §13）。

  python3 -B -W ignore scripts/accuracy/llm_compare/test_llm_compare.py -v   （リポジトリの根から）

社外秘のデータはリポジトリに写さない。split / summarize の試験は手元の ~/CC報告ファイル-keep をその場で読む
（無ければ skip）。claude は偽の命令（一時フォルダに作る小さな python スクリプト）に差し替える。
"""
import csv
from fractions import Fraction
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import capture_prompt_ab as cap  # noqa: E402
import run_claude as rc  # noqa: E402
import split_snapshot as sp  # noqa: E402
import summarize as sm  # noqa: E402

KEEP = os.path.expanduser("~/CC報告ファイル-keep/accuracy-gold-20261020")
SNAP = os.path.join(KEEP, "sample", "snapshot")
GOLD = os.path.join(KEEP, "gold", "gold_v1.tsv")
SCORE_REF = os.path.join(KEEP, "score", "run1-r1")
SCORE = os.path.join(HERE, "..", "score_v102.py")


class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        self.mod = types.SimpleNamespace()
        self.calls = []

        def original(raw_text, **kw):
            self.calls.append(raw_text)
            if raw_text.startswith("FAIL"):
                raise RuntimeError("boom")
            return {"response_text": "{}"}
        self.mod.call_gemini_raw_copy_v8 = original
        self.build = lambda raw, **kw: "P:" + kw["prompt_text"] + "|" + raw

    def kw(self):
        return dict(prompt_text="T", supplier_context=None, knowledge_links=None, new_system_rules=None)

    def test_success_saves_failure_does_not(self):
        c = cap.install(self.mod, self.build, self.d, "t1")
        self.mod.call_gemini_raw_copy_v8("a", **self.kw())
        with self.assertRaises(RuntimeError):
            self.mod.call_gemini_raw_copy_v8("FAIL", **self.kw())
        self.mod.call_gemini_raw_copy_v8("b", **self.kw())
        files = sorted(f for f in os.listdir(self.d) if f.endswith(".txt"))
        self.assertEqual(len(files), 2)  # 失敗は保存しない
        sha_a = hashlib.sha256(b"P:T|a").hexdigest()
        self.assertEqual(files[0], "t1_0001_%s.txt" % sha_a)
        self.assertTrue(files[1].startswith("t1_0002_"))  # 通し番号は成功の数
        idx = open(os.path.join(self.d, "t1.index.tsv"), encoding="utf-8").read().splitlines()
        self.assertEqual(idx[0], "serial\tsha256\tchars")
        self.assertEqual(idx[1], "1\t%s\t%d" % (sha_a, len("P:T|a")))
        self.assertEqual(len(idx), 3)
        self.assertEqual(open(os.path.join(self.d, files[0]), "rb").read(), b"P:T|a")

    def test_other_test_id_does_not_collide(self):
        for tid in ("llmcmp-g1", "llmcmp-g2"):
            m = types.SimpleNamespace(call_gemini_raw_copy_v8=lambda raw, **kw: {"response_text": "{}"})
            cap.install(m, self.build, self.d, tid)
            m.call_gemini_raw_copy_v8("same", **self.kw())
        names = sorted(os.listdir(self.d))
        self.assertEqual(len(names), 4)  # 2 txt + 2 index。別名なので上書き・重複しない
        self.assertTrue(any(n.startswith("llmcmp-g1_0001_") for n in names))
        self.assertTrue(any(n.startswith("llmcmp-g2_0001_") for n in names))

    def test_never_overwrites(self):
        c = cap.install(self.mod, self.build, self.d, "t1")
        self.mod.call_gemini_raw_copy_v8("a", **self.kw())
        c2 = cap.Capturer(self.d, "t1", self.build)  # 同じ test-id をもう一度始めると同名になる
        with self.assertRaises(FileExistsError):
            c2.save("a", self.kw())

    def test_patches_prompt_ab_name_only(self):
        # 差し替え先は prompt_ab 側の名前（モジュール内の名前）。build_prompt は別に注入する
        called = {}
        m = types.SimpleNamespace(call_gemini_raw_copy_v8=lambda raw, **kw: called.setdefault("orig", True) or {"response_text": "x"})
        cap.install(m, self.build, self.d, "t1")
        m.call_gemini_raw_copy_v8("a", **self.kw())
        self.assertTrue(called["orig"])
        src = open(os.path.join(HERE, "capture_prompt_ab.py"), encoding="utf-8").read()
        self.assertIn("prompt_ab_module.call_gemini_raw_copy_v8 =", src)
        self.assertNotIn("gemini_raw_copy_v8.call_gemini_raw_copy_v8 =", src)


FAKE = r'''#!/usr/bin/env python3
import json, os, sys, time
a = sys.argv[1:]
mode = os.environ.get("FAKE_MODE", "ok")
if a[:1] == ["--version"]:
    print("fake 0.0"); sys.exit(0)
if a[:2] == ["auth", "status"]:
    print(os.environ.get("FAKE_AUTH", "logged in (fake)")); sys.exit(0)
assert "--bare" not in a
for need in ("--tools", "--setting-sources", "--strict-mcp-config", "--no-session-persistence", "--json-schema", "--system-prompt"):
    assert need in a, need
assert a[a.index("--effort") + 1] == "high"
sys.stdin.read()
with open(os.environ["FAKE_COUNT"], "a") as f: f.write("x")
n = len(open(os.environ["FAKE_COUNT"]).read())
fail_at = int(os.environ.get("FAKE_AT", "2"))
model = a[a.index("--model") + 1]
d = {"is_error": False, "num_turns": 2, "result": "", "structured_output": {"items": [{"lines": [1], "price": "1", "quantity": "1"}]},
     "usage": {"iterations": [{"type": "message"}], "input_tokens": 5, "output_tokens": 7, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
               "output_tokens_details": {"thinking_tokens": 3}},
     "modelUsage": {"claude-%s-5-5" % model: {}}, "duration_ms": 10, "total_cost_usd": 0.01}
if n == fail_at:
    if mode == "rc": sys.exit(3)
    if mode == "iserror": d["is_error"] = True
    if mode == "model": d["modelUsage"]["claude-other-1"] = {}
    if mode == "turns": d["num_turns"] = 1
    if mode == "iters": d["usage"]["iterations"] = [{}, {}]
    if mode == "hang": time.sleep(30)
print(json.dumps(d))
'''


class RunClaudeTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        self.fake = os.path.join(self.d, "claude")
        open(self.fake, "w").write(FAKE)
        os.chmod(self.fake, os.stat(self.fake).st_mode | stat.S_IXUSR)
        self.pd = os.path.join(self.d, "prompts")
        os.makedirs(self.pd)
        rows, idx = [], ["serial\tsha256\tchars"]
        for i in range(1, 6):  # 成功行5件。うち repeat=1 は3件（2つめの job は repeat 2 と 3 も）
            text = "dummy prompt %d" % i
            sha = hashlib.sha256(text.encode()).hexdigest()
            open(os.path.join(self.pd, "tx_%04d_%s.txt" % (i, sha)), "w").write(text)
            idx.append("%d\t%s\t%d" % (i, sha, len(text)))
        jobs = [("j1", 1), ("j1", 2), ("j2", 1), ("j2", 2), ("j3", 1)]
        for j, r in jobs:
            rows.append(json.dumps({"job_id": j, "repeat": r, "response_text": "{}"}))
        rows.insert(2, json.dumps({"job_id": "jx", "repeat": 1, "error": "x"}))  # 失敗行は通し番号に数えない
        open(os.path.join(self.d, "tx.jsonl"), "w").write("\n".join(rows) + "\n")
        open(os.path.join(self.d, "tx.index.tsv"), "w").write("\n".join(idx) + "\n")
        json.dump({"type": "object"}, open(os.path.join(self.d, "s.json"), "w"))
        self.env = dict(os.environ, FAKE_COUNT=os.path.join(self.d, "count"), PATH=os.environ["PATH"])
        for k in rc.FORBIDDEN_ENV:
            self.env.pop(k, None)

    def run_rc(self, model="haiku", mode="ok", at=99, extra=(), out="o.jsonl", timeout=600):
        os.environ["FAKE_MODE"], os.environ["FAKE_AT"] = mode, str(at)
        os.environ["FAKE_COUNT"] = self.env["FAKE_COUNT"]
        try:
            return rc.main(["--model", model, "--schema", os.path.join(self.d, "s.json"), "--prompt-dir", self.pd,
                            "--pair", "%s:%s" % (os.path.join(self.d, "tx.jsonl"), os.path.join(self.d, "tx.index.tsv")),
                            "--out", os.path.join(self.d, out), "--claude-bin", self.fake, "--timeout", str(timeout), *extra],
                           env=self.env)
        finally:
            for k in ("FAKE_MODE", "FAKE_AT", "FAKE_COUNT"):
                os.environ.pop(k, None)

    def lines(self, out="o.jsonl"):
        p = os.path.join(self.d, out)
        return [json.loads(l) for l in open(p)] if os.path.exists(p) else []

    def test_auth_status_is_redacted(self):
        secret = "someone@example.invalid"
        os.environ["FAKE_AUTH"] = json.dumps({"loggedIn": True, "authMethod": "claude.ai", "email": secret,
                                              "orgName": "ORG-X", "subscriptionType": "max"})
        try:
            self.assertEqual(self.run_rc(), 0)
        finally:
            os.environ.pop("FAKE_AUTH", None)
        txt = open(os.path.join(self.d, "o.jsonl.preflight.json"), encoding="utf-8").read()
        self.assertNotIn(secret, txt)
        self.assertNotIn("ORG-X", txt)
        got = json.loads(txt)["auth_status"]
        self.assertEqual(got, {"loggedIn": True, "authMethod": "claude.ai", "subscriptionType": "max",
                               "parsed": True, "subscription": True})
        # JSON でない出力は全文を残さない
        self.assertEqual(rc.redact_auth("name@example.invalid logged in"), {"parsed": False})

    def test_load_pairs_stop_is_recorded(self):
        bad_idx = os.path.join(self.d, "bad.index.tsv")
        open(bad_idx, "w").write("serial\tsha256\tchars\n")  # 成功行より index が少ない
        code = rc.main(["--model", "haiku", "--schema", os.path.join(self.d, "s.json"), "--prompt-dir", self.pd,
                        "--pair", "%s:%s" % (os.path.join(self.d, "tx.jsonl"), bad_idx),
                        "--out", os.path.join(self.d, "o2.jsonl"), "--claude-bin", self.fake, "--skip-preflight"],
                       env=self.env)
        self.assertEqual(code, 1)
        stop = open(os.path.join(self.d, "o2.jsonl.stop.txt"), encoding="utf-8").read()
        self.assertIn("index に通し番号 1 が無い", stop)

    def test_missing_prompt_file_and_broken_index_are_recorded(self):
        # 文字列のファイルが無い
        for f in os.listdir(self.pd):
            os.unlink(os.path.join(self.pd, f))
        self.assertEqual(self.run_rc(out="m1.jsonl", extra=("--skip-preflight",)), 1)
        self.assertIn("開けない", open(os.path.join(self.d, "m1.jsonl.stop.txt"), encoding="utf-8").read())
        # index の行が壊れている
        bad = os.path.join(self.d, "bad2.index.tsv")
        open(bad, "w").write("serial\tsha256\tchars\nnot-a-number\tabc\n")
        code = rc.main(["--model", "haiku", "--schema", os.path.join(self.d, "s.json"), "--prompt-dir", self.pd,
                        "--pair", "%s:%s" % (os.path.join(self.d, "tx.jsonl"), bad),
                        "--out", os.path.join(self.d, "m2.jsonl"), "--claude-bin", self.fake, "--skip-preflight"], env=self.env)
        self.assertEqual(code, 1)
        self.assertIn("index を読めない", open(os.path.join(self.d, "m2.jsonl.stop.txt"), encoding="utf-8").read())

    def test_broken_jsonl_is_recorded(self):
        idxp = os.path.join(self.d, "tx.index.tsv")
        secret = "SECRET-VALUE-XYZ"
        cases = {
            "nofile": (os.path.join(self.d, "nope.jsonl"), None, "開けない"),
            "badjson": (os.path.join(self.d, "bj.jsonl"), '{"job_id": "a", "repeat": 1}\n' + secret + "{\n", "JSON ではない"),
            "nojob": (os.path.join(self.d, "nj.jsonl"), '{"repeat": 1, "x": "' + secret + '"}\n', "job_id が無い"),
        }
        for name, (path, body, want) in cases.items():
            if body is not None:
                open(path, "w").write(body)
            out = os.path.join(self.d, name + ".jsonl.out")
            code = rc.main(["--model", "haiku", "--schema", os.path.join(self.d, "s.json"), "--prompt-dir", self.pd,
                            "--pair", "%s:%s" % (path, idxp), "--out", out, "--claude-bin", self.fake, "--skip-preflight"],
                           env=self.env)
            self.assertEqual(code, 1, name)
            stop = open(out + ".stop.txt", encoding="utf-8").read()
            self.assertIn(want, stop, name)
            self.assertNotIn(secret, stop, name)  # 値は書かない

    def test_all_ok_uses_repeat1_only(self):
        self.assertEqual(self.run_rc(), 0)
        L = self.lines()
        self.assertEqual([r["job_id"] for r in L], ["j1", "j2", "j3"])
        self.assertEqual(L[0]["config"], "claude-haiku")
        self.assertEqual(json.loads(L[0]["response_text"])["items"][0]["lines"], [1])
        self.assertEqual(L[1]["prompt_sha256"], hashlib.sha256(b"dummy prompt 3").hexdigest())  # 失敗行を飛ばした通し番号
        self.assertFalse(os.path.exists(os.path.join(self.d, "o.jsonl.stop.txt")))

    def stops(self, **kw):
        self.assertEqual(self.run_rc(**kw), 1)
        self.assertEqual(len(self.lines()), 1)  # 2件目で止まる（3件目は呼ばない）
        self.assertEqual(len(open(self.env["FAKE_COUNT"]).read()), 2)
        stop = open(os.path.join(self.d, "o.jsonl.stop.txt"), encoding="utf-8").read()
        self.assertIn("完了件数\t1", stop)

    def test_stop_rc(self): self.stops(mode="rc", at=2)
    def test_stop_is_error(self): self.stops(mode="iserror", at=2)
    def test_stop_mixed_model(self): self.stops(mode="model", at=2)
    def test_stop_turns(self): self.stops(mode="turns", at=2)
    def test_stop_iterations(self): self.stops(mode="iters", at=2)
    def test_stop_timeout(self): self.stops(mode="hang", at=2, timeout=1)

    def check(self, **kw):
        d = {"is_error": False, "num_turns": 1, "result": "text", "structured_output": None,
             "usage": {"iterations": [{"type": "message"}]}, "modelUsage": {"claude-haiku-5-5": {}}}
        d.update(kw)
        return rc.check_response("haiku", 0, json.dumps(d))

    def test_check_no_structured_output_one_turn_passes(self):
        self.assertEqual(self.check()["result"], "text")

    def test_check_no_structured_output_two_turns_stops(self):
        with self.assertRaises(rc.Stop):
            self.check(num_turns=2)

    def test_check_two_iterations_stops(self):
        with self.assertRaises(rc.Stop):
            self.check(usage={"iterations": [{}, {}]})

    def test_check_no_iterations_stops(self):
        with self.assertRaises(rc.Stop):
            self.check(usage={"input_tokens": 1})

    def test_api_key_env_refuses(self):
        self.env["ANTHROPIC_API_KEY"] = "x"
        self.assertEqual(self.run_rc(), 1)
        self.assertEqual(self.lines(), [])

    def test_no_overwrite_and_resume(self):
        self.assertEqual(self.run_rc(mode="rc", at=2), 1)
        with self.assertRaises(SystemExit):
            self.run_rc()
        self.assertEqual(self.run_rc(extra=["--resume"]), 0)
        self.assertEqual([r["job_id"] for r in self.lines()], ["j1", "j2", "j3"])

    def test_cmd_has_no_bare(self):
        cmd = rc.build_cmd("claude", "haiku", "{}")
        self.assertNotIn("--bare", cmd)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")


class SplitSummarizeTest(unittest.TestCase):
    def setUp(self):
        if not (os.path.isdir(SNAP) and os.path.exists(GOLD) and os.path.isdir(SCORE_REF)):
            self.skipTest("手元の ~/CC報告ファイル-keep のデータが無い")
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)

    def test_split_byte_identical(self):
        names = sorted(f for f in os.listdir(SNAP) if f.endswith(".tsv"))
        self.assertEqual(len(names), 100)
        comb = os.path.join(self.d, "comb.tsv")
        header = None
        with open(comb, "wb") as out:
            for n in names:
                data = open(os.path.join(SNAP, n), "rb").read()
                lines = data.split(b"\n")
                self.assertEqual(lines[-1], b"")  # 末尾は改行で終わる
                lines = lines[:-1]
                if header is None:
                    header = lines[0]
                    out.write(b"\t".join([b"tag", b"repeat", b"source_message"]) + b"\t" + header + b"\n")
                else:
                    self.assertEqual(lines[0], header)
                for ln in lines[1:]:
                    out.write(b"f_ct\t1\t" + n[:-4].encode() + b"\t" + ln + b"\n")
        sp.main(["--in", comb, "--out-dir", os.path.join(self.d, "split")])
        got = sorted(os.listdir(os.path.join(self.d, "split", "f_ct", "r1")))
        self.assertEqual(got, names)
        for n in names:
            self.assertEqual(open(os.path.join(self.d, "split", "f_ct", "r1", n), "rb").read(),
                             open(os.path.join(SNAP, n), "rb").read(), n)
        # 同じ投稿のファイルを上書きしない
        with self.assertRaises(SystemExit):
            sp.main(["--in", comb, "--out-dir", os.path.join(self.d, "split")])
        self.split_dir = os.path.join(self.d, "split", "f_ct", "r1")

    def test_summarize_matches_reference_score(self):
        # 分けたフォルダ → score_v102.py → summarize。比べる相手: KEEP/score/run1-r1/result.tsv
        self.test_split_byte_identical()
        out = os.path.join(self.d, "score")
        subprocess.run([sys.executable, "-I", SCORE, "--gold", GOLD, "--snapshot-dir", self.split_dir, "--out-dir", out],
                       check=True, capture_output=True)
        mine, ref = sm.read_result(out), sm.read_result(SCORE_REF)
        self.assertEqual(mine, ref)
        self.assertEqual(mine[("E1", "Gemini")].pop("frac"), Fraction(100 * 1441, 1480))
        self.assertEqual(mine[("E1", "Gemini")], {"ok": 1441, "ng": 39, "na": 0, "rate": 100.0 * 1441 / 1480})
        self.assertEqual(mine[("C1読み落とし", "件数")], {"count": 2})
        summ = os.path.join(self.d, "sum")
        # f_ct を Gemini 3回（同じもの）として、Claude 側に同じ結果を置くと「以上・以下」で合格になる
        self.assertEqual(sm.main(["--out-dir", summ, "--score", "g1=" + out, "--score", "g2=" + out, "--score", "c=" + out,
                                  "--gemini", "g1", "--gemini", "g2", "--claude", "c"]), 0)
        md = open(os.path.join(summ, "summary.md"), encoding="utf-8").read()
        self.assertIn("| E1 | Gemini | 判定 | 97.4% | 97.4% | 97.4% | 97.4% |", md)
        self.assertIn("| c | 正答率 | 合格 |", md)
        self.assertIn("| C1読み落とし | 件数 | 判定 | 2 | 2 | 2 | 2.0 | 2〜2 |", md)

    def test_usage_definitions(self):
        g, c = os.path.join(self.d, "g.jsonl"), os.path.join(self.d, "c.jsonl")
        open(g, "w").write(json.dumps({"config": "v102", "response_text": "x", "elapsed_sec": 2.0, "usage_raw": {
            "prompt_token_count": 10, "candidates_token_count": 3, "thoughts_token_count": 4}}) + "\n")
        open(c, "w").write(json.dumps({"config": "claude-haiku", "response_text": "x", "elapsed_sec": 5.0, "total_cost_usd": 0.5,
                                       "duration_ms": 900, "usage_raw": {"input_tokens": 1, "cache_creation_input_tokens": 2,
                                       "cache_read_input_tokens": 3, "output_tokens": 7,
                                       "output_tokens_details": {"thinking_tokens": 4}}}) + "\n")
        ug, uc = sm.read_usage(g), sm.read_usage(c)
        self.assertEqual((ug["input"], ug["output"], ug["think"]), (10, 3, 4))
        self.assertEqual((uc["input"], uc["output"], uc["think"]), (6, 7, 4))

    def _result_dir(self, name, rates, counts=(0, 0)):
        """rates = {E1,E2,E3: (ok, ng)}、counts = (C1読み落とし, 余分)。result.tsv だけの小さな出力フォルダ"""
        d = os.path.join(self.d, name)
        os.makedirs(d)
        with open(os.path.join(d, "result.tsv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["項目", "段", "OK", "NG", "対象外", "率"])
            for k, (ok, ng) in rates.items():
                w.writerow([k, "Gemini", ok, ng, 0, ""])
            w.writerow(["C1読み落とし", "件数", 0, counts[0], 0, ""])
            w.writerow(["余分", "件数", 0, counts[1], 0, ""])
        return d

    def test_tie_passes_with_fraction(self):
        # Gemini 3回の率 1/3・1/3・2/3 → 平均 4/9。Claude は 4/9 ちょうど。float の平均だと 44.44444444444445 > 44.44444444444444 で落ちる
        e = lambda ok, ng: {"E1": (ok, ng), "E2": (ok, ng), "E3": (ok, ng)}  # noqa: E731
        gs = [self._result_dir("g1", e(1, 2)), self._result_dir("g2", e(1, 2)), self._result_dir("g3", e(2, 1))]
        c = self._result_dir("c", e(4, 5))
        floats = [100.0 * 1 / 3, 100.0 * 1 / 3, 100.0 * 2 / 3]
        self.assertFalse(100.0 * 4 / 9 >= sum(floats) / 3)  # float なら落ちる＝この試験が意味を持つ
        out = os.path.join(self.d, "sumtie")
        self.assertEqual(sm.main(["--out-dir", out, "--score", "g1=" + gs[0], "--score", "g2=" + gs[1], "--score", "g3=" + gs[2],
                                  "--score", "c=" + c, "--gemini", "g1", "--gemini", "g2", "--gemini", "g3", "--claude", "c"]), 0)
        md = open(os.path.join(out, "summary.md"), encoding="utf-8").read()
        self.assertIn("| c | 正答率 | 合格 |", md)
        # 1件だけ足りなければ不合格
        c2 = self._result_dir("c2", e(4, 6))
        out2 = os.path.join(self.d, "sumtie2")
        sm.main(["--out-dir", out2, "--score", "g1=" + gs[0], "--score", "g2=" + gs[1], "--score", "g3=" + gs[2],
                 "--score", "c=" + c2, "--gemini", "g1", "--gemini", "g2", "--gemini", "g3", "--claude", "c"])
        self.assertIn("| c | 正答率 | 不合格 |", open(os.path.join(out2, "summary.md"), encoding="utf-8").read())

    def test_usage_repeat_spec_and_table_rows(self):
        g = os.path.join(self.d, "g.jsonl")
        with open(g, "w") as f:
            for rep, el in ((1, 1.0), (2, 2.0), (3, 4.0)):
                f.write(json.dumps({"job_id": "j", "repeat": rep, "config": "v102", "response_text": "x", "elapsed_sec": el,
                                    "usage_raw": {"prompt_token_count": 10 * rep}}) + "\n")
        self.assertEqual(sm.split_spec(g + ":2"), (g, 2))
        self.assertEqual(sm.split_spec(g), (g, None))
        self.assertEqual(sm.read_usage(g + ":2")["input"], 20)
        self.assertEqual(sm.read_usage(g + ":3")["calls"], 1)
        self.assertEqual(sm.read_usage(g)["calls"], 3)
        c = os.path.join(self.d, "c.jsonl")
        with open(c, "w") as f:
            for i, dm in enumerate((100, 300, 200)):
                f.write(json.dumps({"job_id": "j%d" % i, "repeat": 1, "config": "claude-haiku", "response_text": "x",
                                    "elapsed_sec": 1.0, "duration_ms": dm, "total_cost_usd": 0.25,
                                    "usage_raw": {"input_tokens": 1, "output_tokens": 1}}) + "\n")
        self.assertEqual(sm.read_usage(c)["duration_ms_median"], 200)
        self.assertAlmostEqual(sm.read_usage(c)["list_cost_usd"], 0.75)
        e = {"E1": (1, 1), "E2": (1, 1), "E3": (1, 1)}
        d1, d2, dc = self._result_dir("a1", e), self._result_dir("a2", e), self._result_dir("ac", e)
        out = os.path.join(self.d, "sumrep")
        self.assertEqual(sm.main(["--out-dir", out, "--score", "g1=" + d1, "--score", "g2=" + d2, "--score", "c=" + dc,
                                  "--gemini", "g1", "--gemini", "g2", "--claude", "c",
                                  "--usage", "g1=" + g + ":1", "--usage", "g2=" + g + ":2", "--usage", "c=" + c,
                                  "--expected-posts", "3"]), 0)
        md = open(os.path.join(out, "summary.md"), encoding="utf-8").read()
        self.assertIn("| 入力トークン合計 | 使用量 | 参考 | 10 | 20 | 3 |", md)
        self.assertIn("| duration_ms 中央値(Claudeのみ) | 使用量 | 参考 | - | - | 200 |", md)
        self.assertIn("| - | - | 0.7500 |", md)
        self.assertIn("定価換算 合計USD", md)

    def test_summarize_refuses_inside_repo(self):
        with self.assertRaises(sm.Bad):
            sm.check_out_dir(os.path.join(HERE, "out"))


class ScriptsTest(unittest.TestCase):
    """VPS／Mac 台本の構文と、REVISE で足した止めが入っていること（実行はしない）"""

    def read(self, name):
        return open(os.path.join(HERE, name), encoding="utf-8").read()

    def test_bash_syntax(self):
        for n in ("vps_run_gemini.sh", "vps_convert.sh", "fetch_results.sh"):
            r = subprocess.run(["bash", "-n", os.path.join(HERE, n)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, n + r.stderr)

    def test_run_gemini_guards(self):
        s = self.read("vps_run_gemini.sh")
        for needle in ("docker compose config --format json",           # R1
                       '"$BASE/out/$TID.jsonl"', '"$BASE/out/$TID.index.tsv"', '"$BASE/$TID.out"',   # R2
                       "prompt_ab:llmcmp-%", "TOTAL_USD=5.00", "MIN_REMAIN=1.00", '--max-cost-usd "$REMAIN"',  # R3
                       "deploy.yml", "rev-parse HEAD", "--retry-transient",   # R4
                       "84afd2e4e0094b542d5f1dada1fef39290aa6d997135296e78601fc945ac8b0c"):
            self.assertIn(needle, s)
        self.assertNotIn("--max-cost-usd 5.00", s)
        self.assertNotIn("grep -A2 'healthcheck:'", s)

    def test_run_gemini_rejects_bad_mode_and_test_id(self):
        runs = os.path.join(tempfile.mkdtemp(), "r.txt")
        open(runs, "w").write("x\n")
        self.addCleanup(shutil.rmtree, os.path.dirname(runs))
        sh = os.path.join(HERE, "vps_run_gemini.sh")
        for args, msg in ((("llmcmp-g1", runs, "dyr", "0" * 40), "run か dry"),
                          (("llmcmp-g1", runs), "run か dry"),
                          (("llmcmp-g1;x", runs, "dry", "0" * 40), "test-id"),
                          (("llmcmp-G1", runs, "dry", "0" * 40), "test-id"),
                          (("llmcmp-a\n;id", runs, "dry", "0" * 40), "test-id"),
                          (("llmcmp-a;id\nllmcmp-b", runs, "dry", "0" * 40), "test-id"),
                          (("llmcmp-", runs, "dry", "0" * 40), "test-id")):
            r = subprocess.run(["bash", sh, *args], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(r.returncode, 0, args)
            self.assertIn(msg, r.stdout + r.stderr, args)
        self.assertIn("remote.log に残る", self.read("vps_run_gemini.sh"))

    def test_fetch_checks_expected_sha(self):
        self.assertIn("84afd2e4e0094b542d5f1dada1fef39290aa6d997135296e78601fc945ac8b0c", self.read("fetch_results.sh"))


if __name__ == "__main__":
    unittest.main()
