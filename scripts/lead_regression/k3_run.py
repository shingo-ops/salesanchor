#!/usr/bin/env python3
"""本番の外の確かめ K3a〜K3c と、K3d の比べる側の値（card-a-backend.md §6）。

    python3 -I scripts/lead_regression/k3_run.py --out-dir "$SCRATCH/k3"

- 種は 1〜200 に固定（合格するまで変えない）。base_date は 2026-11-01。
- K3c の並べ替えは、種 s のデータの成約の印を random.Random(1000000 + s) で shuffle する。
- 本番の DB には繋がない。
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT / "backend"))

import generate as gen  # noqa: E402

from app.services import lead_conversion_factors as lcf  # noqa: E402

SEEDS = range(1, 201)
BASE_DATE = dt.date(2026, 11, 1)
PROD_SEED = 20261101

K3A_RANGE = (180, 198)
K3B_RANGE = (0.90, 1.11)
K3C_MIN = 180


def run(out_dir: Path) -> dict:
    keys = lcf.ITEM_KEYS
    cover = {k: 0 for k in keys}  # K3a: 幅が仕込んだ値を含む回数
    log_est = {k: 0.0 for k in keys}  # K3b: 対数の合計（計算できた回だけ）
    n_est = {k: 0 for k in keys}
    not_comp_a = 0
    signif = {k: 0 for k in keys}
    perm_hit = {k: 0 for k in keys}  # K3c: 幅が 1 を含む回数（計算できない回は外れ＝数えない）
    not_comp_c = 0
    redraws: list[int] = []

    for s in SEEDS:
        ds = gen.generate(s, BASE_DATE)
        redraws.append(ds.redraws)
        res = lcf.analyze(ds.leads, ds.messages)
        if res.status != "ok":
            not_comp_a += 1
        else:
            for item in res.items:
                k = item["key"]
                planted = gen.PLANTED_ODDS[k]
                if item["ci_low"] <= planted <= item["ci_high"]:
                    cover[k] += 1
                log_est[k] += math.log(item["odds_ratio"])
                n_est[k] += 1
                if item["significant"]:
                    signif[k] += 1

        # K3c: 成約の印だけを並べ替える（項目・メッセージはそのまま）
        statuses = [lead.status for lead in ds.leads]
        random.Random(1000000 + s).shuffle(statuses)
        shuffled = [dataclasses.replace(lead, status=st) for lead, st in zip(ds.leads, statuses)]
        res_c = lcf.analyze(shuffled, ds.messages)
        if res_c.status != "ok":
            not_comp_c += 1
        else:
            for item in res_c.items:
                if item["ci_low"] <= 1.0 <= item["ci_high"]:
                    perm_hit[item["key"]] += 1

    rows = []
    for k in keys:
        planted = gen.PLANTED_ODDS[k]
        geo = math.exp(log_est[k] / n_est[k]) if n_est[k] else float("nan")
        ratio = geo / planted
        rows.append(
            {
                "key": k,
                "planted": planted,
                "k3a_cover": cover[k],
                "k3a_ok": K3A_RANGE[0] <= cover[k] <= K3A_RANGE[1],
                "k3b_ratio": ratio,
                "k3b_ok": K3B_RANGE[0] <= ratio <= K3B_RANGE[1],
                "k3c_include_one": perm_hit[k],
                "k3c_ok": perm_hit[k] >= K3C_MIN,
                "significant_count": signif[k],
            }
        )

    # K3d の比べる側（本番の値の Dataset）
    ds = gen.generate(PROD_SEED, BASE_DATE)
    res_d = lcf.analyze(ds.leads, ds.messages)
    k3d = []
    if res_d.fit is not None and res_d.fit.computable:
        for idx, item in enumerate(res_d.items, start=1):
            k3d.append(
                {
                    "key": item["key"],
                    "beta": res_d.fit.beta[idx],
                    "se": res_d.fit.se[idx],
                    "odds_ratio": item["odds_ratio"],
                    "ci_low": item["ci_low"],
                    "ci_high": item["ci_high"],
                }
            )

    summary = {
        "seeds": [SEEDS.start, SEEDS.stop - 1],
        "not_computable_k3a_runs": not_comp_a,
        "not_computable_k3c_runs": not_comp_c,
        "redraws_mean": sum(redraws) / len(redraws),
        "redraws_max": max(redraws),
        "items": rows,
        "k3d_status": res_d.status,
        "k3d_redraws": ds.redraws,
        "k3d_counts": [res_d.included_count, res_d.won_count, res_d.lost_count],
        "k3d": k3d,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "k3_results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"seeds {SEEDS.start}-{SEEDS.stop - 1} base_date {BASE_DATE}",
        f"not_computable: K3a runs={not_comp_a} K3c runs={not_comp_c}",
        f"redraws: mean={summary['redraws_mean']:.2f} max={summary['redraws_max']}",
        "key                      K3a(180-198)  K3b(0.90-1.11)  K3c(>=180)  signif",
    ]
    for r in rows:
        lines.append(
            f"{r['key']:<24} {r['k3a_cover']:>4} {'OK' if r['k3a_ok'] else 'NG':<2}   "
            f"{r['k3b_ratio']:.4f} {'OK' if r['k3b_ok'] else 'NG':<2}     "
            f"{r['k3c_include_one']:>4} {'OK' if r['k3c_ok'] else 'NG':<2}   {r['significant_count']:>4}"
        )
    lines.append(
        f"K3a={'OK' if all(r['k3a_ok'] for r in rows) else 'NG'} "
        f"K3b={'OK' if all(r['k3b_ok'] for r in rows) else 'NG'} "
        f"K3c={'OK' if all(r['k3c_ok'] for r in rows) else 'NG'}"
    )
    lines.append(f"K3d seed={PROD_SEED} status={res_d.status} counts(incl,won,lost)={summary['k3d_counts']} redraws={ds.redraws}")
    for r in k3d:
        lines.append(
            f"K3d {r['key']:<24} beta={r['beta']:.6f} se={r['se']:.6f} "
            f"or={r['odds_ratio']:.6f} ci=[{r['ci_low']:.6f}, {r['ci_high']:.6f}]"
        )
    text = "\n".join(lines) + "\n"
    (out_dir / "k3_summary.txt").write_text(text, encoding="utf-8")
    print(text)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir).resolve()
    try:
        out.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        print(f"STOP: 出力先がリポジトリの中です: {out}", file=sys.stderr)
        return 2
    run(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
