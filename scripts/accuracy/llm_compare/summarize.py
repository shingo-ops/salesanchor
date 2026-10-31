#!/usr/bin/env python3
"""score_v102.py の出力・使用量・時間・費用・合否を1枚の表にする（design.md §5-4、§4）。標準ライブラリのみ。

  python3 -I summarize.py --out-dir OUT \
      --score gemini1=DIR --score gemini2=DIR --score gemini3=DIR --score haiku=DIR --score sonnet=DIR \
      --gemini gemini1 --gemini gemini2 --gemini gemini3 --claude haiku --claude sonnet \
      [--usage gemini1=JSONL:1 --usage gemini2=JSONL:2 --usage haiku=JSONL ...] [--daily-n N] [--gemini-30d-cost-usd X --fx-yen Y --claude-extra-yen Z] \
      [--md5-before S --md5-after S --ledger-rows N --gemini-calls N]
  DIR は score_v102.py の --out-dir（result.tsv がある）。--out-dir は集計値だけ（社外秘の元データは入れない）。
"""
import argparse
import csv
from fractions import Fraction
import json
import os
import statistics
import subprocess
import sys

JUDGE_RATE = [("E1", "Gemini"), ("E2", "Gemini"), ("E3", "Gemini")]  # AI の答えだけで決まる率（design §4）
JUDGE_COUNT = [("C1読み落とし", "件数"), ("余分", "件数")]
REF = [("A1", "システム"), ("A2", "システム"), ("A3", "システム"), ("A4", "システム"), ("A5", "システム"),
       ("E2", "システム"), ("E3", "システム"), ("A1", "通し"), ("A2", "通し"), ("A3", "通し"),
       ("A4", "通し"), ("A5", "通し"), ("A4予約", "通し")]


class Bad(Exception):
    pass


def read_result(d):
    """result.tsv → {(項目, 段): {"ok","ng","na","rate"(float or None),"frac"(Fraction or None),"count"(int or None)}}"""
    path = os.path.join(d, "result.tsv")
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        head = next(rd)
        if head[:2] != ["項目", "段"]:
            raise Bad("result.tsv の見出しが違う: " + path)
        for r in rd:
            if len(r) < 6:
                continue
            item, stage, ok, ng, na, _rate = r[:6]
            if stage == "件数":
                out[(item, stage)] = {"count": int(ng)}
                continue
            okn, ngn = int(ok), int(ng)
            den = okn + ngn
            out[(item, stage)] = {"ok": okn, "ng": ngn, "na": int(na or 0), "rate": (100.0 * okn / den) if den else None,
                                "frac": Fraction(100 * okn, den) if den else None}
    return out


def split_spec(spec):
    """'JSONL' または 'JSONL:repeat' → (path, repeat or None)。repeat は末尾が :数字 のときだけ。"""
    head, sep, tail = spec.rpartition(":")
    if sep and tail.isdigit() and head:
        return head, int(tail)
    return spec, None


def read_usage(spec):
    """JSONL（または JSONL:repeat）→ 件数・トークン・時間。Gemini と Claude で定義が違う（design §3）。
    repeat を付けると、その repeat の行だけを数える（Gemini は repeat ごとに別の列で出す）。"""
    path, rep = split_spec(spec)
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    if rep is not None:
        rows = [r for r in rows if r.get("repeat") == rep]
    ok = [r for r in rows if not r.get("error") and r.get("response_text")]
    is_claude = bool(ok) and str(ok[0].get("config", "")).startswith("claude-")
    inp = out = think = 0
    for r in ok:
        u = r.get("usage_raw") or {}
        if is_claude:
            inp += (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
            out += u.get("output_tokens") or 0
            think += ((u.get("output_tokens_details") or {}).get("thinking_tokens")) or 0
        else:
            inp += u.get("prompt_token_count") or 0
            out += u.get("candidates_token_count") or 0
            think += u.get("thoughts_token_count") or 0
    el = [r["elapsed_sec"] for r in ok if r.get("elapsed_sec") is not None]
    res = {"calls": len(rows), "ok": len(ok), "input": inp, "output": out, "think": think,
           "elapsed_total": sum(el), "elapsed_median": statistics.median(el) if el else None,
           "elapsed_max": max(el) if el else None, "claude": is_claude}
    if is_claude:
        res["list_cost_usd"] = sum((r.get("total_cost_usd") or 0) for r in ok)
        dm = [r["duration_ms"] for r in ok if r.get("duration_ms") is not None]
        res["duration_ms_median"] = statistics.median(dm) if dm else None
    return res


def fmt(v, nd=1):
    return "-" if v is None else ("%.*f" % (nd, v) if isinstance(v, float) else str(v))


def build(results, gemini, claude, usage, opts):
    """→ (表の行のリスト, 合否の行のリスト)。行は文字列のリスト。"""
    labels = gemini + claude
    table = [["項目", "段", "判定に使う"] + labels + ["Gemini平均", "Gemini最小〜最大"]]
    gmean = {}
    for key in JUDGE_RATE + REF:
        gs = [results[g][key]["rate"] for g in gemini if key in results[g] and results[g][key].get("rate") is not None]
        fs = [results[g][key]["frac"] for g in gemini if key in results[g] and results[g][key].get("frac") is not None]
        gmean[key] = sum(fs) / len(fs) if fs else None  # 比べるのは Fraction（整数の ok/ng から作る）。float では比べない
        row = [key[0], key[1], "判定" if key in JUDGE_RATE else "参考"]
        for l in labels:
            row.append(fmt(results[l].get(key, {}).get("rate")) + "%" if results[l].get(key, {}).get("rate") is not None else "-")
        row += [fmt(float(gmean[key])) + "%" if gmean[key] is not None else "-",
                ("%.1f〜%.1f%%" % (min(gs), max(gs))) if gs else "-"]
        table.append(row)
    for key in JUDGE_COUNT:
        gs = [results[g][key]["count"] for g in gemini if key in results[g]]
        gmean[key] = Fraction(sum(gs), len(gs)) if gs else None
        table.append([key[0], "件数", "判定"] + [fmt(results[l].get(key, {}).get("count")) for l in labels]
                     + [fmt(float(gmean[key])) if gmean[key] is not None else "-", ("%d〜%d" % (min(gs), max(gs))) if gs else "-"])
    # トークン・時間（並べるだけ）
    for name, fn in (("入力トークン合計", lambda u: u["input"]), ("出力トークン合計", lambda u: u["output"]),
                     ("考えたトークン合計", lambda u: u["think"]), ("成功件数", lambda u: u["ok"]),
                     ("1件の時間 中央値(秒)", lambda u: u["elapsed_median"]), ("1件の時間 最大(秒)", lambda u: u["elapsed_max"]),
                     ("合計時間(秒)", lambda u: u["elapsed_total"]),
                     ("duration_ms 中央値(Claudeのみ)", lambda u: u.get("duration_ms_median")),
                     ("定価換算 合計USD(Claudeのみ・参考。実際の請求ではない)", lambda u: "%.4f" % u["list_cost_usd"] if "list_cost_usd" in u else None)):
        row = [name, "使用量", "参考"]
        for l in labels:
            row.append(fmt(fn(usage[l])) if l in usage else "-")
        table.append(row + ["", ""])
    # 合否
    verdict = []
    for c in claude:
        ok_rate = all(results[c].get(k, {}).get("frac") is not None and gmean[k] is not None
                      and results[c][k]["frac"] >= gmean[k] for k in JUDGE_RATE)
        ok_cnt = all(results[c].get(k, {}).get("count") is not None and gmean[k] is not None
                     and results[c][k]["count"] <= gmean[k] for k in JUDGE_COUNT)
        verdict.append([c, "正答率", "合格" if (ok_rate and ok_cnt) else "不合格",
                        "E1/E2/E3 が Gemini 平均以上、C1・余分が Gemini 平均以下"])
        u = usage.get(c)
        exp = opts.get("expected_posts", 100)
        if u is None:
            verdict.append([c, "サブスクで動く", "未確認", "使用量の JSONL なし"])
        else:
            good = u["ok"] == exp and u["calls"] == exp and not opts.get("stopped", {}).get(c)
            verdict.append([c, "サブスクで動く", "合格" if good else "不合格", "成功 %d / 対象 %d（環境変数・auth status は実施ログで確認）" % (u["ok"], exp)])
            n = opts.get("daily_n")
            if n is None:
                verdict.append([c, "回数の上限", "未確認", "N 未指定"])
            elif n > exp:
                verdict.append([c, "回数の上限", "未確定", "N=%d が %d 件を超える（追試を PO に相談）" % (n, exp)])
            else:
                hours = u["elapsed_total"] / max(u["ok"], 1) * n / 3600
                verdict.append([c, "回数の上限", "合格" if (hours <= 24 and good) else "不合格", "1日 %d 件の所要 %.1f 時間" % (n, hours)])
        g_usd, fx, extra = opts.get("gemini_30d_usd"), opts.get("fx_yen"), opts.get("claude_extra_yen")
        if None in (g_usd, fx, extra):
            verdict.append([c, "費用", "未確認", "gemini費用・為替・追加費用の指定なし"])
        else:
            limit = g_usd * fx
            verdict.append([c, "費用", "合格" if extra <= limit else "不合格",
                            "Claude追加 %.0f円 ≦ Gemini直近30日 %.0f円（為替 %s円/USD）" % (extra, limit, fx)])
    b, a = opts.get("md5_before"), opts.get("md5_after")
    lr, gc = opts.get("ledger_rows"), opts.get("gemini_calls")
    if None in (b, a, lr, gc):
        verdict.append(["全体", "本番の解析結果に書いた件数0件", "未確認", "md5・行数の指定なし"])
    else:
        verdict.append(["全体", "本番の解析結果に書いた件数0件", "合格" if (b == a and lr == gc) else "不合格",
                        "md5 %s・記録帳の行 %d / Gemini 呼び出し %d" % ("一致" if b == a else "不一致", lr, gc)])
    return table, verdict


def check_out_dir(out_dir):
    real = os.path.realpath(out_dir)
    probe = real
    while not os.path.isdir(probe):
        probe = os.path.dirname(probe)
    r = subprocess.run(["git", "-C", probe, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode == 0 and (real == os.path.realpath(r.stdout.strip()) or real.startswith(os.path.realpath(r.stdout.strip()) + os.sep)):
        raise Bad("--out-dir がリポジトリの中です（社外秘の流出防止）")


def write(out_dir, table, verdict):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "summary.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerows(table)
        w.writerow([])
        w.writerows([["対象", "基準", "判定", "根拠"]] + verdict)
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as f:
        def md(rows):
            f.write("| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]) + "\n")
            for r in rows[1:]:
                f.write("| " + " | ".join(r) + " |\n")
        md(table)
        f.write("\n")
        md([["対象", "基準", "判定", "根拠"]] + verdict)


def kv(items):
    out = {}
    for s in items or []:
        k, v = s.split("=", 1)
        out[k] = v
    return out


def usage_paths(items):
    """--usage の LABEL=JSONL[:repeat] → {LABEL: JSONL のパス（repeat 抜き）}"""
    return {k: split_spec(v)[0] for k, v in kv(items).items()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--score", action="append", required=True, help="LABEL=score_v102 の出力フォルダ")
    ap.add_argument("--gemini", action="append", required=True)
    ap.add_argument("--claude", action="append", default=[])
    ap.add_argument("--usage", action="append", help="LABEL=JSONL か LABEL=JSONL:repeat（Gemini は repeat ごと）")
    ap.add_argument("--expected-posts", type=int, default=100)
    ap.add_argument("--daily-n", type=int)
    ap.add_argument("--gemini-30d-cost-usd", type=float)
    ap.add_argument("--fx-yen", type=float)
    ap.add_argument("--claude-extra-yen", type=float)
    ap.add_argument("--md5-before")
    ap.add_argument("--md5-after")
    ap.add_argument("--ledger-rows", type=int)
    ap.add_argument("--gemini-calls", type=int)
    a = ap.parse_args(argv)
    try:
        check_out_dir(a.out_dir)
        results = {k: read_result(v) for k, v in kv(a.score).items()}
        for l in a.gemini + a.claude:
            if l not in results:
                raise Bad("--score に無い名前: " + l)
        usage = {k: read_usage(v) for k, v in kv(a.usage).items()}
        stopped = {c: os.path.exists(p + ".stop.txt") for c, p in usage_paths(a.usage).items()}
        opts = dict(expected_posts=a.expected_posts, daily_n=a.daily_n, gemini_30d_usd=a.gemini_30d_cost_usd,
                    fx_yen=a.fx_yen, claude_extra_yen=a.claude_extra_yen, md5_before=a.md5_before,
                    md5_after=a.md5_after, ledger_rows=a.ledger_rows, gemini_calls=a.gemini_calls, stopped=stopped)
        table, verdict = build(results, a.gemini, a.claude, usage, opts)
        write(a.out_dir, table, verdict)
    except Bad as e:
        print("ABORT:", e, file=sys.stderr)
        return 2
    print("wrote", os.path.join(a.out_dir, "summary.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
