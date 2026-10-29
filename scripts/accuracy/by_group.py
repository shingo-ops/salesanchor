#!/usr/bin/env python3
"""判定表を仕入元ごと・中分類ごとに分けて正答率と幅を出す道具。標準ライブラリのみ。DB には接続しない。

使い方:
  python3 -I scripts/accuracy/by_group.py --verdicts <判定表.tsv> --groups <対応表.tsv> --out-dir <出力先>

- 判定表: 見出し `key\t項目\t判定`。判定は OK / NG / NOWORD。
- 対応表: 見出し `key\t仕入元\t中分類`。空は 不明。
- 出力先はリポジトリの外だけ。overall.tsv / by_supplier.tsv / by_category.tsv ができる。
- 終了コード: 0 正常 / 2 入力の不備 / 3 合計が合わない(何も書かない)。
"""
import argparse
import csv
import math
import os
import subprocess
import sys

Z = 1.959964
UNKNOWN = "不明"
ALL_ITEMS = "全項目"
VERDICTS = ("OK", "NG", "NOWORD")
OUT_HEADER = ["区分", "項目", "正しい", "違う", "答え無し", "正答率", "幅の下", "幅の上", "参考"]


class Stop(Exception):
    def __init__(self, msg, code=2):
        super().__init__(msg)
        self.code = code


def read_tsv(path, header):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    if not rows or rows[0] != header:
        raise Stop("%s: 見出しが想定と違います" % os.path.basename(path))
    return rows[1:]


def load_verdicts(path):
    items, seen, data = [], set(), {}
    for i, r in enumerate(read_tsv(path, ["key", "項目", "判定"]), 2):
        if len(r) != 3:
            raise Stop("判定表 %d 行目: 列数が違います" % i)
        key, item, v = r
        if v not in VERDICTS:
            raise Stop("判定表 %d 行目: 判定の値が不正です" % i)
        if (key, item) in seen:
            raise Stop("判定表 %d 行目: key と項目の組が重複しています" % i)
        seen.add((key, item))
        if item not in items:
            items.append(item)
        data.setdefault(key, {})[item] = v
    return items, data


def load_groups(path):
    out = {}
    for i, r in enumerate(read_tsv(path, ["key", "仕入元", "中分類"]), 2):
        if len(r) != 3:
            raise Stop("対応表 %d 行目: 列数が違います" % i)
        if r[0] in out:
            raise Stop("対応表 %d 行目: key が重複しています" % i)
        out[r[0]] = (r[1] or UNKNOWN, r[2] or UNKNOWN)
    return out


def wilson(k, n):
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def count_by(data, items, label_of):
    """{区分: {項目: [正しい, 違う, 答え無し]}} を返す。全項目は key ごとの合成。"""
    out = {}
    for key in sorted(data):
        cell = out.setdefault(label_of(key), {it: [0, 0, 0] for it in items + [ALL_ITEMS]})
        vs = data[key]
        for it, v in vs.items():
            cell[it][{"OK": 0, "NG": 1, "NOWORD": 2}[v]] += 1
        cell[ALL_ITEMS][1 if "NG" in vs.values() else 0] += 1
    return out


def check_sums(overall, split, items):
    for it in items + [ALL_ITEMS]:
        for idx in range(3):
            total = sum(c[it][idx] for c in split.values())
            if total != overall["全体"][it][idx]:
                raise Stop("STOP: 合計が合いません %s" % it, 3)


def fmt_rows(counts, items):
    labels = sorted(counts, key=lambda s: (s == UNKNOWN, s))
    rows = []
    for lab in labels:
        for it in items + [ALL_ITEMS]:
            ok, ng, nw = counts[lab][it]
            n = ok + ng
            if n:
                rate = "%.1f" % (ok / n * 100)
                lo, hi = wilson(ok, n)
                lo_s, hi_s = "%.1f" % (lo * 100), "%.1f" % (hi * 100)
            else:
                rate = lo_s = hi_s = "-"
            rows.append([lab, it, ok, ng, nw, rate, lo_s, hi_s, "参考" if n < 20 else ""])
    return rows


def check_out_dir(out_dir):
    real = os.path.realpath(out_dir)
    probe = real
    while not os.path.isdir(probe):
        probe = os.path.dirname(probe)
    for c in {probe, os.path.dirname(os.path.realpath(__file__))}:
        r = subprocess.run(["git", "-C", c, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            top = os.path.realpath(r.stdout.strip())
            if real == top or real.startswith(top + os.sep):
                raise Stop("--out-dir がリポジトリの中です（社外秘の流出防止）")


def write_tsv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(OUT_HEADER)
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--groups", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    try:
        check_out_dir(a.out_dir)
        items, data = load_verdicts(a.verdicts)
        groups = load_groups(a.groups)
        missing = sum(1 for k in data if k not in groups)
        if missing:
            sys.stderr.write("対応表に無い key: %d 件（不明に入れました）\n" % missing)
        grp = lambda k: groups.get(k, (UNKNOWN, UNKNOWN))
        overall = count_by(data, items, lambda k: "全体")
        by_sup = count_by(data, items, lambda k: grp(k)[0])
        by_cat = count_by(data, items, lambda k: grp(k)[1])
        if not data:
            overall = {"全体": {it: [0, 0, 0] for it in items + [ALL_ITEMS]}}
        check_sums(overall, by_sup, items)
        check_sums(overall, by_cat, items)
    except Stop as e:
        msg = str(e)
        sys.stderr.write(msg if msg.startswith("STOP:") else "STOP: " + msg)
        sys.stderr.write("\n")
        return e.code
    os.makedirs(a.out_dir, exist_ok=True)
    write_tsv(os.path.join(a.out_dir, "overall.tsv"), fmt_rows(overall, items))
    write_tsv(os.path.join(a.out_dir, "by_supplier.tsv"), fmt_rows(by_sup, items))
    write_tsv(os.path.join(a.out_dir, "by_category.tsv"), fmt_rows(by_cat, items))
    print("keys=%d items=%d" % (len(data), len(items)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
