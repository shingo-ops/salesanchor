#!/usr/bin/env python3
"""
柱3-a/b ペアテスト。

合成ケース(欠落版/充足版)と、実データ全件検算の両方を必ず実行する。
自作の練習問題だけで済ませることは禁止(2026-07-24 の取りこぼし再発防止)。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import check_test_schema_dup as m

Q = '"""'
FAILED = []


def check(label, got, want):
    if got == want:
        print("PASS {}: {}".format(label, got))
    else:
        print("FAIL {}: got={} want={}".format(label, got, want))
        FAILED.append(label)


def names(src):
    return [n for _, n in m.tables_in_source(src)]


def assign(body):
    return "_X_DDL = " + Q + "\n" + body + "\n" + Q + "\n"


def synthetic():
    check("form1-assign",
          names(assign("CREATE TABLE leads (id INTEGER)")), ["leads"])

    src2 = ("conn.execute(\n    text(\n        " + Q + "\n"
            "CREATE TABLE staff (id INTEGER)\n" + Q + "\n    )\n)\n")
    check("form2-multiline", names(src2), ["staff"])

    src3 = ("conn.exec_driver_sql(" + Q + "\n"
            "CREATE TABLE audit_logs (id INTEGER)\n" + Q + ")\n")
    check("form3-exec-driver", names(src3), ["audit_logs"])

    src4 = ("dbapi_conn.execute(" + Q + "\n"
            "CREATE TABLE tenants (id INTEGER)\n" + Q + ")\n")
    check("form4-dbapi", names(src4), ["tenants"])

    check("ifne-not-if",
          names(assign("CREATE TABLE IF NOT EXISTS public.suppliers (id INTEGER)")),
          ["public.suppliers"])

    srcf = ("_T = 'leads'\n_S = f" + Q + "\n"
            "CREATE TABLE IF NOT EXISTS {_T} (id INTEGER)\n" + Q + "\n")
    check("fstring-placeholder", names(srcf), ["{expr}"])

    check("as-syntax-excluded",
          names(assign("CREATE TABLE public.tenants AS SELECT 1")), [])

    check("trap-docstring",
          names(Q + "\nCREATE TABLE foo (id INTEGER)\n" + Q + "\n"), [])
    check("trap-assert",
          names("assert 'CREATE TABLE bar' in sql\n"), [])
    check("trap-comment",
          names("# CREATE TABLE baz\nx = 1\n"), [])


def pair_exit():
    base_src = assign("CREATE TABLE leads (id INTEGER)")
    head_src = base_src + assign("CREATE TABLE staff (id INTEGER)")
    orig_changed = m.changed_test_files
    orig_file_at = m.file_at
    os.environ["BASE_SHA"] = "BASE"
    os.environ["HEAD_SHA"] = "HEAD"
    m.changed_test_files = lambda b, h: ["backend/tests/test_pair_probe.py"]
    try:
        m.file_at = lambda sha, path: head_src if sha == "HEAD" else base_src
        check("pair-violation-exit1", m.main(), 1)
        m.file_at = lambda sha, path: base_src
        check("pair-clean-exit0", m.main(), 0)
    finally:
        m.changed_test_files = orig_changed
        m.file_at = orig_file_at
        os.environ.pop("BASE_SHA", None)
        os.environ.pop("HEAD_SHA", None)


def real_data():
    sha = subprocess.run(["git", "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    files = m.list_test_files(sha)
    check("real-file-list-nonempty", len(files) > 0, True)
    for trap in sorted(m.EXCLUDE_FILES):
        check("real-excluded " + trap, trap in files, False)
    parse_failed = []
    if_names = []
    hit_files = 0
    total = 0
    for path in sorted(files):
        try:
            found = m.tables_in_source(m.file_at(sha, path))
        except Exception as exc:
            parse_failed.append("{}: {}".format(path, exc))
            continue
        if found:
            hit_files += 1
            total += len(found)
        for _, name in found:
            if name.upper() == "IF":
                if_names.append(path)
    check("real-parse-failed", parse_failed, [])
    check("real-if-zero", if_names, [])
    print("REAL SUMMARY sha={} files={} tables={}".format(sha, hit_files, total))


def main():
    synthetic()
    pair_exit()
    real_data()
    if FAILED:
        print("RESULT: FAIL " + ",".join(FAILED))
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
