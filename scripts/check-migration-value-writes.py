#!/usr/bin/env python3
"""migration の値の書き込み検査（ADR-155: マイグレーションは構造変更のみ）。

保護対象の表（scripts/migration-guard/protected-tables.txt）への INSERT / UPDATE / DELETE と、
データの参照（SELECT 等）を見つける。標準ライブラリだけで動く。

使い方:
  python3 scripts/check-migration-value-writes.py diff BASE HEAD [--check 7|8|all]
      PR の差分を検査する（チェック 7・8）。新規ファイルは全体、変更されたファイルは「追加された行」だけを見る。
      neutralize（値の書き込みを外し、コメントと NOTICE を足す）編集は通る。
  python3 scripts/check-migration-value-writes.py repo
      scripts/run_all_migrations.sh に登録された全ファイルを走査し、値の書き込みを持つファイルが
      value-write-allowlist.tsv にあることを確かめる（許可一覧に古い行が残っていても失敗する）。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD_DIR = ROOT / "scripts" / "migration-guard"
TABLES_FILE = GUARD_DIR / "protected-tables.txt"
ALLOWLIST_FILE = GUARD_DIR / "value-write-allowlist.tsv"
RUNNER = ROOT / "scripts" / "run_all_migrations.sh"

MIGRATION_PATH = re.compile(r"^migrations/[0-9].*\.sql$")
# チェック 7 と同じ正規表現。違いは 2 つ: (1) 動的なスキーマ名（%I. / %s.）も許す（tenant ループの
# EXECUTE format で書かれた値の書き込みを見逃さないため）、(2) 表名の後ろに語境界（products が
# products_xxx に当たらない）。
SCHEMA_PREFIX = r"(?:public\.|tenant_[0-9]+\.|%I\.|%s\.)?"
# チェック 8 の許可パターン（構造変更・存在確認・NOTICE の行は、表名が出ても許す）
ALLOW_PATTERN = re.compile(
    r"CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|CREATE\s+(UNIQUE\s+)?INDEX|DROP\s+INDEX|DROP\s+TRIGGER|DROP\s+VIEW"
    r"|CREATE\s+(OR\s+REPLACE\s+)?TRIGGER|COMMENT\s+ON|ADD\s+COLUMN|DROP\s+COLUMN|ALTER\s+COLUMN|REFERENCES"
    r"|information_schema|pg_namespace|pg_class|pg_trigger|to_regclass|RAISE\s+NOTICE"
    r"|CREATE\s+(OR\s+REPLACE\s+)?VIEW|CREATE\s+(OR\s+REPLACE\s+)?FUNCTION|RENAME\s+TO|table_name|table_schema"
    r"|PRIMARY\s+KEY",
    re.IGNORECASE,
)


def load_tables(path: Path = TABLES_FILE) -> list[str]:
    names = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            names.append(line)
    if not names:
        raise SystemExit(f"保護対象の表の一覧が空です: {path}")
    return names


def build_regexes(tables: list[str]) -> dict[str, re.Pattern[str]]:
    alt = "|".join(re.escape(t) for t in sorted(tables, key=len, reverse=True))
    table = rf"({alt})\b"
    return {
        "INSERT": re.compile(rf"INSERT\s+INTO\s+{SCHEMA_PREFIX}{table}", re.IGNORECASE),
        "UPDATE": re.compile(rf"UPDATE\s+{SCHEMA_PREFIX}{table}", re.IGNORECASE),
        "DELETE": re.compile(rf"DELETE\s+FROM\s+{SCHEMA_PREFIX}{table}", re.IGNORECASE),
    }


def build_reference_regex(tables: list[str]) -> re.Pattern[str]:
    alt = "|".join(re.escape(t) for t in sorted(tables, key=len, reverse=True))
    return re.compile(rf"\b(?:{alt})\b", re.IGNORECASE)


def is_comment(line: str) -> bool:
    return line.lstrip().startswith("--")


def normalize(line: str) -> str:
    return " ".join(line.split())


def value_writes(lines: list[str], regexes: dict[str, re.Pattern[str]]) -> list[tuple[int, str, str, str]]:
    """(行番号, 種類, 表名, 行) のリスト。コメント行は見ない。"""
    found = []
    for number, line in enumerate(lines, 1):
        if is_comment(line):
            continue
        for kind, regex in regexes.items():
            match = regex.search(line)
            if match:
                found.append((number, kind, match.group(1).lower(), line.strip()))
    return found


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


# ---------------------------------------------------------------- diff モード（チェック 7・8）
def changed_migrations(base: str, head: str) -> list[tuple[str, list[str], str]]:
    """(状態 A/M/R, 差分を取るパス, 新しいパス)。migrations/ の .sql だけ。"""
    out = git("diff", "-M", "--name-status", "--diff-filter=AMR", base, head, "--", "migrations")
    files = []
    for row in out.splitlines():
        parts = row.split("\t")
        status = parts[0][0]
        new = parts[-1]
        if not MIGRATION_PATH.match(new):
            continue
        paths = [parts[1], parts[2]] if status == "R" else [new]
        files.append((status, paths, new))
    return files


def added_non_comment_lines(base: str, head: str, paths: list[str]) -> list[str]:
    """差分で追加された行（コメント行を除く）。同じ文面が削除された行にもあれば（字下げの変更・移動）除く。"""
    diff = git("diff", "-M", base, head, "--", *paths)
    added = [ln[1:] for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    removed = {normalize(ln[1:]) for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---")}
    return [ln for ln in added if not is_comment(ln) and normalize(ln) not in removed]


def run_diff(base: str, head: str, check: str) -> int:
    tables = load_tables()
    regexes = build_regexes(tables)
    reference = build_reference_regex(tables)
    files = changed_migrations(base, head)
    failed7: list[str] = []
    failed8: list[str] = []
    for status, paths, new in files:
        lines = (
            git("show", f"{head}:{new}").splitlines() if status == "A" else added_non_comment_lines(base, head, paths)
        )
        if status == "A":  # 新規ファイルは全体を見る（コメント行は除く）
            lines = [ln for ln in lines if not is_comment(ln)]
        hits = value_writes(lines, regexes)
        if hits and check in ("7", "all"):
            failed7.append(f"--- {Path(new).name} ---")
            failed7.extend(f"  {kind} {table}: {line}" for _, kind, table, line in hits)
        if check in ("8", "all"):
            bad = [ln.strip() for ln in lines if reference.search(ln) and not ALLOW_PATTERN.search(ln)]
            if bad:
                failed8.append(f"--- {Path(new).name} ---")
                failed8.extend(f"  {line}" for line in bad)
    if not files:
        print("✅ 追加・変更された migrations/*.sql なし — チェック 7・8 スキップ")
        return 0
    status_code = 0
    if check in ("7", "all"):
        if failed7:
            status_code = 1
            print("❌ MIGRATION GUARD FAILED (チェック7)")
            print(f"共用マスタテーブル（{len(tables)} 表: scripts/migration-guard/protected-tables.txt）への")
            print("INSERT / UPDATE / DELETE が、追加された行に検出されました（ADR-155）。")
            print("\n".join(failed7))
            print("マイグレーションは構造変更のみ。値はアプリ画面か CSV で変える。参考: ADR-155-product-master-ssot-csv-app.md")
        else:
            print(f"✅ 共用マスタテーブルへのデータ操作なし（{len(files)} ファイル）— チェック7 通過")
    if check in ("8", "all"):
        if failed8:
            status_code = 1
            print("❌ MIGRATION GUARD FAILED (チェック8)")
            print("共用マスタテーブルのデータ参照（構造変更・存在確認・NOTICE 以外）が、追加された行に検出されました（ADR-155）。")
            print("\n".join(failed8))
        else:
            print(f"✅ 共用マスタテーブルへのデータ参照なし（{len(files)} ファイル）— チェック8 通過")
    return status_code


# ---------------------------------------------------------------- repo モード（全件走査）
def registered_files() -> list[str]:
    files = []
    for line in RUNNER.read_text(encoding="utf-8").splitlines():
        if line.startswith("run_sql "):
            files.append(line.split()[1])
    return list(dict.fromkeys(files))


def load_allowlist(path: Path = ALLOWLIST_FILE) -> dict[str, tuple[set[str], str]]:
    rows: dict[str, tuple[set[str], str]] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        cols = raw.split("\t")
        if len(cols) < 4 or not all(c.strip() for c in cols[:4]):
            raise SystemExit(f"{path}:{number}: 列は file<TAB>tables<TAB>reason<TAB>decision_ref の 4 つが必要です")
        rows[cols[0].strip()] = ({t.strip().lower() for t in cols[1].split(",") if t.strip()}, cols[2].strip())
    return rows


def scan_registered() -> dict[str, set[str]]:
    regexes = build_regexes(load_tables())
    flagged: dict[str, set[str]] = {}
    for path in registered_files():
        file = ROOT / path
        if not file.is_file():
            continue
        hits = value_writes(file.read_text(encoding="utf-8").splitlines(), regexes)
        if hits:
            flagged[path] = {table for _, _, table, _ in hits}
    return flagged


def run_repo() -> int:
    registered = set(registered_files())
    flagged = scan_registered()
    allow = load_allowlist()
    problems = []
    for path, tables in sorted(flagged.items()):
        if path not in allow:
            problems.append(f"許可一覧にない値の書き込み: {path}（{', '.join(sorted(tables))}）")
        elif allow[path][0] != tables:
            problems.append(
                f"許可一覧の tables が実際と違う: {path}（一覧 {sorted(allow[path][0])} / 実際 {sorted(tables)}）"
            )
    for path in sorted(allow):
        if path not in registered:
            problems.append(f"許可一覧の行が、登録されていない（または無い）ファイルを指している: {path}")
        elif path not in flagged:
            problems.append(f"許可一覧の古い行（このファイルに値の書き込みはもう無い。行を消す）: {path}")
    if problems:
        print("❌ MIGRATION GUARD FAILED (全件走査)")
        print("\n".join(f"  - {p}" for p in problems))
        print("直し方: 値の書き込みは migration から外す（neutralize）か、残すものは理由つきで")
        print("scripts/migration-guard/value-write-allowlist.tsv に書く。外したファイルの行は同じ PR で消す。")
        return 1
    print(f"✅ 登録された {len(registered)} ファイルを走査: 値の書き込みを持つ {len(flagged)} ファイル = 許可一覧 {len(allow)} 行 — 全件走査 通過")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    diff = sub.add_parser("diff")
    diff.add_argument("base")
    diff.add_argument("head")
    diff.add_argument("--check", choices=["7", "8", "all"], default="all")
    sub.add_parser("repo")
    args = parser.parse_args()
    if args.mode == "diff":
        return run_diff(args.base, args.head, args.check)
    return run_repo()


if __name__ == "__main__":
    sys.exit(main())
