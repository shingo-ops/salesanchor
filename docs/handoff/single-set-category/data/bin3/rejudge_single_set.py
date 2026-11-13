"""13 商品をシングルセット系（区分 15）へ付け替えた後、その商品の行を持つ投稿を、本番と同じ関数
line_analysis_v102_svc.run_v102_analysis でシステム段だけ解析し直す。Gemini は呼ばない。PO 2026-11-13「1」。

対象: 13 商品（PIDS）のどれかの行を持つ投稿（置き換え済みの行も含める）。ただし人の手直し(item_corrections)がある投稿・
      v102 でない投稿・done でない投稿は外して名前を出す（外したものは書かない）。
仕入元ごとに独立して扱う（現行の印の付け直しは仕入元の中だけで決まる: tcg_analyzer_svc._merge_supplier_products）。
投稿は line_posted_at（無ければ received_at）の古い順に流す（〆の参照と価格の引き継ぎが前の投稿の行を読むため）。
MODE=dryrun: 仕入元ごとに、投稿の古い順に1つの取引で流す（commit は flush に差し替え）→ 比べる → ROLLBACK → 元に戻ったか確認。
             変化の全件を CHG_PATH に、外した投稿の一覧を EXCL_PATH に書く。
MODE=commit: 対象の投稿の集合が EXP_PATH と同じでなければ何も書かずに止まる。仕入元ごとに内部試走し、
             その変化が EXP_PATH の同じ仕入元の分と全件同じときだけ、実行前を SNAP_PATH(仕入元ごとに1行) に足して本番どおり実行し、
             読み戻して試走と同じか確かめる。違う仕入元は書かずに飛ばして名前を出す。
目当ての合格: 商品はそのまま・単位 Set・状態の群 single・bundle_size なし。
"""
from __future__ import annotations
import json, os, sys, time
from sqlalchemy import text
from app.services import line_analysis_v102_svc as svc
from app.services import gemini_raw_copy_v102_soldout_ref as soldout_ref
from app.tasks.tcg_extraction import _get_sync_session

MODE = os.environ.get("MODE", "")
SNAP = os.environ.get("SNAP_PATH", "/m/before_snapshot.jsonl")
EXP_PATH = os.environ.get("EXP_PATH", "/m/expected.json")
CHG_PATH = os.environ.get("CHG_PATH", "/m/changes.json")
PIDS = (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
SINGLE_SET_CATEGORY = 15  # PC_SINGLE_SET（便2 で本番に入れた区分）
SOLDOUT_BASES = (svc.CONDITION_BASIS_SOLDOUT_REF, soldout_ref.CONDITION_BASIS_SOLDOUT_INHERIT)  # 〆が前の行の状態を写した印（design.md §2 KGI 1）
EXCL_PATH = os.environ.get("EXCL_PATH", "/m/excluded.json")
LOCK_TIMEOUT = "1s"  # ADR-1037。PO の台本が PGOPTIONS で付ける。付いていなければ止まる
IN_FLIGHT = None
DISCOVER = """
SELECT ej.id::text AS job, sm.supplier_channel_id::text AS ch, sm.received_at, sm.line_posted_at, ej.prompt_version, ej.status,
       (SELECT count(*) FROM public.item_corrections ic JOIN public.extraction_items e2 ON e2.id = ic.extraction_item_id
         WHERE e2.extraction_job_id = ej.id) AS corr,
       (SELECT count(*) FROM public.analysis_results ar3 JOIN public.extraction_items e3 ON e3.id = ar3.extraction_item_id
         WHERE e3.extraction_job_id = ej.id AND ar3.product_id = ANY(:pids) AND ar3.is_current) AS cur_rows
FROM public.extraction_jobs ej JOIN public.source_messages sm ON sm.id = ej.source_message_id
WHERE ej.id IN (SELECT ei.extraction_job_id FROM public.analysis_results ar JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
                WHERE ar.product_id = ANY(:pids))
ORDER BY COALESCE(sm.line_posted_at, sm.received_at), sm.received_at, ej.id
"""
ROWS = """
SELECT ei.id::text AS item_id, ei.gemini_index, ar.id::text AS result_id, ar.product_id, ar.pid_resolved, ar.unit_id, ar.unit_canonical,
       ar.unit_resolved, ar.condition_id, ar.condition_canonical, ar.condition_basis, ar.quantity_normalized::text AS q,
       ar.price_normalized::text AS p, ar.status, ar.exclusion, ar.needs_review, ar.review_reasons, ar.is_current, ar.work_id,
       ar.price_basis, ar.ship_ja, ar.ship_en, ar.bundle_size::text AS bundle_size, lc.value_group
FROM public.extraction_items ei LEFT JOIN public.analysis_results ar ON ar.extraction_item_id = ei.id
LEFT JOIN public.line_conditions lc ON lc.id = ar.condition_id
WHERE ei.extraction_job_id = CAST(:ej AS uuid) ORDER BY ei.gemini_index NULLS LAST, ei.id, ar.id
"""
STRICT = ("product_id", "pid_resolved", "unit_id", "unit_canonical", "unit_resolved", "condition_id", "condition_canonical",
          "condition_basis", "q", "p", "status", "exclusion", "needs_review", "review_reasons", "work_id", "price_basis", "ship_ja", "ship_en",
          "bundle_size")
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
    if not COMMITTED and IN_FLIGHT is None:
        say("RESULT", f"MODE={MODE} 不合格 (STOP)。何も書いていません")
    else:
        extra = f"。書いたかもしれない投稿 1 件: {IN_FLIGHT}" if IN_FLIGHT is not None else ""
        say("RESULT", f"MODE={MODE} 途中で止まった（書き終えた投稿 {len(COMMITTED)} 件{extra}・要確認）")
    sys.exit(2)
def norm(x): return json.loads(json.dumps(x, ensure_ascii=False, default=str, sort_keys=True))

def exclusion_reasons(r):
    why = []
    if r["corr"]: why.append(f"人の手直し {r['corr']} 件")
    if not svc.is_v102_prompt_version(r["prompt_version"]): why.append("v102 でない")
    if r["status"] != "done": why.append(f"status={r['status']}")
    return why

def classify_target(t, a):
    """t=前の行・a=後の行（無ければ None）。戻り値 (判定, 後の形)。判定は OK / NG / SOLDOUT。
    単位と bundle_size は SOLDOUT でも見る（KGI 2 は〆の行を外さない）。状態の群だけ SOLDOUT を別にする（KGI 1）。"""
    if a is None:
        return "NG", "行が無い"
    key = f"{a['product_id']}/{a['unit_canonical']}/{a['condition_canonical']}/{a['value_group']}/bundle={a['bundle_size']}/cur={a['is_current']}"
    if a["product_id"] not in PIDS:
        return "NG", key
    if t["product_id"] in PIDS and a["product_id"] != t["product_id"]:
        return "NG", key
    if a["unit_canonical"] != "Set" or a["bundle_size"] is not None:
        return "NG", key
    if a["value_group"] == "single":
        return "OK", key
    if a["condition_basis"] in SOLDOUT_BASES:
        return "SOLDOUT", key
    return "NG", key

def job_reasons(s, ej):
    r = q(s, "SELECT review_reasons FROM public.extraction_jobs WHERE id=CAST(:ej AS uuid)", ej=ej)
    return str(r[0]["review_reasons"] or "").split(svc.REASON_SEPARATOR) if r else []

def discover(s):
    rows = q(s, DISCOVER, pids=list(PIDS)); s.rollback()
    say("[PRE]", f"line_posted_at が空の投稿 {sum(1 for r in rows if r['line_posted_at'] is None)} 件")
    keep, skipped = [], []
    for r in rows:
        why = exclusion_reasons(r)
        if why:
            skipped.append({"job": r["job"], "ch": r["ch"], "received_at": str(r["received_at"]), "cur_rows": r["cur_rows"], "why": why})
        else:
            keep.append(r)
    for x in skipped: say("[EXCLUDE]", f"{x['job'][:8]} 仕入元 {x['ch'][:8]} {x['received_at']} 現行の行 {x['cur_rows']} 理由: {', '.join(x['why'])}")
    plan = {}
    for r in keep: plan.setdefault(r["ch"], []).append(r["job"])
    return plan, skipped

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

def judge_channel(ch, jobs, before, after, tally, secs=None):
    ok_all = True; out = {"jobs": {}, "cur_other": {}}
    for ej in jobs:
        c = changes(before, after, ej)
        if not c.pop("same_items"): say("[NG]", f"{ej[:8]} 行の集合が違う"); ok_all = False
        af = {r["item_id"]: r for r in after["rows"][ej]}
        targets = [r for r in before["rows"][ej] if r["product_id"] in PIDS or (af.get(r["item_id"]) or {}).get("product_id") in PIDS]
        tlist = []
        for t in targets:
            a = af.get(t["item_id"])
            label, key = classify_target(t, a)
            tally[(label, key)] = tally.get((label, key), 0) + 1
            shape = {f: t[f] for f in ("unit_canonical", "condition_canonical", "value_group", "bundle_size", "condition_basis", "is_current")}
            say(f"[TARGET-{label}]", f"{ej[:8]} 行 {t['item_id'][:8]} 前 {json.dumps(shape, ensure_ascii=False, default=str)} → 後 {key}/{a['condition_basis'] if a else None} p={t['p']} q={t['q']}")
            tlist.append({"item": t["item_id"], "before": shape, "after": key, "label": label})
        c["targets"] = tlist
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
    tail = f" {secs:.1f}秒" if secs is not None else ""
    say("[SUM-CH]", f"仕入元 {ch[:8]} 投稿 {len(jobs)} 件 変化した行={n_oth}（目当て含む） 投稿内の現行の変化={sum(len(c['cur_in']) for c in out['jobs'].values())} 対象外の投稿の現行の変化={len(out['cur_other'])} 投稿の印の変化={sum(1 for c in out['jobs'].values() if c['job'])}{tail}")
    return ok_all, out

def trial(s, ch, jobs):
    """仕入元1つ分を1つの取引で試走し、元に戻ったか確かめる。"""
    before = state(s, jobs, ch); s.rollback()
    for ej in jobs:
        err = check_rows(ej, before["rows"][ej])
        if err: return None, None, err
    real_commit = s.commit
    s.commit = s.flush
    broke = None
    after = None
    try:
        for ej in jobs:
            t0 = time.time()
            stats = svc.run_v102_analysis(s, ej)
            say("[run]", f"{ej[:8]} 試走 {time.time()-t0:.1f}s stats={stats}")
            if svc.REASON_EXTRACT_EXCEPTION in job_reasons(s, ej):
                broke = ej
                break
        if broke is None:
            after = state(s, jobs, ch)
    finally:
        s.rollback(); s.commit = real_commit
    back = state(s, jobs, ch); s.rollback()
    if back != before: return None, None, f"仕入元 {ch[:8]} rollback 後に実行前と違う（試走の間にほかの書き込みがあった可能性）"
    if broke is not None: return None, None, f"仕入元 {ch[:8]} の投稿 {broke[:8]} で extract_exception が付いた"
    say("[OK]", f"仕入元 {ch[:8]} rollback 確認: 実行前と同じ=True")
    return before, after, None

def main():
    global IN_FLIGHT
    if MODE not in ("dryrun", "commit"): stop("MODE は dryrun/commit")
    s = _get_sync_session()
    try:
        lt = q(s, "SHOW lock_timeout")[0]["lock_timeout"]
        say("[PRE]", f"lock_timeout={lt}")
        s.rollback()
        if lt != LOCK_TIMEOUT: stop("lock_timeout が 1s でない（PGOPTIONS が付いていない）")
        p = q(s, "SELECT id, is_active, product_category_id FROM public.products WHERE id = ANY(:pids) ORDER BY id", pids=list(PIDS))
        say("[PRE]", f"商品 {p}")
        if len(p) != 13 or any(r["is_active"] is not True or r["product_category_id"] != SINGLE_SET_CATEGORY for r in p):
            stop("13 商品のどれかが無い・止まっている・区分がシングルセット系(15)でない")
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
            try:
                t0 = time.monotonic()
                before, after, err = trial(s, ch, jobs)
                secs = time.monotonic() - t0
                if err:
                    say("[NG]", err); all_ok = False; skipped_ch.append(ch); continue
                ok, out = judge_channel(ch, jobs, before, after, tally, secs=secs)
                nout = norm(out); allch[ch] = nout
                all_ok = all_ok and ok
                if MODE == "dryrun": continue
                if not ok or nout != exp["changes"].get(ch):
                    say("[SKIP]", f"仕入元 {ch[:8]} の試走の変化が確かめ済みと違う（または不合格）。書かずに飛ばす"); skipped_ch.append(ch); continue
                with open(SNAP, "a") as f: f.write(json.dumps({"ch": ch, "before": before}, ensure_ascii=False, default=str) + "\n")
                for ej in jobs:
                    IN_FLIGHT = ej
                    stats = svc.run_v102_analysis(s, ej)
                    reasons = job_reasons(s, ej)
                    s.rollback()
                    if svc.REASON_EXTRACT_EXCEPTION in reasons:
                        stop(f"仕入元 {ch[:8]} の投稿 {IN_FLIGHT} で extract_exception が付いた。この投稿は本番に review_reasons=extract_exception・system_review_detail=NULL が入った。戻す材料は SNAP_PATH のこの仕入元の before")
                    COMMITTED.append(ej); n_written += 1
                    IN_FLIGHT = None
                    say("[run]", f"{ej[:8]} 本実行 stats={stats}")
                final = state(s, jobs, ch); s.rollback()
                pick = lambda st: {ej: [{k: r[k] for k in ("item_id", "is_current") + STRICT} for r in st["rows"][ej]] for ej in jobs}
                same = pick(final) == pick(after)
                _ok, fout = judge_channel(ch, jobs, before, final, {})
                fsame = norm(fout) == nout
                say("[OK-WRITE]" if same and fsame else "[NG-WRITE]", f"仕入元 {ch[:8]} 読み戻し: 試走と同じ={same} 変化が試走と同じ={fsame}")
                if not (same and fsame): stop(f"仕入元 {ch[:8]} の読み戻しが試走と違う。ここで止めた")
            except Exception as e:
                s.rollback()
                if MODE == "dryrun":
                    say("[NG]", f"仕入元 {ch[:8]} 例外 {type(e).__name__}: {str(e)[:300]}"); all_ok = False; skipped_ch.append(ch); continue
                head = f"仕入元 {ch[:8]} 例外 {type(e).__name__}: {str(e)[:300]}。"
                k = sum(1 for ej in jobs if ej in COMMITTED)
                if IN_FLIGHT is not None:
                    stop(head + f"途中の投稿 {IN_FLIGHT} は、review_reasons と system_review_detail だけでなく結果の行まで本番に書かれた可能性がある。戻す材料は SNAP_PATH のこの仕入元の before")
                elif k == 0:
                    stop(head + "この仕入元は本番には書いていない")
                else:
                    stop(head + f"この仕入元は {k} 件書き終えた後、読み戻し・比べる段で止まった。戻す材料は SNAP_PATH のこの仕入元の before")
        for (k, key), n in sorted(tally.items(), key=lambda x: -x[1]): say("[TALLY]", f"{k} {key} {n} 行")
        say("[COUNT]", f"仕入元 {len(plan)} 件中 飛ばした {len(skipped_ch)} 件 {[c[:8] for c in skipped_ch]}")
        if MODE == "dryrun":
            with open(CHG_PATH, "w") as f:
                json.dump({"plan": norm(plan), "skipped": norm(skipped), "changes": allch}, f, ensure_ascii=False, sort_keys=True, indent=1)
            say("[changes]", f"変化の全件を保存 {CHG_PATH}")
            with open(EXCL_PATH, "w") as f:
                json.dump(norm(skipped), f, ensure_ascii=False, sort_keys=True, indent=1)
            say("[excluded]", f"外した投稿 {len(skipped)} 件を保存 {EXCL_PATH}")
            say("RESULT", "MODE=dryrun 合格（書き込みなし）" if all_ok and not skipped_ch else "MODE=dryrun 不合格あり（書き込みなし）")
            return 0
        say("RESULT", f"MODE=commit 書いた投稿 {n_written}/{n_jobs} 件 {'合格' if all_ok and not skipped_ch else '要確認あり'}")
        return 0
    finally:
        s.close()

if __name__ == "__main__":
    sys.exit(main())
