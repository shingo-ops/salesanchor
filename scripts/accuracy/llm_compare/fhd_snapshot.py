#!/usr/bin/env python3
"""f_hd 試験の「変換器」と「写しとの照合」。VPS の celery-worker の中で読み取り専用で動かす。

使い方（中身を stdin から渡す。-w /app で app が読める）:
  docker exec -i -w /app astro-webapp-celery-worker-1 python - check  JOBS_FILE   < fhd_snapshot.py
  docker exec -i -w /app astro-webapp-celery-worker-1 python - convert JSONL...    < fhd_snapshot.py  > snap.tsv

check  : 本番の写し(v102-f_ct)の元になった応答 → 本番の再判定と同じ組み立て(rejudge) → 本番の写しと比べる。
         差が出た件に「後から掛かる処理の印」を付ける。印の無い差が1件でもあれば「進まない」と出す。
convert: prompt_ab の JSONL の Gemini 応答(response_text) → check と同じ rejudge で判定し直し → SNAP_COLS（14列）で標準出力へ（先頭に tag,repeat,source_message の3列）。
         f_ct 2回・f_hd 2回の4組を同じ1回の READ ONLY 取引で判定し直す。prompt_ab が JSONL に書いた v102_items は判定に使わない（件数の参考だけ stderr）。
JSONL に response_text が残ること: origin/main(5cb04e08) backend/app/tools/prompt_ab.py:550-551（_append_jsonl の row に "response_text"）。

【rejudge = 本番の再判定と同じ組み立て】 origin/main backend/app/services/line_analysis_v102_svc.py（5cb04e08）
  run_v102_analysis :1486 の本体（:1491-1495 の読み込み〜）:
    :1514 masters, unit_ids = load_v102_masters(session)
    :1519 decisions = load_v102_decisions(session, [str(r.id) for r in rows])
    :1520 fixed_products = _fixed_products(response_text, ctx, masters, rows, decisions)   （_fixed_products 定義 :1180）
    :1524-1527 followup_masters = masters_with_followup(masters, load_followup_reference(..), load_soldout_ref_posts(..), load_posted_date(..))
    :1528 pipeline = run_v102_pipeline(response_text, ctx, followup_masters, fixed_products=fixed_products)
  本番は response_text を保存済みの件(rows)から作る(:1518 _response_from_rows)ので、rows と応答の件の位置は必ず合う。
  試験の新しい応答には対応する rows が無い。本番の件(rows)は f_ct の元の応答のもの。
  check  : 応答は本番の件から作るので位置が必ず合う。fixed_products は :1520 と同じく条件なしで当てる。
  convert: 本番の行から、新しい応答で落とした件を除いた数が、新しい受理件数と同じときだけ同じ関数を当てる（svc.py:1180-1196 の数え方）。
           違えば位置が対応しないので {}（人の判断なし）にし、人の判断がある投稿では stderr に「FIXED_SKIP」を出す。【本番に無い判断】
  DB を使う他の後処理(_write_results のうち買取単位・価格の引き継ぎ・〆の相手・単位と価格の確認)は掛けない（印で説明する）。
絶対にしないこと: _write_results の呼び出し・書き込み・commit。取引は READ ONLY で、最後に rollback する。
"""
import json
import sys
from types import SimpleNamespace

from sqlalchemy import text

from app.services import line_analysis_v102_svc as S
from app.tasks.tcg_extraction import _get_sync_session, load_extraction_context

SNAP_COLS = ["extraction_item_id", "line_start", "line_end", "source_lines", "raw_price",
             "raw_quantity", "product_id", "condition_canonical",
             "unit_canonical", "status", "ship_ja", "price_normalized",
             "quantity_normalized", "exclusion"]
COMPARE = ["product_id", "condition_canonical", "unit_canonical", "status", "ship_ja",
           "price_normalized", "quantity_normalized", "exclusion"]
SCHEMA = S.analyzer.TCG_SCHEMA
assert not hasattr(sys.modules[__name__], "_write_results")  # 書き込みの関数は使わない


def _s(v):
    return "" if v is None else str(v)


def _num(v):
    t = _s(v).strip()
    if t == "":
        return ""
    try:
        return format(float(t), ".2f")
    except ValueError:
        return t


def _norm(col, v):
    if col in ("price_normalized", "quantity_normalized"):
        return _num(v)
    if col == "ship_ja":
        return S._balance_brackets(_s(v)).replace(" ", "").replace("　", "") if v else ""
    return _s(v)


def convert_job(response_text, v102_items, raw_text, masters, unit_ids):
    """v102_items → SNAP_COLS の行のリスト（行 = 応答の件ごと）と、中間の (item, row, values)。
    本番の _write_results のうち、DB を使わない部分（件の対応付け・列の値・まとめ売り・バルク価格・規則13）だけを同じ関数で行う。
    DB を使う部分（人の判断・買取単位・価格の引き継ぎ・〆の相手・単位と価格の確認）は掛けない（印で説明する）。"""
    try:
        body = json.loads(response_text)
    except ValueError as e:
        raise ValueError("応答がJSONとして読めない: %s" % e)
    items = body.get("items") if isinstance(body, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("応答に items が無い/空")
    rows = [SimpleNamespace(id="g%d" % r["gemini_index"], **r) for r in S._item_rows(items)]
    pairs = S._map_to_rows(v102_items, rows)
    vals = [S._analysis_values(item, masters, unit_ids, {}) for item, _r in pairs]
    unit_words, set_words = S.split_unit_words({a: info[0] for a, info in (masters.get("unit_alias_to_info") or {}).items()})
    blocks = [S._source_block(raw_text, r) for _i, r in pairs]
    bulk = S.PRODUCT_KUBUN_BULK
    vals = [S._apply_bundle(v, b, unit_words, set_words, unit_ids, bulk_shapes=it.get("product_category") == bulk)
            for v, (it, _r), b in zip(vals, pairs, blocks)]
    vals = [S._apply_bulk_price(v, it, b if it.get("product_category") == bulk else "", unit_ids)
            for v, (it, _r), b in zip(vals, pairs, blocks)]
    vals = S._sell_out_stock_closed_in_the_same_post(pairs, vals, {}, unit_ids, masters["status_entries"])
    out = []
    for v, (item, r) in zip(vals, pairs):
        out.append({
            "extraction_item_id": r.id, "line_start": _s(r.line_start), "line_end": _s(r.line_end),
            "source_lines": "[" + ", ".join(str(x) for x in (r.source_lines or [])) + "]",
            "raw_price": _s(r.raw_price), "raw_quantity": _s(r.raw_quantity),
            "product_id": _s(v["product_id"]), "condition_canonical": _s(v["condition_canonical"]),
            "unit_canonical": _s(v["unit_canonical"]), "status": _s(v["status"]), "ship_ja": _s(v["ship_ja"]),
            "price_normalized": _s(v["price_normalized"]), "quantity_normalized": _s(v["quantity_normalized"]),
            "exclusion": _s(v["exclusion"]),
        })
    return out, [(i, r, v) for v, (i, r) in zip(vals, pairs)]


def _job_state(session, job, cache, masters):
    """投稿ごとの本番側の材料を1回だけ読む（読み取りのみ）。run_v102_analysis :1491-1527 と同じ読み方。"""
    if job in cache:
        return cache[job]
    ctx = load_extraction_context(session, job)
    jr = session.execute(text(f"SELECT gemini_unsure FROM {SCHEMA}.extraction_jobs WHERE id=:ej"), {"ej": job}).one()
    rows = session.execute(text(f"""
        SELECT id, gemini_index, source_lines, line_start, line_end, raw_price, raw_quantity FROM {SCHEMA}.extraction_items
        WHERE extraction_job_id = :ej ORDER BY gemini_index NULLS LAST, created_at, id"""), {"ej": job}).fetchall()
    st = {"ctx": ctx, "rows": rows, "gemini_unsure": jr.gemini_unsure, "decisions": None, "fm": None}
    if ctx is not None and rows:
        st["decisions"] = S.load_v102_decisions(session, [str(r.id) for r in rows])
        st["fm"] = S.masters_with_followup(masters, S.load_followup_reference(session, job),
                                           S.load_soldout_ref_posts(session, job), S.load_posted_date(session, job))
    cache[job] = st
    return st


def rejudge(response_text, st, masters, unit_ids, job, mode):
    """本番の再判定と同じ組み立て（上の docstring 参照）で response_text を判定し直す。戻り: (conv, mid, fixed)。
    mode="check"  : 応答は本番の件から作った写しなので位置が必ず合う。本番 svc.py:1520 と同じく _fixed_products を条件なしで当てる。
    mode="convert": 新しい応答。本番の行から、新しい応答で落とした件を除いた数が、新しい受理件数と同じときだけ _fixed_products を当てる。違えば FIXED_SKIP（{}）。"""
    ctx, rows = st["ctx"], st["rows"]
    decisions = st["decisions"] or {}  # R7: 件が無い投稿は None になり得る
    if mode == "check":
        fixed = S._fixed_products(response_text, ctx, masters, rows, decisions)
    else:
        items_new, _e = S.parse_v101_response(response_text, ctx.raw_text, status_entries=masters["status_entries"], keep_rejected=True)
        n_new = len([it for it in items_new if "rejected" not in it])
        rej_new = {it["gemini_index"] for it in items_new if "rejected" in it}
        n_prod = len([r for r in rows if r.gemini_index not in rej_new])  # svc.py:1186-1191 の accepted と同じ数え方
        if n_new == n_prod:
            fixed = S._fixed_products(response_text, ctx, masters, rows, decisions)
        else:
            fixed = {}
            if any(d.product_id is not None for d in decisions.values()):
                print("FIXED_SKIP\t%s\t受理件数 新%d != 本番の行から新しく落とした件を除いた数%d（人の判断あり）" % (job, n_new, n_prod), file=sys.stderr)
    pipe = S.run_v102_pipeline(response_text, ctx, st["fm"], fixed_products=fixed)
    conv, mid = convert_job(response_text, pipe["v102_items"], ctx.raw_text, masters, unit_ids)
    return conv, mid, fixed


def _begin(session):
    session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))  # R5: 試験の最中に動いたマスタを読み直さない・書かない


def _assert_tx(session):
    """R5 の確認: 取引が repeatable read かつ読み取り専用か。違えば False（終了コード 2 で止める）。"""
    iso = session.execute(text("SHOW transaction_isolation")).scalar()
    ro = session.execute(text("SHOW transaction_read_only")).scalar()
    print("TX\ttransaction_isolation=%s\ttransaction_read_only=%s" % (iso, ro), file=sys.stderr)
    return iso == "repeatable read" and ro == "on"


def _prod_rows(session, job_id):
    """本番の写し（v102-f_ct）。件ごとに computed_at が一番新しい1行。"""
    return {int(r.gemini_index): r for r in session.execute(text(f"""
        SELECT DISTINCT ON (i.gemini_index) i.gemini_index, i.id AS item_id, ar.product_id, ar.condition_canonical,
               ar.unit_canonical, ar.status, ar.ship_ja, ar.price_normalized, ar.quantity_normalized, ar.exclusion,
               ar.bundle_size, ar.price_basis, ar.review_reasons
        FROM {SCHEMA}.extraction_items i JOIN {SCHEMA}.analysis_results ar ON ar.extraction_item_id = i.id
        WHERE i.extraction_job_id = :ej AND ar.engine_version = :ev AND i.gemini_index IS NOT NULL
        ORDER BY i.gemini_index, ar.computed_at DESC, ar.id
    """), {"ej": job_id, "ev": S.V102_ENGINE_VERSION}).fetchall()}


def check(job_ids):
    session = _get_sync_session()
    total = diffs = unmarked = 0
    try:
        _begin(session)
        masters, unit_ids = S.load_v102_masters(session)
        print("job\tindex\tcolumns\tmarks\tvalues")
        cache = {}
        for job in job_ids:
            st = _job_state(session, job, cache, masters)
            ctx, rows = st["ctx"], st["rows"]
            if ctx is None or not rows or any(r.gemini_index is None for r in rows):
                print("%s\t-\t読めない投稿\t印なし" % job); unmarked += 1; continue
            response_text = S._response_from_rows(rows, st["gemini_unsure"])
            decisions = st["decisions"] or {}
            try:
                conv_a, mid, _fx = rejudge(response_text, st, masters, unit_ids, job, "check")  # 本番 svc.py:1520 と同じく _fixed_products を条件なしで当てる
            except Exception as e:  # noqa: BLE001
                print("%s\t-\t判定し直しで例外 %s\t印なし" % (job, type(e).__name__)); unmarked += 1; continue
            prod = _prod_rows(session, job)
            uai = masters.get("unit_alias_to_info") or {}
            for pos, row in enumerate(rows):
                total += 1
                pr = prod.get(int(row.gemini_index))
                if pr is None:
                    diffs += 1; unmarked += 1
                    print("%s\t%d\t本番の写し無し\t印なし" % (job, pos)); continue
                cols = [c for c in COMPARE if _norm(c, conv_a[pos][c]) != _norm(c, getattr(pr, c))]
                if not cols:
                    continue
                diffs += 1
                marks = []
                item, _r, vals = mid[pos]
                if decisions.get(str(row.id)) is not None:
                    marks.append("人の判断あり")
                if item.get("product_category") == S.PRODUCT_KUBUN_BULK:
                    marks.append("バルク系")
                if pr.bundle_size is not None:
                    marks.append("まとめ売りの数あり")
                try:
                    if S.is_buyback_candidate(item, vals, uai):
                        marks.append("買取単位")
                except Exception:  # noqa: BLE001
                    pass
                if S.STATUS_SOLD_OUT in (_s(pr.status), _s(conv_a[pos]["status"])) or item.get("soldout_targets"):
                    marks.append("〆の相手")
                if _s(pr.price_basis).startswith(S.PRICE_BASIS_INHERIT_PREFIX):
                    marks.append("価格の引き継ぎ")
                if not marks:
                    unmarked += 1
                vals_txt = " / ".join("%s: 本番=%s 変換器=%s" % (c, _norm(c, getattr(pr, c)), _norm(c, conv_a[pos][c])) for c in cols)  # 表示のみ
                print("%s\t%d\t%s\t%s\t%s" % (job, pos, ",".join(cols), ",".join(marks) or "印なし", vals_txt.replace("\t", " ").replace("\n", " ")))
        print("SUMMARY\tjobs=%d\titems=%d\tdiffs=%d\tunmarked=%d" % (len(job_ids), total, diffs, unmarked))
        print("結果: " + ("進まない（印の無い差が %d 件）" % unmarked if unmarked else "進める（差はすべて印あり）"))
        tx_ok = _assert_tx(session)
    finally:
        session.rollback()  # 何も書いていないが、最後は必ず戻す
        session.close()
    if not tx_ok:
        print("ABORT: 取引が repeatable read / read only ではない", file=sys.stderr)
        return 2
    return 1 if unmarked else 0


def convert(paths):
    session = _get_sync_session()
    try:
        _begin(session)
        masters, unit_ids = S.load_v102_masters(session)
        print("\t".join(["tag", "repeat", "source_message"] + SNAP_COLS))
        cache, sm_cache = {}, {}
        for p in paths:
            tag = p.rsplit("/", 1)[-1].replace(".jsonl", "")
            n_in = n_out = n_skip = n_cnt_diff = 0
            for line in open(p, encoding="utf-8"):
                if not line.strip():
                    continue
                r = json.loads(line)
                n_in += 1
                job = r["job_id"]
                st = _job_state(session, job, cache, masters)
                if st["ctx"] is None:
                    print("SKIP\t%s\t%s\t投稿なし" % (tag, job), file=sys.stderr); n_skip += 1; continue
                if job not in sm_cache:
                    sm_cache[job] = session.execute(
                        text(f"SELECT source_message_id::text FROM {SCHEMA}.extraction_jobs WHERE id=:ej"), {"ej": job}).scalar_one()
                if not r.get("response_text") or r.get("error"):
                    print("SKIP\t%s\t%s\t応答なし" % (tag, job), file=sys.stderr); n_skip += 1; continue
                try:
                    conv, _mid, _fx = rejudge(r["response_text"], st, masters, unit_ids, job, "convert")
                except Exception as e:  # noqa: BLE001
                    print("SKIP\t%s\t%s\t%s: %s" % (tag, job, type(e).__name__, str(e)[:120]), file=sys.stderr); n_skip += 1; continue
                if r.get("v102_items") is not None and len(r["v102_items"]) != len(conv):
                    n_cnt_diff += 1  # 参考: prompt_ab の v102_items の件数と違う投稿（判定には使わない）
                for c in conv:
                    print("\t".join([tag, str(r["repeat"]), sm_cache[job]] + [c[k].replace("\t", " ").replace("\n", " ") for k in SNAP_COLS]))
                n_out += 1
            print("CONVERT\t%s\t行=%d\t判定=%d\t除外=%d\tv102_items件数が違う=%d" % (tag, n_in, n_out, n_skip, n_cnt_diff), file=sys.stderr)
        tx_ok = _assert_tx(session)
    finally:
        session.rollback()
        session.close()
    if not tx_ok:
        print("ABORT: 取引が repeatable read / read only ではない", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "check":
        sys.exit(check([l.strip() for l in open(sys.argv[2]) if l.strip() and not l.startswith("#")]))
    if mode == "convert":
        sys.exit(convert(sys.argv[2:]))
    sys.exit("usage: check JOBS_FILE | convert JSONL...")
