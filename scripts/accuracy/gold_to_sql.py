#!/usr/bin/env python3
"""正解表(TSV)から、本番DBへの投入SQL 3本を作る道具(ADR-1043)。標準ライブラリのみ。

使い方:
  python3 scripts/accuracy/gold_to_sql.py --gold G --version V --note N --out-dir D

- 出力先 D はリポジトリの外だけ。中を指すと止まる(正解表の中身は社外秘のため)。
- 点検のどれかが外れたら、ファイルを1つも書かず、理由を標準エラーに1行出して終了コード2。
  理由には値そのものを入れない(何行目・何列目だけ)。
- 出力: 01_precheck.sql / 02_apply.sql / 03_verify.sql(戻し用ファイルは作らない。戻し方は design.md §7)
- 流すのは Opus(担当は流さない)。このファイル自体は値を含まない。
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys
import uuid

HEADER = ["投稿id", "price_line", "lines", "許容する行", "E2_price", "E3_quantity", "A1_product_id",
          "A2_condition", "A3_unit", "A4_status", "A5_ship", "A4根拠", "迷い", "除外", "裁定根拠", "PO確認"]
# HEADER と同じ並びの DB 列名(migrations/20261023_180000_create_accuracy_gold.sql)
DB_COLS = ["post_id", "price_line", "lines", "allowed_lines", "e2_price", "e3_quantity", "a1_product_id",
           "a2_condition", "a3_unit", "a4_status", "a5_ship", "a4_basis", "hesitation", "exclusion",
           "ruling_basis", "po_check"]
VERSION_RE = re.compile(r"^[a-z0-9_]+$")
CHUNK = 500
HERE = os.path.dirname(os.path.abspath(__file__))


class Stop(Exception):
    pass


def lit(v):
    return "'" + v.replace("'", "''") + "'"


def check_chars(s, where):
    for ch in s:
        if ch in ('\\', '"', '\r') or (ord(ch) < 0x20 and ch not in ('\t', '\n')):
            raise Stop("%s に使えない文字があります" % where)


def parse_gold(raw):
    """バイト列を点検して (行のリスト[16列のlist]) を返す。外れたら Stop。"""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Stop("正解表が UTF-8 ではありません")
    if "\r" in text:
        raise Stop("正解表に CR があります")
    if not text.endswith("\n"):
        raise Stop("正解表の末尾が改行ではありません")
    lines = text[:-1].split("\n")
    head = lines[0].split("\t")
    if head != HEADER:
        raise Stop("見出しが期待と違います(1行目)")
    rows = []
    for i, line in enumerate(lines[1:], start=2):
        cols = line.split("\t")
        if len(cols) != len(HEADER):
            raise Stop("%d 行目の列数が %d ではありません" % (i, len(HEADER)))
        for j, v in enumerate(cols, start=1):
            check_chars(v, "%d 行目 %d 列目" % (i, j))
        pid = cols[0]
        try:
            ok = str(uuid.UUID(pid)) == pid
        except ValueError:
            ok = False
        if not ok:
            raise Stop("%d 行目の投稿idが小文字 uuid ではありません" % i)
        rows.append(cols)
    if not rows:
        raise Stop("データ行がありません")
    return rows


def repo_roots():
    roots = []
    for cwd in (os.getcwd(), HERE):
        try:
            r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True)
        except OSError:
            continue
        if r.returncode == 0 and r.stdout.strip():
            roots.append(os.path.realpath(r.stdout.strip()))
    return roots


def inside(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


def check_out_dir(out_dir):
    for root in repo_roots():
        if inside(out_dir, root):
            raise Stop("--out-dir がリポジトリの中です")


def header_comment(version):
    return ("-- ADR-1043 正解表の投入(版 %s)。本番での実行は Opus(担当は実行しない)。社外秘。リポジトリに入れない。\n" % version)


def build_precheck(version, rows):
    post_ids = sorted({r[0] for r in rows})
    prod_ids = sorted({r[6] for r in rows if re.fullmatch(r"[0-9]+", r[6])}, key=int)
    out = [header_comment(version),
           "\\set ON_ERROR_STOP on\n",
           "BEGIN;\n",
           "SET LOCAL app.is_operator = 'true';\n\n",
           "-- 表 2 つがあること\n",
           "SELECT CASE WHEN to_regclass('public.accuracy_gold_versions') IS NOT NULL "
           "AND to_regclass('public.accuracy_gold_rows') IS NOT NULL THEN 1 ELSE 1 / 0 END;\n\n",
           "-- その版がまだ無いこと\n",
           "SELECT CASE WHEN count(*) = 0 THEN 1 ELSE 1 / 0 END FROM public.accuracy_gold_versions "
           "WHERE gold_version = %s;\n\n" % lit(version),
           "-- 投稿idが source_messages に全部あること\n",
           "WITH m AS (SELECT count(*) AS n FROM (VALUES %s) AS v(id) "
           "WHERE NOT EXISTS (SELECT 1 FROM public.source_messages s WHERE s.id = v.id::uuid))\n"
           "SELECT 'MISSING_POSTS ' || n, CASE WHEN n = 0 THEN 1 ELSE 1 / 0 END FROM m;\n\n"
           % ", ".join("(%s)" % lit(p) for p in post_ids)]
    out.append("-- a1_product_id の数字が products に全部あること\n")
    if prod_ids:
        out.append("WITH m AS (SELECT count(*) AS n FROM (VALUES %s) AS v(id) "
                   "WHERE NOT EXISTS (SELECT 1 FROM public.products p WHERE p.id = v.id::integer))\n"
                   "SELECT 'MISSING_PRODUCTS ' || n, CASE WHEN n = 0 THEN 1 ELSE 1 / 0 END FROM m;\n\n"
                   % ", ".join("(%s)" % lit(p) for p in prod_ids))
    else:
        out.append("SELECT 'MISSING_PRODUCTS 0';\n\n")
    out.append("ROLLBACK;\n")
    out.append("SELECT 'PRECHECK_END';\n")
    return "".join(out)


def build_apply(version, note, sha, rows, posts):
    n = len(rows)
    out = [header_comment(version),
           "-- 使い方(終わり方を必ず指定する):\n"
           "--   試し  : psql -v end=ROLLBACK -f 02_apply.sql   (件数を確かめて最後に ROLLBACK。何も残らない)\n"
           "--   本番  : psql -v end=COMMIT   -f 02_apply.sql   (試しが全部 OK だった後だけ)\n"
           "\\set ON_ERROR_STOP on\n"
           "\\if :{?end}\n"
           "\\else\n"
           "  \\echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'\n"
           "  SELECT 1 / 0;\n"
           "\\endif\n"
           "BEGIN;\n"
           "SET LOCAL app.is_operator = 'true';\n\n",
           "INSERT INTO public.accuracy_gold_versions (gold_version, file_sha256, row_count, post_count, note)\n"
           "VALUES (%s, %s, %d, %d, %s);\n\n" % (lit(version), lit(sha), n, posts, lit(note))]
    cols = ", ".join(["gold_version", "row_no"] + DB_COLS)
    for start in range(0, n, CHUNK):
        vals = []
        for k, r in enumerate(rows[start:start + CHUNK], start=start + 1):
            vals.append("(" + ", ".join([lit(version), str(k), lit(r[0]) + "::uuid"] + [lit(v) for v in r[1:]]) + ")")
        out.append("INSERT INTO public.accuracy_gold_rows (%s) VALUES\n%s;\n\n" % (cols, ",\n".join(vals)))
    out.append("SELECT CASE WHEN count(*) = %d THEN 1 ELSE 1 / 0 END FROM public.accuracy_gold_rows "
               "WHERE gold_version = %s;\n\n" % (n, lit(version)))
    out.append(":end;\nSELECT 'APPLY_END';\n")
    return "".join(out)


def build_verify(version, rows, posts):
    v = lit(version)
    return (header_comment(version) +
            "\\set ON_ERROR_STOP on\n"
            "BEGIN;\n"
            "SET LOCAL app.is_operator = 'true';\n"
            "SELECT 'VERSION ' || gold_version || ' rows=' || row_count || ' posts=' || post_count "
            "FROM public.accuracy_gold_versions WHERE gold_version = %(v)s;\n"
            "-- 行数・投稿数が版の記録と同じこと\n"
            "SELECT CASE WHEN count(*) = %(n)d AND count(DISTINCT post_id) = %(p)d THEN 1 ELSE 1 / 0 END\n"
            "  FROM public.accuracy_gold_rows WHERE gold_version = %(v)s;\n"
            "SELECT CASE WHEN row_count = %(n)d AND post_count = %(p)d THEN 1 ELSE 1 / 0 END\n"
            "  FROM public.accuracy_gold_versions WHERE gold_version = %(v)s;\n"
            "-- row_no が 1〜N の連番であること\n"
            "SELECT CASE WHEN min(row_no) = 1 AND max(row_no) = %(n)d AND count(*) = %(n)d THEN 1 ELSE 1 / 0 END\n"
            "  FROM public.accuracy_gold_rows WHERE gold_version = %(v)s;\n"
            "ROLLBACK;\n"
            "SELECT 'VERIFY_END';\n" % {"v": v, "n": len(rows), "p": posts})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gold", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--note", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    try:
        if not VERSION_RE.fullmatch(a.version):
            raise Stop("--version は英小文字・数字・_ だけです")
        if any(c in a.note for c in ("\n", "\r", "\\", "\x00")):
            raise Stop("--note に使えない文字があります")
        check_out_dir(a.out_dir)
        try:
            with open(a.gold, "rb") as f:
                raw = f.read()
        except OSError:
            raise Stop("--gold を読めません")
        rows = parse_gold(raw)
        sha = hashlib.sha256(raw).hexdigest()
        posts = len({r[0] for r in rows})
        files = {
            "01_precheck.sql": build_precheck(a.version, rows),
            "02_apply.sql": build_apply(a.version, a.note, sha, rows, posts),
            "03_verify.sql": build_verify(a.version, rows, posts),
        }
    except Stop as e:
        sys.stderr.write("STOP: %s\n" % e)
        return 2
    os.makedirs(a.out_dir, exist_ok=True)
    for name, body in files.items():
        p = os.path.join(a.out_dir, name)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        print(p)
    print("sha256=%s" % sha)
    print("rows=%d" % len(rows))
    print("posts=%d" % posts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
