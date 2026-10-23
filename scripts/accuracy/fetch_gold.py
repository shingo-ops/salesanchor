#!/usr/bin/env python3
"""本番DBに置いた正解表を、読むだけの窓口(ADR-1042)から取り出してTSVにする道具(ADR-1043)。標準ライブラリのみ。

使い方:
  python3 scripts/accuracy/fetch_gold.py --version gold_v1 --out /tmp/gold_v1.tsv [--url U]

- 取り出した本文の sha256 と行数を、版の記録(accuracy_gold_versions)と照らし合わせる。
  一致したときだけ --out に書く。違えば何も書かず終了コード1(既にあるファイルは触らない)。
- 鍵: クラウドでは通信の仕組みが自動でヘッダを付ける。手元で試すときだけ、環境変数 READ_WINDOW_TOKEN が
  あればヘッダ X-Read-Window-Token に付ける。鍵の値は表示もログもしない。
"""
import argparse
import hashlib
import importlib.util
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_URL = "https://api.salesanchor.jp/api/v1/ops/read-window/query"
TIMEOUT = 90
VERSION_RE = re.compile(r"^[a-z0-9_]+$")
ROW_LIMIT = 5000


def _load_gold_to_sql():
    spec = importlib.util.spec_from_file_location("gold_to_sql", os.path.join(HERE, "gold_to_sql.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_g = _load_gold_to_sql()


def version_sql(version):
    """版の記録(sha256・行数)を1行で返す問い合わせ。"""
    if not VERSION_RE.fullmatch(version):
        raise ValueError("version は英小文字・数字・_ だけです")
    return ("select file_sha256, row_count, post_count from ai_ro.public__accuracy_gold_versions "
            "where gold_version = '%s'" % version)


def rows_sql(version):
    """正解表の中身を、元の見出しを別名にして row_no 順に返す問い合わせ。"""
    if not VERSION_RE.fullmatch(version):
        raise ValueError("version は英小文字・数字・_ だけです")
    cols = []
    for head, col in zip(_g.HEADER, _g.DB_COLS):
        expr = "post_id::text" if col == "post_id" else col
        cols.append('%s as "%s"' % (expr, head))
    return ("-- limit=%d\nselect %s from ai_ro.public__accuracy_gold_rows "
            "where gold_version = '%s' order by row_no" % (ROW_LIMIT, ", ".join(cols), version))


def post(url, sql, token=None):
    """窓口に SQL を送り (HTTP番号, rc文字列, 本文bytes) を返す。通信エラーは (0, '', b'')。"""
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if token:
        headers["X-Read-Window-Token"] = token
    req = urllib.request.Request(url, data=sql.encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.headers.get("X-Read-Window-Rc", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("X-Read-Window-Rc", ""), e.read()
    except (urllib.error.URLError, OSError) as e:
        return 0, "", type(e).__name__.encode("ascii", "replace")


def first_line(body):
    return body.decode("utf-8", "replace").split("\n", 1)[0][:200]


def fail_http(status, rc, body):
    sys.stderr.write("STOP: http=%s rc=%s %s\n" % (status, rc or "-", first_line(body)))
    return 1


def parse_version_reply(body):
    """見出し行+1行を (sha256, row_count, post_count) にする。0行なら None。形が違えば ValueError。"""
    lines = body.decode("utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or lines[0].split("\t") != ["file_sha256", "row_count", "post_count"]:
        raise ValueError("版の応答の見出しが想定と違います")
    if len(lines) == 1:
        return None
    if len(lines) != 2:
        raise ValueError("版の応答が 1 行ではありません")
    cols = lines[1].split("\t")
    if len(cols) != 3:
        raise ValueError("版の応答の列数が想定と違います")
    return cols[0], int(cols[1]), int(cols[2])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default=DEFAULT_URL)
    a = ap.parse_args(argv)
    token = os.environ.get("READ_WINDOW_TOKEN") or None
    try:
        vsql = version_sql(a.version)
        rsql = rows_sql(a.version)
    except ValueError as e:
        sys.stderr.write("STOP: %s\n" % e)
        return 1

    status, rc, body = post(a.url, vsql, token)
    if status != 200 or rc != "0":
        return fail_http(status, rc, body)
    try:
        rec = parse_version_reply(body)
    except (ValueError, UnicodeDecodeError) as e:
        sys.stderr.write("STOP: %s\n" % e)
        return 1
    if rec is None:
        sys.stderr.write("STOP: 版がありません(%s)。投入前です\n" % a.version)
        return 1
    want_sha, want_rows, _posts = rec

    status, rc, body = post(a.url, rsql, token)
    if status != 200 or rc != "0":
        return fail_http(status, rc, body)
    got_sha = hashlib.sha256(body).hexdigest()
    got_rows = body.count(b"\n") - 1
    if got_sha != want_sha or got_rows != want_rows:
        sys.stderr.write("STOP: 取り出した表が版の記録と違います(sha256 一致=%s, 行数 取得=%d 記録=%d)。ファイルは書いていません\n"
                         % (got_sha == want_sha, got_rows, want_rows))
        return 1
    with open(a.out, "wb") as f:
        f.write(body)
    print("sha256=%s rows=%d" % (got_sha[:12], got_rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
