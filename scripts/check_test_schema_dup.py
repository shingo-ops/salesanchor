#!/usr/bin/env python3
"""
check_test_schema_dup.py

テスト(backend/tests/)が本番テーブル定義を新規にコピー(独自 CREATE TABLE)
したら検出して赤にする。柱3-a/b(docs/specs/process-hardening/design-pillar3.md)。

方式: Python の ast で文字列リテラル内の CREATE TABLE を拾う。
      docstring と assert 配下は除外。f-string は定数部を連結し
      置換部を {expr} に置き換えて再構成する。

使い方:
  CI:     BASE_SHA=<sha> HEAD_SHA=<sha> python3 scripts/check_test_schema_dup.py
  棚卸し: python3 scripts/check_test_schema_dup.py --inventory <sha>
"""
import ast
import os
import re
import subprocess
import sys

TESTS_DIR = "backend/tests/"
EXCLUDE_FILES = {
    "backend/tests/conftest.py",
    "backend/tests/test_tenant_service.py",
    "backend/tests/test_inventory_parser_real_samples.py",
}

_CREATE = re.compile(r"CREATE\s+TABLE\b", re.IGNORECASE)
_IFNE = re.compile(r"IF\s+NOT\s+EXISTS\b", re.IGNORECASE)
_NAME = re.compile(r"[A-Za-z0-9_.{}\"]+")
_AS = re.compile(r"AS\b", re.IGNORECASE)


def extract_table_names(text):
    names = []
    for m in _CREATE.finditer(text):
        rest = text[m.end():].lstrip()
        m_if = _IFNE.match(rest)
        if m_if:
            rest = rest[m_if.end():].lstrip()
        m_name = _NAME.match(rest)
        if not m_name:
            continue
        name = m_name.group(0)
        after = rest[m_name.end():].lstrip()
        if _AS.match(after):
            continue
        if name.upper() == "IF":
            raise RuntimeError("IF をテーブル名として抽出した: " + repr(rest[:80]))
        names.append(name)
    return names


def _joined(node):
    parts = []
    for v in node.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            parts.append(v.value)
        else:
            parts.append("{expr}")
    return "".join(parts)


def literal_strings(source):
    tree = ast.parse(source)
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) \
                    and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                skip.add(id(body[0].value))
        if isinstance(node, ast.Assert):
            for sub in ast.walk(node):
                skip.add(id(sub))
        if isinstance(node, ast.JoinedStr):
            for sub in ast.walk(node):
                if sub is not node:
                    skip.add(id(sub))
    out = []
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.JoinedStr):
            out.append((node.lineno, _joined(node)))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.lineno, node.value))
    return out


def tables_in_source(source):
    found = []
    if not source:
        return found
    for lineno, text in literal_strings(source):
        for name in extract_table_names(text):
            found.append((lineno, name))
    return found


def file_at(sha, path):
    r = subprocess.run(["git", "show", sha + ":" + path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return ""
    return r.stdout


def list_test_files(sha):
    r = subprocess.run(["git", "ls-tree", "-r", "--name-only", sha, "--", TESTS_DIR],
                       capture_output=True, text=True, check=True)
    return [p for p in r.stdout.split("\n")
            if p.endswith(".py") and p not in EXCLUDE_FILES]


def inventory(sha):
    detail = []
    files = 0
    total = 0
    for path in sorted(list_test_files(sha)):
        found = tables_in_source(file_at(sha, path))
        if not found:
            continue
        files += 1
        total += len(found)
        print("FILE {} {}".format(path, len(found)))
        for lineno, name in found:
            detail.append("{}\t{}\t{}".format(path, lineno, name))
    with open("/tmp/pillar3-inventory.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(detail) + "\n")
    print("SUMMARY files={} tables={}".format(files, total))


def changed_test_files(base, head):
    r = subprocess.run(["git", "diff", "--name-only", base + "..." + head],
                       capture_output=True, text=True, check=True)
    return [p for p in r.stdout.split("\n")
            if p.startswith(TESTS_DIR) and p.endswith(".py")
            and p not in EXCLUDE_FILES]


_PREFIX_DROP = re.compile(r"^(\{[^}]*\}|tenant_\d+)\.")


def normalize_name(name):
    """スキーマ前置きを落とす。public. は別物の可能性があるため残す。"""
    n = name
    while True:
        m = _PREFIX_DROP.match(n)
        if not m:
            return n
        n = n[m.end():]


def inventory_rows(sha):
    rows = []
    for path in sorted(list_test_files(sha)):
        for lineno, name in tables_in_source(file_at(sha, path)):
            rows.append((path, str(lineno), name, normalize_name(name)))
    return rows


def _rows_from_file(inv_path):
    rows = []
    with open(inv_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) != 4:
                continue
            if not cells[1].isdigit():
                continue
            rows.append((cells[0], cells[1], cells[2], cells[3]))
    return rows


def _key_counts(rows):
    d = {}
    for r in rows:
        k = (r[0], r[3])
        d[k] = d.get(k, 0) + 1
    return d


def generate_inventory(sha, out_path):
    rows = inventory_rows(sha)
    files = sorted(set(r[0] for r in rows))
    counts = {}
    for r in rows:
        counts[r[3]] = counts.get(r[3], 0) + 1
    out = []
    out.append("# 柱3-c 既存複製一覧（機械生成・手で編集しない）")
    out.append("")
    out.append("> この文書は何か（専門用語なしの1行）:")
    out.append("> テストが本番のテーブル定義をコピーしている箇所の全件リスト。片付けの進み具合を数える表。")
    out.append("")
    out.append("親: docs/specs/process-hardening/kgi.md（柱3-c）")
    out.append("設計: docs/specs/process-hardening/design-pillar3.md")
    out.append("生成元SHA: " + sha)
    out.append("生成: python3 scripts/check_test_schema_dup.py --write-inventory <sha> " + out_path)
    out.append("照合: python3 scripts/check_test_schema_dup.py --check-inventory " + out_path + " <sha>")
    out.append("")
    out.append("合計: {}ファイル・{}件".format(len(files), len(rows)))
    out.append("")
    out.append("## 一覧")
    out.append("")
    out.append("| ファイル | 行 | 元の表記 | 束ねた名前 |")
    out.append("|---|---|---|---|")
    for r in rows:
        out.append("| {} | {} | {} | {} |".format(r[0], r[1], r[2], r[3]))
    out.append("")
    out.append("## 集計（束ねた名前ごと・多い順）")
    out.append("")
    out.append("| 名前 | 件数 |")
    out.append("|---|---|")
    for name in sorted(counts, key=lambda k: (-counts[k], k)):
        out.append("| {} | {} |".format(name, counts[name]))
    out.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print("WROTE {} files={} tables={}".format(out_path, len(files), len(rows)))


def check_inventory(inv_path, sha):
    measured = inventory_rows(sha)
    recorded = _rows_from_file(inv_path)
    mk = _key_counts(measured)
    rk = _key_counts(recorded)
    added = []
    removed = []
    keys = set(mk)
    keys.update(rk)
    for k in sorted(keys):
        d = mk.get(k, 0) - rk.get(k, 0)
        if d > 0:
            added.append("{} {} +{}".format(k[0], k[1], d))
        elif d < 0:
            removed.append("{} {} {}".format(k[0], k[1], d))
    print("MEASURED files={} tables={}".format(len(set(r[0] for r in measured)), len(measured)))
    print("RECORDED files={} tables={}".format(len(set(r[0] for r in recorded)), len(recorded)))
    if added:
        print("新しい複製が増えています:", file=sys.stderr)
        for a in added:
            print("   " + a, file=sys.stderr)
        return 1
    if removed:
        print("複製が減りました。一覧の更新が必要です:")
        for r in removed:
            print("   " + r)
        return 0
    print("一覧と実測が一致(pass)")
    return 0


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "--write-inventory":
        generate_inventory(sys.argv[2], sys.argv[3])
        return 0
    if len(sys.argv) >= 4 and sys.argv[1] == "--check-inventory":
        return check_inventory(sys.argv[2], sys.argv[3])
    if len(sys.argv) >= 3 and sys.argv[1] == "--inventory":
        inventory(sys.argv[2])
        return 0
    base = os.environ.get("BASE_SHA")
    head = os.environ.get("HEAD_SHA")
    if not base or not head:
        print("BASE_SHA / HEAD_SHA が設定されていません", file=sys.stderr)
        return 1
    changed = changed_test_files(base, head)
    if not changed:
        print("対象テストファイルの変更なし - スキップ(pass)")
        return 0
    offenders = []
    for path in changed:
        b = len(tables_in_source(file_at(base, path)))
        h = len(tables_in_source(file_at(head, path)))
        print("[INFO] {}: BASE={} HEAD={}".format(path, b, h))
        if h > b:
            offenders.append("{} ({} -> {})".format(path, b, h))
    if offenders:
        print("テストに本番テーブル定義の新規コピーが増えています:", file=sys.stderr)
        for o in offenders:
            print("   " + o, file=sys.stderr)
        return 1
    print("テストへの新規スキーマ複製なし(pass)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
