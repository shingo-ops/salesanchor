#!/usr/bin/env python3
"""workflow の run: から呼ぶ台本の道が、その段の作業場所から見て実在するかを確かめる見張り。

目的: 設計 docs/handoff/design-token-audit-notify-path/design.md 「2. 同じ間違いを止める点検」。
job の既定の作業場所（defaults.run.working-directory）のせいで、根元からの道で書いた台本が
見つからず exit 127 になる間違い（design-token-audit.yml・2026-11-09〜11-23 の3回）を PR で止める。

拾う形: bash|sh|node|python|python3 [-I] に続く、scripts/ を含む相対の道
作業場所: 段の working-directory → job の defaults.run → workflow の defaults.run → "." の順。
run の中で、拾った位置より前にある「行全体が cd だけの行」の最後の行を作業場所に足す。
$ を含む道・作業場所・cd の行と、/ か ~ で始まる cd は解けないので飛ばす。

実行方法:
    python3 -I scripts/ci/check_workflow_script_paths.py [--workflows-dir DIR] [--known-files FILE]
実在の一覧は既定で git ls-tree -r --name-only HEAD（sparse-checkout でも全部の道が出る）。
--known-files を渡すと、そのファイルの1行1道を実在の一覧として使う（試験用）。
終了コード: 道の不一致 0 件なら 0、それ以外（読めないファイル含む）は 1。
標準ライブラリと PyYAML だけを使う。
"""
import argparse
import os
import re
import subprocess
import sys

import yaml

CALL = re.compile(
    r"(?:^|[\s;&|(])(?:bash|sh|node|python3?)\s+(?:-I\s+)?"
    r"((?:\./|\.\./)*(?:[\w.-]+/)*scripts/[\w./-]+)"
)
CD = re.compile(r"(?m)^\s*cd\s+([^\s;&|]+)\s*$")


def repo_root():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def known_files(path):
    if path:
        with open(path, encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    out = subprocess.run(
        ["git", "-C", repo_root(), "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout
    return set(out.splitlines())


def run_dir(node, fallback):
    value = ((node.get("defaults") or {}).get("run") or {}).get("working-directory")
    return fallback if value is None else str(value)


def check(workflows_dir, files):
    checked = 0
    bad = []
    for name in sorted(os.listdir(workflows_dir)):
        if not name.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(workflows_dir, name), encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        if not isinstance(doc, dict):
            continue
        wf_dir = run_dir(doc, ".")
        for job_id, job in (doc.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            job_dir = run_dir(job, wf_dir)
            for step in job.get("steps") or []:
                if not isinstance(step, dict) or not step.get("run"):
                    continue
                run = str(step["run"])
                base = str(step.get("working-directory", job_dir))
                if "$" in base:
                    continue
                cds = [(m.start(), m.group(1)) for m in CD.finditer(run)]
                for m in CALL.finditer(run):
                    path = m.group(1)
                    if "$" in path:
                        continue
                    prior = [d for pos, d in cds if pos < m.start()]
                    where = base
                    if prior:
                        last = prior[-1]
                        if "$" in last or last.startswith(("/", "~")):
                            continue
                        where = os.path.join(base, last)
                    full = os.path.normpath(os.path.join(where, path))
                    checked += 1
                    if full not in files:
                        bad.append(
                            f"NG {name} job={job_id} step={step.get('name')!r} "
                            f"working-directory={base} 道={path} → {full}（実在しません）"
                        )
    return checked, bad


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workflows-dir", default=os.path.join(repo_root(), ".github", "workflows"))
    parser.add_argument("--known-files")
    args = parser.parse_args()
    try:
        files = known_files(args.known_files)
        checked, bad = check(args.workflows_dir, files)
    except (OSError, yaml.YAMLError, subprocess.CalledProcessError) as error:
        print(f"読めませんでした: {error}")
        return 1
    for line in bad:
        print(line)
    print(f"確かめた呼び出し {checked} 件 / 道の不一致 {len(bad)} 件")
    if bad:
        print("→ その段の作業場所から見た道になっていません。job の既定が frontend なら ../scripts/... と書きます。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
