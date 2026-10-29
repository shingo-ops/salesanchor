#!/usr/bin/env python3
"""投稿→仕入元の番号、商品→中分類 の対応表を、読むだけの窓口(ADR-1042)から作る道具。標準ライブラリのみ。

使い方:
  python3 -I scripts/accuracy/fetch_groups.py --keys <keys.tsv> --out <対応表.tsv> [--url U]

- keys.tsv: 見出し `key\tmsg_id\tproduct_id`(product_id は空でもよい)。
- 対応表: 見出し `key\t仕入元\t中分類`。仕入元は supplier_id の数字だけ(名前は引かない)。
  商品が空・見つからないときの中分類は `商品なし`。
- 窓口に必要な列が無ければ何も書かず `BLOCKED:` で終了コード1。id の形が不正なら終了コード2。
- 鍵は fetch_gold.py と同じ(READ_WINDOW_TOKEN は手元の試験用)。
"""
import argparse
import csv
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
NUM_RE = re.compile(r"^[0-9]{1,18}$")
BATCH = 500
NO_PRODUCT = "商品なし"
UNKNOWN = "不明"

_spec = importlib.util.spec_from_file_location("fetch_gold", os.path.join(HERE, "fetch_gold.py"))
fg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fg)

NEEDED = {
    "public__source_messages": ("id", "supplier_channel_id"),
    "public__supplier_channels": ("id", "supplier_id"),
    "public__products": ("id", "work_id"),
    "public__type_master": ("id", "name_ja"),
}


class Stop(Exception):
    def __init__(self, msg, code):
        super().__init__(msg)
        self.code = code


def columns_sql():
    names = ", ".join("'%s'" % t for t in NEEDED)
    return ("select table_name, column_name from information_schema.columns "
            "where table_schema = 'ai_ro' and table_name in (%s)" % names)


def supplier_sql(msg_ids):
    ids = ", ".join("'%s'" % i for i in msg_ids)
    return ("-- limit=%d\nselect m.id::text, c.supplier_id from ai_ro.public__source_messages m "
            "join ai_ro.public__supplier_channels c on c.id = m.supplier_channel_id "
            "where m.id in (%s)" % (fg.ROW_LIMIT, ids))


def category_sql(product_ids):
    ids = ", ".join(product_ids)
    return ("-- limit=%d\nselect p.id, t.name_ja from ai_ro.public__products p "
            "join ai_ro.public__type_master t on t.id = p.work_id "
            "where p.id in (%s)" % (fg.ROW_LIMIT, ids))


def query(url, sql, token, header):
    status, rc, body = fg.post(url, sql, token)
    if status != 200 or rc != "0":
        raise Stop("STOP: http=%s rc=%s %s" % (status, rc or "-", fg.first_line(body)), 1)
    lines = body.decode("utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or lines[0].split("\t") != header:
        raise Stop("STOP: 応答の見出しが想定と違います", 1)
    rows = [l.split("\t") for l in lines[1:]]
    if len(rows) >= fg.ROW_LIMIT or any(len(r) != len(header) for r in rows):
        raise Stop("STOP: 応答の行数または列数が想定と違います", 1)
    return rows


def check_columns(url, token):
    rows = query(url, columns_sql(), token, ["table_name", "column_name"])
    have = {(r[0], r[1]) for r in rows}
    for t, cols in NEEDED.items():
        for c in cols:
            if (t, c) not in have:
                raise Stop("BLOCKED: 窓口に %s.%s が無い" % (t, c), 1)


def read_keys(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    if not rows or rows[0] != ["key", "msg_id", "product_id"]:
        raise Stop("STOP: keys の見出しが想定と違います", 2)
    out, seen = [], set()
    for i, r in enumerate(rows[1:], 2):
        if len(r) != 3:
            raise Stop("STOP: keys %d 行目の列数が違います" % i, 2)
        key, mid, pid = r
        if not UUID_RE.fullmatch(mid):
            raise Stop("STOP: keys %d 行目の msg_id の形が不正です" % i, 2)
        if pid != "" and not NUM_RE.fullmatch(pid):
            raise Stop("STOP: keys %d 行目の product_id の形が不正です" % i, 2)
        if key in seen:
            raise Stop("STOP: keys %d 行目の key が重複しています" % i, 2)
        seen.add(key)
        out.append((key, mid, pid))
    return out


def batches(seq):
    for i in range(0, len(seq), BATCH):
        yield seq[i:i + BATCH]


def run(keys_path, out_path, url, token):
    keys = read_keys(keys_path)
    check_columns(url, token)
    sup, cat = {}, {}
    for b in batches(sorted({m for _, m, _ in keys})):
        for mid, sid in query(url, supplier_sql(b), token, ["id", "supplier_id"]):
            sup[mid] = sid
    for b in batches(sorted({p for _, _, p in keys if p})):
        for pid, name in query(url, category_sql(b), token, ["id", "name_ja"]):
            cat[pid] = name
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["key", "仕入元", "中分類"])
        for key, mid, pid in keys:
            w.writerow([key, sup.get(mid, UNKNOWN), cat.get(pid, NO_PRODUCT) if pid else NO_PRODUCT])
    print("keys=%d" % len(keys))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--keys", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default=fg.DEFAULT_URL)
    a = ap.parse_args(argv)
    token = os.environ.get("READ_WINDOW_TOKEN") or None
    try:
        run(a.keys, a.out, a.url, token)
    except Stop as e:
        sys.stderr.write(str(e) + "\n")
        return e.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
