#!/usr/bin/env python3
"""必須チェックの「まとめ役」の判定ロジックを静的に確かめ、真理値表で流して確かめる。

目的: 設計 docs/handoff/ci-aggregator-gate/design.md §3 C7。
まとめ役（`if: always()` かつ needs に detect-changes を含むジョブ）の
「Report results」の run が、判定ジョブ（detect-changes）の失敗や想定外の答えで
緑にならないことを、全部の組み合わせで確かめる。

実行方法:
    python3 -I scripts/ci/check_ci_aggregators.py [--workflows-dir DIR] [--json]

終了コード: 問題 0 件・外れ 0 件なら 0、それ以外（読めないファイル含む）は 1。
標準ライブラリと PyYAML だけを使う。
"""
import argparse
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile

import yaml

DETECT = "detect-changes"
EXPR_RE = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
RESULT_RE = re.compile(r"^needs\.([A-Za-z0-9_-]+)\.result$")
OUTPUT_RE = re.compile(r"^needs\.detect-changes\.outputs\.([A-Za-z0-9_-]+)$")
EVENT_EXPR = "github.event_name"
IF_RE = re.compile(
    r"needs\.detect-changes\.outputs\.([A-Za-z0-9_-]+) == 'true'"
    r"( \|\| github\.event_name == 'workflow_dispatch')?"
)
RESULT_VALUES = ["success", "failure", "skipped", "cancelled"]
DET_VALUES = ["success", "failure", "cancelled", "skipped"]
OUT_VALUES = ["true", "false", ""]
TIMEOUT_SEC = 10
MAX_RECORDED = 5


def default_workflows_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "..", ".github", "workflows")


def as_needs_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def find_aggregators(jobs):
    found = []
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        cond = job.get("if")
        if cond is None or str(cond).strip() != "always()":
            continue
        if DETECT in as_needs_list(job.get("needs")):
            found.append(name)
    return found


def static_check(jobs, name):
    """(problems, info) を返す。info は真理値表に必要な情報。"""
    problems = []
    job = jobs[name]
    needs = as_needs_list(job.get("needs"))
    others = [n for n in needs if n != DETECT]

    steps = job.get("steps") or []
    reports = [
        s for s in steps
        if isinstance(s, dict) and s.get("name") == "Report results"
    ]
    if len(reports) != 1 or not isinstance(reports[0].get("run"), str):
        problems.append(
            "「Report results」の段が run を持つ形でちょうど 1 つ無い"
            f"（見つかった数: {len(reports)}）"
        )
        return problems, None
    run = reports[0]["run"]

    exprs = [m.group(1) for m in EXPR_RE.finditer(run)]
    for e in exprs:
        if RESULT_RE.match(e) or OUTPUT_RE.match(e) or e == EVENT_EXPR:
            continue
        problems.append(f"置き換えられない式: ${{{{ {e} }}}}")

    if f"needs.{DETECT}.result" not in exprs:
        problems.append(f"run の中に needs.{DETECT}.result が無い")

    keys = sorted({OUTPUT_RE.match(e).group(1) for e in exprs if OUTPUT_RE.match(e)})
    if len(keys) != 1:
        problems.append(
            f"run が参照する needs.{DETECT}.outputs.<鍵> が 1 種類でない: {keys}"
        )
    key = keys[0] if len(keys) == 1 else None

    referenced = {RESULT_RE.match(e).group(1) for e in exprs if RESULT_RE.match(e)}
    for j in others:
        if j not in referenced:
            problems.append(f"needs に挙げた {j} の結果を run が見ていない（needs.{j}.result が無い）")
    for x in sorted(referenced):
        if x != DETECT and x not in needs:
            problems.append(f"run が見ている needs.{x}.result の {x} が needs に無い")

    always_jobs = []
    follow_jobs = []
    manual_jobs = set()
    for j in others:
        jj = jobs.get(j)
        if not isinstance(jj, dict):
            problems.append(f"分けられない if: jobs.{j} が無い")
            continue
        if "if" not in jj:
            always_jobs.append(j)
            continue
        text = str(jj["if"]).replace("${{", "").replace("}}", "")
        text = re.sub(r"\s+", " ", text).strip()
        m = IF_RE.fullmatch(text)
        if not m:
            problems.append(f"分けられない if: {jj['if']!s}")
            continue
        if key is not None and m.group(1) != key:
            problems.append(
                f"{j} の if の鍵 {m.group(1)} が run の鍵 {key} と違う"
            )
        follow_jobs.append(j)
        if m.group(2):
            manual_jobs.add(j)

    if problems:
        return problems, None
    return problems, {
        "run": run,
        "key": key,
        "always": always_jobs,
        "follow": follow_jobs,
        "manual": manual_jobs,
    }


def expected(det, out, results, ev, info):
    if det != "success":
        return 1
    if out not in ("true", "false"):
        return 1
    for j in info["always"]:
        if results[j] != "success":
            return 1
    for j in info["follow"]:
        must_run = out == "true" or (ev == "workflow_dispatch" and j in info["manual"])
        want = "success" if must_run else "skipped"
        if results[j] != want:
            return 1
    return 0


def substitute(run, det, out, results, ev):
    def repl(m):
        e = m.group(1)
        if e == EVENT_EXPR:
            return ev
        mo = OUTPUT_RE.match(e)
        if mo:
            return out
        mr = RESULT_RE.match(e)
        if mr:
            x = mr.group(1)
            return det if x == DETECT else results[x]
        return m.group(0)

    return EXPR_RE.sub(repl, run)


def run_script(path, workdir):
    try:
        p = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=workdir,
            timeout=TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return None
    return 0 if p.returncode == 0 else 1


def truth_table(info, tmpdir):
    jobs = info["always"] + info["follow"]
    evs = ["pull_request", "workflow_dispatch"] if info["manual"] else ["pull_request"]
    script_path = os.path.join(tmpdir, "report.sh")
    combos = 0
    mismatches = 0
    recorded = []
    for det in DET_VALUES:
        for out in OUT_VALUES:
            for vals in itertools.product(RESULT_VALUES, repeat=len(jobs)):
                results = dict(zip(jobs, vals))
                for ev in evs:
                    combos += 1
                    exp = expected(det, out, results, ev, info)
                    text = substitute(info["run"], det, out, results, ev)
                    with open(script_path, "w", encoding="utf-8") as f:
                        f.write(text + "\n")
                    act = run_script(script_path, tmpdir)
                    if act != exp:
                        mismatches += 1
                        if len(recorded) < MAX_RECORDED:
                            recorded.append({
                                "det": det, "out": out, "results": results,
                                "ev": ev, "expected": exp,
                                "actual": "timeout" if act is None else act,
                            })
    return combos, mismatches, recorded


def main():
    ap = argparse.ArgumentParser(description="まとめ役の判定ロジックの検査")
    ap.add_argument("--workflows-dir", default=default_workflows_dir())
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    wdir = args.workflows_dir
    aggregators = []
    read_errors = []
    try:
        names = sorted(
            n for n in os.listdir(wdir)
            if n.endswith(".yml") and os.path.isfile(os.path.join(wdir, n))
        )
    except OSError as e:
        print(f"読めないフォルダ: {wdir}: {e}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        for fname in names:
            path = os.path.join(wdir, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    doc = yaml.safe_load(f)
            except (OSError, yaml.YAMLError, UnicodeDecodeError) as e:
                read_errors.append(f"{fname}: {e}")
                continue
            jobs = doc.get("jobs") if isinstance(doc, dict) else None
            if not isinstance(jobs, dict):
                continue
            for jname in find_aggregators(jobs):
                problems, info = static_check(jobs, jname)
                combos = mismatches = 0
                recorded = []
                if info is not None:
                    combos, mismatches, recorded = truth_table(info, tmpdir)
                aggregators.append({
                    "file": fname, "job": jname, "combos": combos,
                    "mismatches": mismatches, "problems": problems,
                    "mismatch_samples": recorded,
                })

    total_combos = sum(a["combos"] for a in aggregators)
    total_mismatches = sum(a["mismatches"] for a in aggregators)
    total_problems = sum(len(a["problems"]) for a in aggregators) + len(read_errors)
    ok = total_mismatches == 0 and total_problems == 0

    if args.as_json:
        print(json.dumps({
            "ok": ok,
            "aggregators": aggregators,
            "read_errors": read_errors,
            "total_combos": total_combos,
            "total_mismatches": total_mismatches,
            "total_problems": total_problems,
        }, ensure_ascii=False))
    else:
        for e in read_errors:
            print(f"読めなかった: {e}")
        for a in aggregators:
            tag = "OK" if not a["problems"] and a["mismatches"] == 0 else "NG"
            print(f"{tag} {a['file']}:{a['job']} 組 {a['combos']} 外れ {a['mismatches']}")
            for p in a["problems"]:
                print(f"  問題: {p}")
            for s in a["mismatch_samples"]:
                print(f"  外れ: {json.dumps(s, ensure_ascii=False)}")
        print(
            f"合計 まとめ役 {len(aggregators)} 組 {total_combos} "
            f"外れ {total_mismatches} 問題 {total_problems}"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
