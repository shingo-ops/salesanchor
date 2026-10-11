#!/usr/bin/env python3
"""全件ドライランの対象（登録された全ファイル − 除外一覧）を決め、報告する。強制はしない。

使い方:
  python3 scripts/migration-dryrun-report.py set
      対象のファイルを 1 行ずつ出す。除外一覧が不正（登録されていない・無い・重複）なら失敗する。
  python3 scripts/migration-dryrun-report.py run --db NAME [--rounds 2] [--psql CMD ...]
      対象を登録順に psql で流す。落ちても続け、結果を表にして出す。終了コードは常に 0（報告のみ）。
      GITHUB_STEP_SUMMARY があれば、そこにも書く。

除外一覧: scripts/migration-guard/dryrun-exclusions.tsv（file / reason / fix_ref）。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_all_migrations.sh"
EXCLUSIONS = ROOT / "scripts" / "migration-guard" / "dryrun-exclusions.tsv"


def registered_files() -> list[str]:
    files = [ln.split()[1] for ln in RUNNER.read_text(encoding="utf-8").splitlines() if ln.startswith("run_sql ")]
    return list(dict.fromkeys(files))


def load_exclusions(path: Path = EXCLUSIONS) -> dict[str, str]:
    rows: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        cols = raw.split("\t")
        if len(cols) < 3 or not all(c.strip() for c in cols[:3]):
            raise SystemExit(f"{path}:{number}: 列は file<TAB>reason<TAB>fix_ref の 3 つが必要です")
        if cols[0] in rows:
            raise SystemExit(f"{path}:{number}: 重複した行: {cols[0]}")
        rows[cols[0].strip()] = cols[1].strip()
    return rows


def dryrun_set() -> tuple[list[str], dict[str, str]]:
    registered = registered_files()
    exclusions = load_exclusions()
    problems = [f"登録されていない除外: {f}" for f in exclusions if f not in registered]
    problems += [f"ファイルが無い除外: {f}" for f in exclusions if f in registered and not (ROOT / f).is_file()]
    if problems:
        raise SystemExit("除外一覧が不正です:\n" + "\n".join(f"  - {p}" for p in problems))
    return [f for f in registered if f not in exclusions], exclusions


def run_file(psql: list[str], db: str, path: str) -> tuple[bool, str]:
    proc = subprocess.run(
        [*psql, "-d", db, "-v", "ON_ERROR_STOP=1", "-f", str(ROOT / path)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if proc.returncode == 0:
        return True, ""
    tail = [ln for ln in (proc.stderr or proc.stdout).strip().splitlines() if ln.strip()][-2:]
    return False, " / ".join(tail)[:300]


def run_report(db: str, rounds: int, psql: list[str]) -> int:
    files, exclusions = dryrun_set()
    registered = len(registered_files())
    print(f"全件ドライラン（報告のみ）: 登録 {registered} ファイル − 除外 {len(exclusions)} = 対象 {len(files)} ファイル")
    summary = [f"### 全件ドライラン（報告のみ・強制しない）", f"登録 {registered} − 除外 {len(exclusions)} = 対象 {len(files)}", ""]
    for number in range(1, rounds + 1):
        failed: list[tuple[str, str]] = []
        for index, path in enumerate(files, 1):
            ok, detail = run_file(psql, db, path)
            print(f"{'✅' if ok else '❌'} [{number}周目 {index}/{len(files)}] {path}" + ("" if ok else f"  {detail}"))
            if not ok:
                failed.append((path, detail))
        line = f"{number}周目: 成功 {len(files) - len(failed)} / 失敗 {len(failed)}"
        print(line)
        summary.append(f"**{line}**")
        summary.extend(f"- `{p}`: {d}" for p, d in failed)
        summary.append("")
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n".join(summary) + "\n")
    return 0  # 報告のみ


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("set")
    run = sub.add_parser("run")
    run.add_argument("--db", required=True)
    run.add_argument("--rounds", type=int, default=2)
    run.add_argument("--psql", nargs="+", default=["psql", "-h", "localhost", "-U", "jarvis"])
    args = parser.parse_args()
    if args.mode == "set":
        files, _ = dryrun_set()
        print("\n".join(files))
        return 0
    return run_report(args.db, args.rounds, args.psql)


if __name__ == "__main__":
    sys.exit(main())
