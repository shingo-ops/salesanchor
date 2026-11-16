"""30周年ピカチュウ30種コンプリートセット(466062) の区分が 2026-11-11 13:38 JST に PO の画面操作で
シングル(2)→セット(4) に変わった。古い解析のまま「単品」(Single) で残る行を持つ投稿を、本番と同じ関数
line_analysis_v102_svc.run_v102_analysis でシステム段だけやり直す。Gemini は呼ばない。PO 2026-11-11「2」（241件すべて）。

対象: 466062 の行で condition_canonical='Single' を持つ投稿。ただし人の手直し(item_corrections)がある投稿・
      v102 でない投稿・done でない投稿は外して名前を出す（外したものは書かない）。
仕入元ごとに独立して扱う（現行の印の付け直しは仕入元の中だけで決まる: tcg_analyzer_svc._merge_supplier_products）。
MODE=dryrun: 仕入元ごとに、投稿の古い順に1つの取引で流す（commit は flush に差し替え）→ 比べる → ROLLBACK → 元に戻ったか確認。
             変化の全件を CHG_PATH に書く。
MODE=commit: 対象の投稿の集合が EXP_PATH と同じでなければ何も書かずに止まる。仕入元ごとに内部試走し、
             その変化が EXP_PATH の同じ仕入元の分と全件同じときだけ、実行前を SNAP_PATH(仕入元ごとに1行) に足して本番どおり実行し、
             読み戻して試走と同じか確かめる。違う仕入元は書かずに飛ばして名前を出す。
目当ての合格: 466062 の Single だった行が、466062 のまま Single でなくなる。
"""
from __future__ import annotations
import json, os, sys, time
from sqlalchemy import text
from app.services import line_analysis_v102_svc as svc
from app.tasks.tcg_extraction import _get_sync_session

MODE = os.environ.get("MODE", "")
SNAP = os.environ.get("SNAP_PATH", "/m/before_snapshot.jsonl")
EXP_PATH = os.environ.get("EXP_PATH", "/m/expected.json")
CHG_PATH = os.environ.get("CHG_PATH", "/m/changes.json")
PID = 466062
SET_CATEGORY = 4
DISCOVER = """
SELECT ej.id::text AS job, sm.supplier_channel_id::text AS ch, sm.received_at, ej.prompt_version, ej.status,
       (SELECT count(*) FROM public.item_corrections ic JOIN public.extraction_items e2 ON e2.id = ic.extraction_item_id
         WHERE e2.extraction_job_id = ej.id) AS corr
FROM public.extraction_jobs ej JOIN public.source_messages sm ON sm.id = ej.source_message_id
WHERE ej.id IN (SELECT ei.extraction_job_id FROM public.analysis_results ar JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
                WHERE ar.product_id = :pid AND ar.condition_canonical = 'Single')
ORDER BY sm.received_at, ej.id
"""
ROWS = """
SELECT ei.id::text AS item_id, ei.gemini_index, ar.id::text AS result_id, ar.product_id, ar.pid_resolved, ar.unit_id, ar.unit_canonical,
       ar.unit_resolved, ar.condition_id, ar.condition_canonical, ar.condition_basis, ar.quantity_normalized::text AS q,
       ar.price_normalized::text AS p, ar.status, ar.exclusion, ar.needs_review, ar.review_reasons, ar.is_current, ar.work_id,
       ar.price_basis, ar.ship_ja, ar.ship_en
FROM public.extraction_items ei LEFT JOIN public.analysis_results ar ON ar.extraction_item_id = ei.id
WHERE ei.extraction_job_id = CAST(:ej AS uuid) ORDER BY ei.gemini_index NULLS LAST, ei.id, ar.id
"""
STRICT = ("product_id", "pid_resolved", "unit_id", "unit_canonical", "unit_resolved", "condition_id", "condition_canonical",
          "condition_basis", "q", "p", "status", "exclusion", "needs_review", "review_reasons", "work_id", "price_basis", "ship_ja", "ship_en")
CUR = """
SELECT ar.id::text AS result_id, ar.product_id, ar.condition_id, ar.is_current
FROM public.analysis_results ar JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id JOIN public.source_messages sm ON sm.id = ej.source_message_id
WHERE sm.supplier_channel_id = CAST(:ch AS uuid) AND NOT (ej.id::text = ANY(:jobs)) ORDER BY ar.id
"""
COMMITTED = []

def say(t, m=""): print(f"{t} {m}".rstrip(), flush=True)
def q(s, sql, **p): return [dict(r._mapping) for r in s.execute(text(sql), p).fetchall()]
def stop(m):
    say("STOP", m)
    say("RESULT", f"MODE={MODE} 不合格 (STOP)。何も書いていません" if not COMMITTED else f"MODE={MODE} 途中で止まった（書いた投稿 {len(COMMITTED)} 件・要確認）")
    sys.exit(2)
def norm(x): return json.loads(json.dumps(x, ensure_ascii=False, default=str, sort_keys=True))

def discover(s):
    rows = q(s, DISCOVER, pid=PID); s.rollback()
    keep, skipped = [], []
    for r in rows:
        why = []
        if r["corr"]: why.append(f"人の手直し {r['corr']} 件")
        if not svc.is_v102_prompt_version(r["prompt_version"]): why.append("v102 でない")
        if r["status"] != "done": why.append(f"status={r['status']}")
        (skipped if why else keep).append((r, why))
    for r, why in skipped: say("[EXCLUDE]", f"{r['job'][:8]} 仕入元 {r['ch'][:8]} {r['received_at']} 理由: {', '.join(why)}")
    plan = {}
    for r, _ in keep: plan.setdefault(r["ch"], []).append(r["job"])
    return plan, [r["job"] for r, _ in skipped]

def state(s, jobs, ch):
    return {"rows": {ej: q(s, ROWS, ej=ej) for ej in jobs},
            "job": {ej: q(s, "SELECT review_reasons, system_review_detail::text AS d FROM public.extraction_jobs WHERE id=CAST(:ej AS uuid)", ej=ej)[0] for ej in jobs},
            "cur": q(s, CUR, ch=ch, jobs=jobs)}

def check_rows(ej, rows):
    if any(r["result_id"] is None for r in rows): return f"{ej[:8]} に解析結果の無い行がある"
    ids = [r["item_id"] for r in rows]
    if len(ids) != len(set(ids)): return f"{ej[:8]} に解析結果が2つ以上ある行がある"
    return None

def changes(before, after, ej):
    bf = {r["item_id"]: r for r in before["rows"][ej]}; af = {r["item_id"]: r for r in after["rows"][ej]}
    rows = {i: {f: [str(bf[i][f]), str(af[i][f])] for f in STRICT if bf[i][f] != af[i][f]} for i in bf if i in af}
    rows = {i: d for i, d in rows.items() if d}
    cur_in = {i: [bf[i]["is_current"], af[i]["is_current"]] for i in bf if i in af and bf[i]["is_current"] != af[i]["is_current"]}
    job = None if before["job"][ej] == after["job"][ej] else {"before": before["job"][ej], "after": after["job"][ej]}
    return {"rows": rows, "cur_in": cur_in, "job": job, "same_items": set(bf) == set(af)}

def judge_channel(ch, jobs, before, after, tally):
    ok_all = True; out = {"jobs": {}, "cur_other": {}}
    for ej in jobs:
        c = changes(before, after, ej)
        if not c.pop("same_items"): say("[NG]", f"{ej[:8]} 行の集合が違う"); ok_all = False
        targets = [r for r in before["rows"][ej] if r["product_id"] == PID and r["condition_canonical"] == "Single"]
        af = {r["item_id"]: r for r in after["rows"][ej]}
        for t in targets:
            a = af.get(t["item_id"])
            good = a is not None and a["product_id"] == PID and a["condition_canonical"] != "Single"
            key = f"{a['product_id'] if a else None}/{a['unit_canonical'] if a else None}/{a['condition_canonical'] if a else None}" if a else "行が無い"
            tally[("OK" if good else "NG", key)] = tally.get(("OK" if good else "NG", key), 0) + 1
            say("[TARGET-OK]" if good else "[TARGET-NG]", f"{ej[:8]} 行 {t['item_id'][:8]} 前 {t['unit_canonical']}/{t['condition_canonical']}/{t['condition_basis']} cur={t['is_current']} → 後 {key}/{a['condition_basis'] if a else None} cur={a['is_current'] if a else None} p={t['p']} q={t['q']}")
        tids = {t["item_id"] for t in targets}
        for i, dd in c["rows"].items():
            if i not in tids: say("[OTHER]", f"{ej[:8]} 行 {i[:8]} " + json.dumps(dd, ensure_ascii=False)[:600])
        for k, v in c["cur_in"].items():
            if k not in tids: say("[OTHER-CUR]", f"{ej[:8]} 行 {k[:8]} is_current {v}")
        if svc.REASON_EXTRACT_EXCEPTION in str(after["job"][ej].get("review_reasons") or "").split(svc.REASON_SEPARATOR):
            ok_all = False; say("[NG]", f"{ej[:8]} extract_exception が付いた")
        if c["job"]: say("[JOB-CHG]", f"{ej[:8]} " + json.dumps(c["job"], ensure_ascii=False, default=str)[:1500])
        out["jobs"][ej] = c
    ob = {r["result_id"]: r["is_current"] for r in before["cur"]}
    out["cur_other"] = {r["result_id"]: [ob.get(r["result_id"]), r["is_current"]] for r in after["cur"] if ob.get(r["result_id"]) != r["is_current"]}
    for k, v in out["cur_other"].items(): say("[CUR-OTHER-JOB]", f"仕入元 {ch[:8]} の対象外の投稿の行 {k[:8]} is_current {v}")
    n_oth = sum(len(c["rows"]) for c in out["jobs"].values())
    say("[SUM-CH]", f"仕入元 {ch[:8]} 投稿 {len(jobs)} 件 変化した行={n_oth}（目当て含む） 投稿内の現行の変化={sum(len(c['cur_in']) for c in out['jobs'].values())} 対象外の投稿の現行の変化={len(out['cur_other'])} 投稿の印の変化={sum(1 for c in out['jobs'].values() if c['job'])}")
    return ok_all, out

def trial(s, ch, jobs):
    """仕入元1つ分を1つの取引で試走し、元に戻ったか確かめる。"""
    before = state(s, jobs, ch); s.rollback()
    for ej in jobs:
        err = check_rows(ej, before["rows"][ej])
        if err: return None, None, err
    real_commit = s.commit
    s.commit = s.flush
    try:
        for ej in jobs:
            t0 = time.time()
            stats = svc.run_v102_analysis(s, ej)
            say("[run]", f"{ej[:8]} 試走 {time.time()-t0:.1f}s stats={stats}")
        after = state(s, jobs, ch)
    finally:
        s.rollback(); s.commit = real_commit
    back = state(s, jobs, ch); s.rollback()
    if back != before: return None, None, f"仕入元 {ch[:8]} rollback 後に実行前と違う（試走の間にほかの書き込みがあった可能性）"
    say("[OK]", f"仕入元 {ch[:8]} rollback 確認: 実行前と同じ=True")
    return before, after, None

def main():
    if MODE not in ("dryrun", "commit"): stop("MODE は dryrun/commit")
    s = _get_sync_session()
    try:
        p = q(s, "SELECT id, name, is_active, product_category_id FROM public.products WHERE id=:i", i=PID)
        say("[PRE]", f"商品 {p}")
        if len(p) != 1 or p[0]["is_active"] is not True or p[0]["product_category_id"] != SET_CATEGORY: stop("466062 が無い・止まっている・区分がセット(4)でない")
        s.rollback()
        plan, skipped = discover(s)
        n_jobs = sum(len(v) for v in plan.values())
        say("[PLAN]", f"仕入元 {len(plan)} 件 投稿 {n_jobs} 件 外した投稿 {len(skipped)} 件")
        exp = None
        if MODE == "commit":
            try:
                exp = json.load(open(EXP_PATH))
            except Exception as e:
                stop(f"確かめ済みの変化 {EXP_PATH} が読めない: {e}")
            if exp.get("plan") != norm(plan) or exp.get("skipped") != norm(skipped):
                stop("対象の投稿の集合が、確かめ済み（expected.json）と違う。dryrun からやり直す")
            say("[OK-PLAN]", "対象の投稿の集合は確かめ済みと同じ")
        tally = {}; allch = {}; all_ok = True; skipped_ch = []; n_written = 0
        for ch, jobs in plan.items():
            say("[CH]", f"仕入元 {ch[:8]} 投稿 {len(jobs)} 件")
            before, after, err = trial(s, ch, jobs)
            if err:
                say("[NG]", err); all_ok = False; skipped_ch.append(ch); continue
            ok, out = judge_channel(ch, jobs, before, after, tally)
            nout = norm(out); allch[ch] = nout
            all_ok = all_ok and ok
            if MODE == "dryrun": continue
            if not ok or nout != exp["changes"].get(ch):
                say("[SKIP]", f"仕入元 {ch[:8]} の試走の変化が確かめ済みと違う（または不合格）。書かずに飛ばす"); skipped_ch.append(ch); continue
            with open(SNAP, "a") as f: f.write(json.dumps({"ch": ch, "before": before}, ensure_ascii=False, default=str) + "\n")
            for ej in jobs:
                stats = svc.run_v102_analysis(s, ej)
                COMMITTED.append(ej); n_written += 1
                say("[run]", f"{ej[:8]} 本実行 stats={stats}")
                s.rollback()
            final = state(s, jobs, ch); s.rollback()
            pick = lambda st: {ej: [{k: r[k] for k in ("item_id", "is_current") + STRICT} for r in st["rows"][ej]] for ej in jobs}
            same = pick(final) == pick(after)
            _ok, fout = judge_channel(ch, jobs, before, final, {})
            fsame = norm(fout) == nout
            say("[OK-WRITE]" if same and fsame else "[NG-WRITE]", f"仕入元 {ch[:8]} 読み戻し: 試走と同じ={same} 変化が試走と同じ={fsame}")
            if not (same and fsame): all_ok = False
        for (k, key), n in sorted(tally.items(), key=lambda x: -x[1]): say("[TALLY]", f"{k} {key} {n} 行")
        say("[COUNT]", f"仕入元 {len(plan)} 件中 飛ばした {len(skipped_ch)} 件 {[c[:8] for c in skipped_ch]}")
        if MODE == "dryrun":
            with open(CHG_PATH, "w") as f:
                json.dump({"plan": norm(plan), "skipped": norm(skipped), "changes": allch}, f, ensure_ascii=False, sort_keys=True, indent=1)
            say("[changes]", f"変化の全件を保存 {CHG_PATH}")
            say("RESULT", "MODE=dryrun 合格（書き込みなし）" if all_ok and not skipped_ch else "MODE=dryrun 不合格あり（書き込みなし）")
            return 0
        say("RESULT", f"MODE=commit 書いた投稿 {n_written}/{n_jobs} 件 {'合格' if all_ok and not skipped_ch else '要確認あり'}")
        return 0
    finally:
        s.close()

if __name__ == "__main__":
    sys.exit(main())
