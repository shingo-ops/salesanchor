#!/usr/bin/env python3
"""v102 正答率の採点の道具（読み取り専用・標準ライブラリのみ）。

使い方:
  python3 -I scripts/accuracy/score_v102.py --gold GOLD.tsv --snapshot-dir DIR --out-dir OUT
詳細は scripts/accuracy/README.md と docs/handoff/accuracy-measurement/card-bin2.md を参照。
"""
import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys

GOLD_COLS = ["投稿id", "price_line", "lines", "許容する行", "E2_price", "E3_quantity",
             "A1_product_id", "A2_condition", "A3_unit", "A4_status", "A5_ship", "除外"]
SNAP_COLS = ["extraction_item_id", "line_start", "line_end", "source_lines", "raw_price",
             "raw_quantity", "product_id", "condition_canonical",
             "unit_canonical", "status", "ship_ja", "price_normalized",
             "quantity_normalized", "exclusion"]
NO_ANSWER = ("(除外)", "対象外")
EXCL_ALLOWED = ("", "ALL", "A1", "A2A3", "A1+A2A3")
A4_MAP = {"在庫あり": "In Stock", "予約": "Pre-order", "売り切れ": "Sold out"}


class Stop(Exception):
    pass


def read_tsv(path, required):
    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        try:
            header = next(rd)
        except StopIteration:
            raise Stop("空のファイル: %s" % os.path.basename(path))
        idx = {h: i for i, h in enumerate(header)}
        missing = [c for c in required if c not in idx]
        if missing:
            raise Stop("必要な列がありません (%s): %s" % (os.path.basename(path), ",".join(missing)))
        rows = []
        for r in rd:
            if not r:
                continue
            rows.append({c: (r[idx[c]] if idx[c] < len(r) else "") for c in required})
        return rows


def line_set(text):
    return {int(x) for x in re.findall(r"\d+", text or "")}


def sys_lines(r):
    s = line_set(r["source_lines"])
    if s:
        return s
    a, b = r["line_start"], r["line_end"]
    if a.strip().isdigit() and b.strip().isdigit():
        return set(range(int(a), int(b) + 1))
    return set()


def digits(text):
    return "".join(re.findall(r"\d", text or ""))


def norm_int(text):
    t = (text or "").strip()
    if not t:
        return ""
    try:
        return str(int(float(t)))
    except ValueError:
        return t


def norm_ship(text):
    t = re.sub(r"[\s　]", "", text or "")
    return re.sub(r"[【】()（）]", "", t)


def pline_num(g):
    m = re.search(r"\d+", g["price_line"])
    return int(m.group()) if m else 0


def check_spelling(gold, snaps):
    """綴りだけ違う値の組（大文字小文字・前後空白）があれば止める。"""
    problems = []
    for gc, sc in (("A2_condition", "condition_canonical"), ("A3_unit", "unit_canonical")):
        vals = {r[gc] for r in gold if r[gc] not in NO_ANSWER} | {r[sc] for r in snaps}
        groups = {}
        for v in vals:
            groups.setdefault(v.strip().casefold(), set()).add(v)
        for k, vs in groups.items():
            if len(vs) > 1:
                problems.append((gc, sorted(vs)))
    if problems:
        raise Stop("綴りが揃わない値の組: %r" % (problems,))


def a4_table(gold, snaps):
    counts = {}
    for r in snaps:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    unknown = [v for v in counts if v not in A4_MAP.values()]
    gunknown = [r["A4_status"] for r in gold if r["A4_status"] not in A4_MAP and r["A4_status"] not in NO_ANSWER]
    if unknown or gunknown:
        raise Stop("A4 の読み替え表に無い値: system=%r gold=%r" % (unknown, sorted(set(gunknown))))
    return {k: (v, counts.get(v, 0)) for k, v in A4_MAP.items()}


def match_post(golds, items):
    """golds: 1投稿の正解の件。items: 同じ投稿のシステムの件（全行）。
    戻り値: {正解のindex: システムの件}, 余ったシステムの件のリスト"""
    used = set()
    pairs = {}
    order = sorted(range(len(golds)), key=lambda i: (pline_num(golds[i]), i))
    for gi in order:
        g = golds[gi]
        pl = pline_num(g)
        glines = line_set(g["lines"])
        best = None
        for it in items:
            if it["extraction_item_id"] in used:
                continue
            try:
                a, b = int(it["line_start"]), int(it["line_end"])
            except ValueError:
                continue
            if not (a <= pl <= b):
                continue
            key = (-len(glines & sys_lines(it)), it["extraction_item_id"])
            if best is None or key < best[0]:
                best = (key, it)
        if best:
            used.add(best[1]["extraction_item_id"])
            pairs[gi] = best[1]
    extra = [it for it in items if it["extraction_item_id"] not in used]
    return pairs, extra


class Tally:
    def __init__(self):
        self.ok = self.ng = self.na = 0

    def add(self, v):
        if v == "ok":
            self.ok += 1
        elif v == "ng":
            self.ng += 1
        else:
            self.na += 1

    def rate(self):
        d = self.ok + self.ng
        return "%.1f%%" % (100.0 * self.ok / d) if d else "-"


def judge(g, it, field):
    """戻り値: (判定 ok/ng/na/skip, 正解の表示, システムの表示, 段)"""
    ex = g["除外"]
    if field == "A1" and "A1" in ex:
        return "skip", "", ""
    if field in ("A2", "A3") and "A2" in ex:
        return "skip", "", ""
    if field == "E1":
        req = line_set(g["lines"])
        allow = req | line_set(g["許容する行"])
        s = sys_lines(it)
        return ("ok" if req <= s <= allow else "ng"), g["lines"] + "|" + g["許容する行"], str(sorted(s))
    gv = {"E2": g["E2_price"], "E3": g["E3_quantity"], "A1": g["A1_product_id"],
          "A2": g["A2_condition"], "A3": g["A3_unit"], "A4": g["A4_status"],
          "A5": g["A5_ship"]}[field]
    if gv in NO_ANSWER:
        return "na", gv, ""
    return None, gv, None  # 呼び出し側で値を比べる


def score(gold, snap_by_post, verdicts=None):
    all_snaps = [r for rs in snap_by_post.values() for r in rs]
    for g in gold:
        if g["除外"] not in EXCL_ALLOWED:
            raise Stop("想定外の除外の書き方: %r" % g["除外"])
    check_spelling(gold, all_snaps)
    table = a4_table(gold, all_snaps)

    key_of = {id(g): i for i, g in enumerate(gold, 1)}
    vmap = {"ok": "OK", "ng": "NG", "na": "NOWORD", "skip": "SKIP"}

    def vrec(g, item, verdict):
        if verdicts is not None:
            verdicts.append((key_of[id(g)], item, vmap[verdict]))

    by_post = {}
    for g in gold:
        by_post.setdefault(g["投稿id"], []).append(g)

    T = {}

    def tl(k):
        return T.setdefault(k, Tally())

    errors = []
    c1 = extra = 0
    nocur_posts = 0
    unmatched_snapshot_posts = 0
    for pid in sorted(by_post):
        golds = by_post[pid]
        items = snap_by_post.get(pid)
        if pid not in snap_by_post:
            unmatched_snapshot_posts += 1
        if not items:
            nocur_posts += 1
            c1 += sum(1 for g in golds if g["除外"] != "ALL")
            for g in golds:
                if g["除外"] != "ALL":
                    vrec(g, "C1", "ng")
            continue
        pairs, ex = match_post(golds, items)
        extra += len(ex)
        for gi, g in enumerate(golds):
            if g["除外"] == "ALL":
                continue
            it = pairs.get(gi)
            if it is None:
                c1 += 1
                vrec(g, "C1", "ng")
                continue
            vrec(g, "C1", "ok")
            res = {}

            def rec(stage, field, verdict, gv, sv):
                tl((field, stage)).add(verdict)
                if verdict == "ng":
                    errors.append((pid, g["price_line"], field, stage, gv, sv))

            v, gv, sv = judge(g, it, "E1")
            e1ok = v == "ok"
            rec("Gemini", "E1", v, gv, sv)
            vrec(g, "E1", v)
            # E2 / E3
            for fld, graw, sraw_g, sraw_s in (("E2", "E2_price", "raw_price", "price_normalized"),
                                              ("E3", "E3_quantity", "raw_quantity", "quantity_normalized")):
                gval = g[graw]
                if gval in NO_ANSWER:
                    gres = sres = ("na", gval, "")
                else:
                    gd = digits(gval)
                    a = digits(it[sraw_g])
                    b = norm_int(it[sraw_s])
                    gres = ("ok" if a == gd else "ng", gval, it[sraw_g])
                    sres = ("ok" if b == gd else "ng", gval, it[sraw_s])
                rec("Gemini", fld, *gres)
                if e1ok:
                    rec("システム", fld, *sres)
                    vrec(g, fld, sres[0])
                else:
                    vrec(g, fld, "skip")
            # A1..A5
            for fld in ("A1", "A2", "A3", "A4", "A5"):
                v, gv, sv = judge(g, it, fld)
                if v is None:
                    if fld == "A1":
                        if gv == "未登録":
                            v = "ok" if it["product_id"] == "" else "ng"
                        elif gv == "商品でない":
                            v = "ok" if it["exclusion"] != "" else "ng"
                        else:
                            v = "ok" if it["product_id"] == gv else "ng"
                        sv = it["product_id"] if gv != "商品でない" else it["exclusion"]
                    elif fld == "A2":
                        sv = it["condition_canonical"]
                        v = "ok" if sv == gv else "ng"
                    elif fld == "A3":
                        sv = it["unit_canonical"]
                        v = "ok" if sv == gv else "ng"
                    elif fld == "A4":
                        sv = it["status"]
                        v = "ok" if sv == table[gv][0] else "ng"
                    else:
                        sv = it["ship_ja"]
                        if gv == "無し":
                            v = "ok" if norm_ship(sv) == "" else "ng"
                        else:
                            v = "ok" if norm_ship(sv) == norm_ship(gv) else "ng"
                vrec(g, fld, v)
                if v == "skip":
                    continue
                rec("通し", fld, v, gv, sv)
                if e1ok:
                    tl((fld, "システム")).add(v)
                    if v == "ng":
                        errors.append((pid, g["price_line"], fld, "システム", gv, sv))
                if fld == "A4" and g["A4_status"] == "予約":
                    tl(("A4予約", "通し")).add(v)
    errors.sort(key=lambda e: (e[0], pline_num({"price_line": e[1]}), e[2], e[3]))
    if verdicts is not None:
        order = {n: i for i, n in enumerate(VERDICT_ITEMS)}
        verdicts.sort(key=lambda r: (r[0], order[r[1]]))
    return T, errors, c1, extra, nocur_posts, unmatched_snapshot_posts, table


VERDICT_ITEMS = ("C1", "E1", "E2", "E3", "A1", "A2", "A3", "A4", "A5")


def check_verdicts(T, c1, verdicts):
    """V.tsv の数を result.tsv の元（T・c1）と照らす。合わない項目名のリストを返す。"""
    cnt = {}
    for _, item, v in verdicts:
        cnt.setdefault(item, {}).setdefault(v, 0)
        cnt[item][v] += 1

    def got(item, v):
        return cnt.get(item, {}).get(v, 0)

    bad = []
    if got("C1", "NG") != c1:
        bad.append("C1")
    for item, stage in (("E1", "Gemini"), ("E2", "システム"), ("E3", "システム"),
                        ("A1", "通し"), ("A2", "通し"), ("A3", "通し"), ("A4", "通し"), ("A5", "通し")):
        t = T.get((item, stage), Tally())
        if (got(item, "OK"), got(item, "NG"), got(item, "NOWORD")) != (t.ok, t.ng, t.na):
            bad.append(item)
    return bad


def result_rows(T, c1, extra):
    rows = []

    def add(item, stage):
        t = T.get((item, stage), Tally())
        rows.append([item, stage, t.ok, t.ng, t.na, t.rate()])

    for f in ("E1", "E2", "E3"):
        add(f, "Gemini")
    for f in ("A1", "A2", "A3", "A4", "A5", "E2", "E3"):
        add(f, "システム")
    for f in ("A1", "A2", "A3", "A4", "A5"):
        add(f, "通し")
    add("A4予約", "通し")
    rows.append(["C1読み落とし", "件数", "", c1, "", "-"])
    rows.append(["余分", "件数", "", extra, "", "-"])
    return rows


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def check_out_dir(out_dir):
    real = os.path.realpath(out_dir)
    probe = real
    while not os.path.isdir(probe):
        probe = os.path.dirname(probe)
    cands = {probe, os.path.dirname(os.path.realpath(__file__))}
    for c in cands:
        r = subprocess.run(["git", "-C", c, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            top = os.path.realpath(r.stdout.strip())
            if real == top or real.startswith(top + os.sep):
                raise Stop("--out-dir がリポジトリの中です（社外秘の流出防止）")


def write_tsv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--snapshot-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--verdicts-out")
    a = ap.parse_args(argv)
    try:
        check_out_dir(a.out_dir)
        if a.verdicts_out:
            check_out_dir(os.path.dirname(os.path.abspath(a.verdicts_out)))
        gold = read_tsv(a.gold, GOLD_COLS)
        snap_by_post = {}
        files = sorted(f for f in os.listdir(a.snapshot_dir) if f.endswith(".tsv"))
        for f in files:
            rows = read_tsv(os.path.join(a.snapshot_dir, f), SNAP_COLS)
            snap_by_post[f[:-4]] = rows  # 全行を使う（is_current では絞らない）
        verdicts = [] if a.verdicts_out else None
        T, errors, c1, extra, nocur, nofile, table = score(gold, snap_by_post, verdicts)
        os.makedirs(a.out_dir, exist_ok=True)
        write_tsv(os.path.join(a.out_dir, "result.tsv"),
                  ["項目", "段", "正しい", "違う", "答え無し", "正答率"], result_rows(T, c1, extra))
        write_tsv(os.path.join(a.out_dir, "errors.tsv"),
                  ["投稿id", "price_line", "項目", "段", "正解", "システム"], errors)
        with open(os.path.join(a.out_dir, "inputs.sha256"), "w", encoding="utf-8", newline="") as f:
            ents = [(os.path.basename(a.gold), sha256_file(a.gold))]
            ents += [(f, sha256_file(os.path.join(a.snapshot_dir, f))) for f in files]
            for n, h in sorted(ents):
                f.write("%s  %s\n" % (h, n))
        if verdicts is not None:
            bad = check_verdicts(T, c1, verdicts)
            if bad:
                raise Stop("判定の数が集計と合いません " + " ".join(bad))
            os.makedirs(os.path.dirname(os.path.abspath(a.verdicts_out)), exist_ok=True)
            write_tsv(a.verdicts_out, ["key", "項目", "判定"], verdicts)
    except Stop as e:
        print("STOP: %s" % e, file=sys.stderr)
        return 2
    # 画面には件数だけ（時刻・パスは出力ファイルに入れない）
    print("写しの行が無い投稿=%d (うち写しファイル無し=%d)" % (nocur, nofile))
    print("A4読み替え表: " + " / ".join("%s=%s(%d)" % (k, v[0], v[1]) for k, v in table.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
