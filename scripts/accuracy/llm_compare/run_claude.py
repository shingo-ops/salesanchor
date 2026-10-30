#!/usr/bin/env python3
"""Gemini に渡したのと同じ文字列を claude CLI（サブスク）に解かせる（design.md §5-2）。手元の Mac で動かす。

  python3 -I run_claude.py --model haiku --schema v102_response_schema.json \
      --prompt-dir DIR --pair llmcmp-g1.jsonl:llmcmp-g1.index.tsv [--pair 続き.jsonl:続き.index.tsv] --out OUT.jsonl

・対象は JSONL の repeat=1 の成功行（error 欄なし）。成功行の並び順 N 番目 = index の通し番号 N（capture_prompt_ab.py）。
・順番に1件ずつ。rc≠0・is_error=true・時間切れ・別モデル混入・num_turns≠1・答えが空 のどれかで、理由を問わず即停止
  （時刻と件数を OUT.stop.txt に記録。待って再開しない）。--resume は「成功済みの job を飛ばして続きから」の明示指定のときだけ。
・--bare は使わない（API の鍵だけになりサブスクで動かない）。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

SYSTEM_PROMPT = "与えられた指示に従い、指定の JSON だけを返してください。"
FORBIDDEN_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")  # 空であること（CLAUDE_CODE_OAUTH_TOKEN はサブスクの鍵なので可）


class Stop(Exception):
    pass


def build_cmd(claude_bin, model, schema_text, effort="high"):
    cmd = [claude_bin, "-p", "--model", model, "--effort", effort, "--output-format", "json",
           "--json-schema", schema_text, "--tools", "", "--setting-sources", "", "--strict-mcp-config",
           "--no-session-persistence", "--system-prompt", SYSTEM_PROMPT]
    assert "--bare" not in cmd
    return cmd


def load_pairs(pairs):
    """[(jsonl, index)] → [(job_id, serial, sha, test_id)]。repeat=1 の成功行だけ、JSONL の並び順で。"""
    out = []
    for pair in pairs:
        jsonl, index = pair.rsplit(":", 1)
        test_id = os.path.basename(index)[: -len(".index.tsv")]
        idx = {}
        try:
            with open(index, encoding="utf-8") as f:
                next(f)
                for line in f:
                    s, sha, chars = line.rstrip("\n").split("\t")
                    idx[int(s)] = (sha, int(chars))
        except (OSError, ValueError, StopIteration) as e:
            raise Stop("index を読めない（行が壊れている／無い）: %s: %s" % (index, type(e).__name__))
        serial = 0
        try:
            f = open(jsonl, encoding="utf-8")
        except OSError as e:
            raise Stop("JSONL を開けない: %s: %s" % (jsonl, type(e).__name__))
        with f:
            for lineno, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    raise Stop("JSONL の %d 行目が JSON ではない: %s" % (lineno, jsonl))  # 行の中身は書かない
                if not isinstance(r, dict):
                    raise Stop("JSONL の %d 行目が JSON オブジェクトではない: %s" % (lineno, jsonl))
                if r.get("error"):
                    continue
                serial += 1
                if r.get("repeat") == 1:
                    if serial not in idx:
                        raise Stop("index に通し番号 %d が無い: %s" % (serial, index))
                    if "job_id" not in r:
                        raise Stop("JSONL の %d 行目に job_id が無い: %s" % (lineno, jsonl))
                    out.append((r["job_id"], serial, idx[serial][0], test_id))
        if serial != len(idx):
            raise Stop("JSONL の成功行 %d 件と index %d 件が合わない: %s" % (serial, len(idx), jsonl))
    ids = [j for j, _, _, _ in out]
    if len(ids) != len(set(ids)):
        raise Stop("同じ job が repeat=1 で2回ある")
    return out


def check_env(env):
    bad = [k for k in FORBIDDEN_ENV if env.get(k)]
    if bad:
        raise Stop("次の環境変数が空ではない（サブスクで動かない）: %s" % ",".join(bad))


def check_response(model, rc, stdout, timed_out=False):
    """1件の結果を確かめる。問題があれば Stop。通れば (parsed dict)。"""
    if timed_out:
        raise Stop("時間切れ")
    if rc != 0:
        raise Stop("rc=%s" % rc)
    try:
        d = json.loads(stdout)
    except ValueError:
        raise Stop("出力が JSON ではない")
    if not isinstance(d, dict):
        raise Stop("出力が JSON オブジェクトではない")
    if d.get("is_error") is not False:
        raise Stop("is_error=%r" % (d.get("is_error"),))
    mu = d.get("modelUsage")
    if not isinstance(mu, dict) or len(mu) != 1 or model not in next(iter(mu)):
        raise Stop("modelUsage が指定したモデル1種だけではない: %s" % (sorted(mu) if isinstance(mu, dict) else mu))
    if d.get("num_turns") != 1:
        raise Stop("num_turns=%r" % (d.get("num_turns"),))
    return d


def pick_response(d, field="auto"):
    """response_text に入れる文字列。auto = structured_output があればそれ、なければ result。"""
    so, res = d.get("structured_output"), d.get("result")
    if field == "structured_output" or (field == "auto" and so is not None):
        if so is None:
            raise Stop("structured_output が無い")
        text = so if isinstance(so, str) else json.dumps(so, ensure_ascii=False)
    else:
        text = res
    if not isinstance(text, str) or not text.strip():
        raise Stop("答えが空")
    return text


def run_one(cmd, prompt_text, timeout, runner=subprocess.run):
    with tempfile.TemporaryDirectory() as cwd:  # 空の一時フォルダ
        try:
            p = runner(cmd, input=prompt_text, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        except subprocess.TimeoutExpired:
            return None, "", True
    return p.returncode, p.stdout, False


def record_stop(path, reason, done, total):
    with open(path, "w", encoding="utf-8") as f:
        f.write("時刻\t%s\n理由\t%s\n完了件数\t%d\n対象件数\t%d\n"
                % (datetime.now(timezone.utc).isoformat(), reason, done, total))


LOGIN_KEYS = ("loggedIn", "authMethod", "apiProvider", "subscriptionType")  # ログイン種別を示す欄だけ残す（メール等は残さない）


def redact_auth(text):
    """`claude auth status` の出力から、ログイン種別を示す欄だけを取り出す。全文は保存しない。"""
    try:
        d = json.loads(text)
    except ValueError:
        return {"parsed": False}
    if not isinstance(d, dict):
        return {"parsed": False}
    out = {k: d[k] for k in LOGIN_KEYS if k in d and isinstance(d[k], (bool, str, int, type(None)))}
    out["parsed"] = True
    out["subscription"] = bool(d.get("subscriptionType"))
    return out


def preflight(claude_bin, env, runner=subprocess.run):
    check_env(env)
    info = {}
    for key, args in (("version", ["--version"]), ("auth_status", ["auth", "status"])):
        p = runner([claude_bin] + args, capture_output=True, text=True, timeout=60)
        text = (p.stdout or p.stderr or "").strip()
        info[key] = redact_auth(text) if key == "auth_status" else text
        if p.returncode != 0:
            raise Stop("claude %s が rc=%s" % (" ".join(args), p.returncode))
    return info


def main(argv=None, runner=subprocess.run, env=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=("haiku", "sonnet"))
    ap.add_argument("--schema", required=True)
    ap.add_argument("--prompt-dir", required=True)
    ap.add_argument("--pair", action="append", required=True, help="JSONL:INDEX（test-id ごとに1組）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--claude-bin", default="claude")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--response-field", choices=("auto", "result", "structured_output"), default="auto")
    ap.add_argument("--limit", type=int, default=0, help="先頭から何件だけ（試しの1件用）。0=全部")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--skip-preflight", action="store_true")
    a = ap.parse_args(argv)
    env = os.environ if env is None else env
    stop_path = a.out + ".stop.txt"
    schema_text = json.dumps(json.load(open(a.schema, encoding="utf-8")), ensure_ascii=False)
    cmd = build_cmd(a.claude_bin, a.model, schema_text, a.effort)
    targets = []
    done_ids = set()
    if os.path.exists(a.out):
        if not a.resume:
            sys.exit("出力が既にある（上書きしない）。続きは --resume: " + a.out)
        done_ids = {json.loads(l)["job_id"] for l in open(a.out, encoding="utf-8") if l.strip()}
    done = len(done_ids)
    try:
        targets = load_pairs(a.pair)  # 止まったら stop.txt に残す
        if a.limit:
            targets = targets[: a.limit]
        if not a.skip_preflight:
            info = preflight(a.claude_bin, env, runner)
            with open(a.out + ".preflight.json", "w", encoding="utf-8") as f:
                json.dump({"model": a.model, **info}, f, ensure_ascii=False)
        for job_id, serial, sha, test_id in targets:
            if job_id in done_ids:
                continue
            path = os.path.join(a.prompt_dir, "%s_%04d_%s.txt" % (test_id, serial, sha))
            try:
                data = open(path, "rb").read()
            except OSError:
                raise Stop("文字列のファイルを開けない: %s" % os.path.basename(path))
            if hashlib.sha256(data).hexdigest() != sha:
                raise Stop("文字列の sha256 が名前と違う: %s" % os.path.basename(path))
            started = time.monotonic()
            rc, stdout, timed_out = run_one(cmd, data.decode("utf-8"), a.timeout, runner)
            elapsed = round(time.monotonic() - started, 3)
            d = check_response(a.model, rc, stdout, timed_out)
            row = {"job_id": job_id, "repeat": 1, "config": "claude-" + a.model, "prompt_sha256": sha,
                   "response_text": pick_response(d, a.response_field), "usage_raw": d.get("usage"),
                   "model_usage": d.get("modelUsage"), "duration_ms": d.get("duration_ms"),
                   "total_cost_usd": d.get("total_cost_usd"), "elapsed_sec": elapsed, "errors": [],
                   "claude_raw": d}
            with open(a.out, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            done += 1
    except Stop as e:
        record_stop(stop_path, str(e), done, len(targets))
        print("STOP: %s" % e, file=sys.stderr)
        return 1
    print("完了 %d / %d" % (done, len(targets)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
