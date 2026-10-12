#!/usr/bin/env python3
"""Generate precheck/dryrun/apply/rollback/postcheck .sql for the duplicate merge:
   retire 440561 (PM0226), 440572 (PM0224), 440571 (PM0223) into survivors 226 (DB-FB09), 625 (YGO-LOCR), 626 (YGO-LOCH).
Same style as the deckbuild / MEGA changes (one spec table -> five files). Nothing here touches a database.
Usage: python3 gen_sql.py   (writes next to this file)

Rollback design: apply.sql stores, in the audit_log.new_values JSON of each retired product (key "merge"), the exact ids
of every repointed row and every is_current flip (with the old value and old updated_at). rollback.sql reads those audit
rows (marked by merge_id) and restores exactly those rows.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MERGE_ID = "dup-merge-20261005"
ACTOR_APPLY = "claude-opus (PO承認 2026-10-05)"
ACTOR_ROLLBACK = "claude-opus (rollback; PO decision required)"

# expected counts as of 2026-10-05 (read-only reads; see product-check/dup_merge_prep.md and dupmerge/flip_calc.txt)
SPECS = [
    {"retired": 440561, "retired_code": "PM0226", "survivor": 226, "survivor_code": "DB-FB09",
     "ar": 82, "flips": 8, "flips_to_true": 0, "ei": 1, "bb": 0},
    {"retired": 440572, "retired_code": "PM0224", "survivor": 625, "survivor_code": "YGO-LOCR",
     "ar": 53, "flips": 6, "flips_to_true": 0, "ei": 6, "bb": 1},
    {"retired": 440571, "retired_code": "PM0223", "survivor": 626, "survivor_code": "YGO-LOCH",
     "ar": 32, "flips": 4, "flips_to_true": 0, "ei": 10, "bb": 0},
]

SNAP = """jsonb_build_object(
        'product', (SELECT to_jsonb(p) FROM public.products p WHERE p.id = __ID__),
        'search_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_search_keywords k WHERE k.product_id = __ID__), '[]'::jsonb),
        'exclude_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_exclude_keywords k WHERE k.product_id = __ID__), '[]'::jsonb))"""

SHOW = """SELECT p.id, p.product_code, p.mark, p.name, p.is_active,
       (SELECT count(*) FROM public.analysis_results ar WHERE ar.product_id = p.id) AS analysis_results,
       (SELECT count(*) FROM public.extraction_items ei WHERE ei.resolved_product_code = p.id::text) AS extraction_items,
       (SELECT count(*) FROM public.buyback_shop_products b WHERE b.product_id = p.id) AS buyback_shop_products,
       (SELECT count(*) FROM public.product_search_keywords k WHERE k.product_id = p.id) AS search_kw_rows
  FROM public.products p WHERE p.id IN (440561, 226, 440572, 625, 440571, 626) ORDER BY p.id;"""

# ---------------------------------------------------------------- precheck / postcheck
PRECHECK_DO = """DO $do$
DECLARE
  specs jsonb := $j$__SPECS__$j$::jsonb;
  spec jsonb; r record; s record; n int; f_false int; f_true int;
BEGIN
  FOR spec IN SELECT * FROM jsonb_array_elements(specs) LOOP
    SELECT * INTO r FROM public.products WHERE id = (spec->>'retired')::int;
    SELECT * INTO s FROM public.products WHERE id = (spec->>'survivor')::int;
    IF r.id IS NULL OR s.id IS NULL THEN RAISE EXCEPTION 'product missing for pair %', spec; END IF;
    IF r.product_code IS DISTINCT FROM spec->>'retired_code' OR s.product_code IS DISTINCT FROM spec->>'survivor_code'
       OR r.is_active IS NOT TRUE OR s.is_active IS NOT TRUE THEN
      RAISE EXCEPTION 'PAIR state differs: retired % (%, active %), survivor % (%, active %)', r.id, r.product_code, r.is_active, s.id, s.product_code, s.is_active;
    END IF;
    SELECT count(*) INTO n FROM public.analysis_results WHERE product_id = r.id;
    IF n <> (spec->>'ar')::int THEN RAISE EXCEPTION 'analysis_results for % = % (expected %)', r.id, n, spec->>'ar'; END IF;
    SELECT count(*) INTO n FROM public.extraction_items WHERE resolved_product_code = r.id::text;
    IF n <> (spec->>'ei')::int THEN RAISE EXCEPTION 'extraction_items for % = % (expected %)', r.id, n, spec->>'ei'; END IF;
    SELECT count(*) INTO n FROM public.buyback_shop_products WHERE product_id = r.id;
    IF n <> (spec->>'bb')::int THEN RAISE EXCEPTION 'buyback_shop_products for % = % (expected %)', r.id, n, spec->>'bb'; END IF;
    -- predicted is_current flips under the app rule (tcg_analyzer_svc.py:1759-1791), computed as if the retired rows already pointed at the survivor
    WITH x AS (
      SELECT ar.id, ar.condition_id, ar.is_current, ar.computed_at, sm.received_at, sm.supplier_channel_id AS ch,
             (ar.product_id = r.id) AS is_retired
        FROM public.analysis_results ar
        JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
        JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
        JOIN public.source_messages sm ON sm.id = ej.source_message_id
       WHERE ar.product_id IN (r.id, s.id) AND ar.pid_resolved = TRUE),
    aff AS (SELECT DISTINCT ch, condition_id FROM x WHERE is_retired AND condition_id IS NOT NULL),
    ranked AS (
      SELECT x.id, x.is_current,
             (row_number() OVER (PARTITION BY x.ch, x.condition_id ORDER BY x.received_at DESC, x.computed_at DESC) = 1) AS should
        FROM x WHERE EXISTS (SELECT 1 FROM aff WHERE aff.ch IS NOT DISTINCT FROM x.ch AND aff.condition_id = x.condition_id))
    SELECT count(*) FILTER (WHERE is_current AND NOT should), count(*) FILTER (WHERE NOT is_current AND should)
      INTO f_false, f_true FROM ranked;
    IF f_false <> (spec->>'flips')::int OR f_true <> (spec->>'flips_to_true')::int THEN
      RAISE EXCEPTION 'predicted flips for survivor % = to_false % / to_true % (expected % / %)', s.id, f_false, f_true, spec->>'flips', spec->>'flips_to_true';
    END IF;
    RAISE NOTICE 'OK pair % -> %: ar % / flips % / ei % / bb %', r.product_code, s.product_code, spec->>'ar', spec->>'flips', spec->>'ei', spec->>'bb';
  END LOOP;
END
$do$;"""

POSTCHECK_DO = """DO $do$
DECLARE
  a record; nv jsonb; spec jsonb; n int; bad int; seen int := 0;
BEGIN
  FOR a IN SELECT id, new_values FROM public.audit_log
            WHERE table_name = 'products' AND changed_by = '__ACTOR__' AND new_values LIKE '%__MERGE_ID__%' ORDER BY id LOOP
    nv := a.new_values::jsonb;
    seen := seen + 1;
    IF EXISTS (SELECT 1 FROM public.products WHERE id = (nv#>>'{merge,retired}')::int AND is_active) THEN RAISE EXCEPTION 'retired % is still active', nv#>>'{merge,retired}'; END IF;
    IF NOT EXISTS (SELECT 1 FROM public.products WHERE id = (nv#>>'{merge,survivor}')::int AND is_active) THEN RAISE EXCEPTION 'survivor % is not active', nv#>>'{merge,survivor}'; END IF;
    SELECT count(*) INTO n FROM public.analysis_results WHERE product_id = (nv#>>'{merge,retired}')::int;
    IF n <> 0 THEN RAISE EXCEPTION 'analysis_results still point at retired %: %', nv#>>'{merge,retired}', n; END IF;
    SELECT count(*) INTO n FROM public.extraction_items WHERE resolved_product_code = nv#>>'{merge,retired}';
    IF n <> 0 THEN RAISE EXCEPTION 'extraction_items still hold retired %: %', nv#>>'{merge,retired}', n; END IF;
    SELECT count(*) INTO n FROM public.buyback_shop_products WHERE product_id = (nv#>>'{merge,retired}')::int;
    IF n <> 0 THEN RAISE EXCEPTION 'buyback_shop_products still point at retired %: %', nv#>>'{merge,retired}', n; END IF;
    SELECT count(*) INTO n FROM public.analysis_results WHERE product_id = (nv#>>'{merge,survivor}')::int AND id::text IN (SELECT jsonb_array_elements_text(nv#>'{merge,ids,analysis_results}'));
    IF n <> jsonb_array_length(nv#>'{merge,ids,analysis_results}') THEN RAISE EXCEPTION 'repointed analysis_results not all on survivor %: % of %', nv#>>'{merge,survivor}', n, jsonb_array_length(nv#>'{merge,ids,analysis_results}'); END IF;
    SELECT count(*) INTO bad FROM jsonb_array_elements(nv#>'{merge,ids,is_current_flips}') f
      JOIN public.analysis_results ar ON ar.id::text = f->>'id' WHERE ar.is_current IS DISTINCT FROM (f->>'to')::boolean;
    IF bad <> 0 THEN RAISE EXCEPTION 'is_current flips not in place for survivor %: % rows differ', nv#>>'{merge,survivor}', bad; END IF;
    RAISE NOTICE 'OK % -> %: retired inactive, 0 references left, % repointed rows on the survivor, % flips in place', nv#>>'{merge,retired}', nv#>>'{merge,survivor}', n, jsonb_array_length(nv#>'{merge,ids,is_current_flips}');
  END LOOP;
  IF seen <> __N__ THEN RAISE EXCEPTION 'expected __N__ audit rows, found %', seen; END IF;
END
$do$;"""

# ---------------------------------------------------------------- apply (also used for dryrun)
APPLY_DO = """DO $do$
DECLARE
  specs jsonb := $j$__SPECS__$j$::jsonb;
  spec jsonb; r_id int; s_id int; r record; s record;
  ar_ids jsonb; ei_ids jsonb; bb_ids jsonb; flips jsonb;
  c int; n_to_true int; s_before int;
  before_snap jsonb; after_snap jsonb; merge_info jsonb; touched int := 0;
BEGIN
  FOR spec IN SELECT * FROM jsonb_array_elements(specs) LOOP
    r_id := (spec->>'retired')::int; s_id := (spec->>'survivor')::int;

    -- 1. lock and guard the two products
    SELECT * INTO r FROM public.products WHERE id = r_id FOR UPDATE;
    SELECT * INTO s FROM public.products WHERE id = s_id FOR UPDATE;
    IF r.id IS NULL OR s.id IS NULL THEN RAISE EXCEPTION 'product missing for pair %', spec; END IF;
    IF r.product_code IS DISTINCT FROM spec->>'retired_code' OR s.product_code IS DISTINCT FROM spec->>'survivor_code'
       OR r.is_active IS NOT TRUE OR s.is_active IS NOT TRUE THEN
      RAISE EXCEPTION 'GUARD pair state: retired % (%, active %), survivor % (%, active %)', r.id, r.product_code, r.is_active, s.id, s.product_code, s.is_active;
    END IF;
    before_snap := jsonb_build_object('retired', __SNAP_R__, 'survivor', __SNAP_S__);

    -- 2. ids of the rows that will be repointed, and exact-count guards
    ar_ids := COALESCE((SELECT jsonb_agg(id::text ORDER BY id::text) FROM public.analysis_results WHERE product_id = r_id), '[]'::jsonb);
    ei_ids := COALESCE((SELECT jsonb_agg(id::text ORDER BY id::text) FROM public.extraction_items WHERE resolved_product_code = r_id::text), '[]'::jsonb);
    bb_ids := COALESCE((SELECT jsonb_agg(id::text ORDER BY id::text) FROM public.buyback_shop_products WHERE product_id = r_id), '[]'::jsonb);
    IF jsonb_array_length(ar_ids) <> (spec->>'ar')::int THEN RAISE EXCEPTION 'GUARD analysis_results for % = % (expected %)', r_id, jsonb_array_length(ar_ids), spec->>'ar'; END IF;
    IF jsonb_array_length(ei_ids) <> (spec->>'ei')::int THEN RAISE EXCEPTION 'GUARD extraction_items for % = % (expected %)', r_id, jsonb_array_length(ei_ids), spec->>'ei'; END IF;
    IF jsonb_array_length(bb_ids) <> (spec->>'bb')::int THEN RAISE EXCEPTION 'GUARD buyback_shop_products for % = % (expected %)', r_id, jsonb_array_length(bb_ids), spec->>'bb'; END IF;
    SELECT count(*) INTO s_before FROM public.analysis_results WHERE product_id = s_id;

    -- 3. analysis_results.product_id retired -> survivor
    UPDATE public.analysis_results SET product_id = s_id
     WHERE product_id = r_id AND id::text IN (SELECT jsonb_array_elements_text(ar_ids));
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> (spec->>'ar')::int THEN RAISE EXCEPTION 'analysis_results UPDATE for % affected % rows (expected %)', r_id, c, spec->>'ar'; END IF;
    RAISE NOTICE 'pair % -> %: analysis_results repointed rows=%', r_id, s_id, c;

    -- 4. is_current recompute inside the affected partitions only, with the app's rule (backend/app/services/tcg_analyzer_svc.py:1759-1791):
    --    partition = (supplier channel, product, condition); newest source_messages.received_at wins, then analysis_results.computed_at DESC;
    --    only pid_resolved rows with a product; conditions compare with "=" so NULL-condition rows are not touched (same as the app).
    flips := COALESCE((
      WITH aff AS (
        SELECT DISTINCT sm.supplier_channel_id AS ch, ar.condition_id
          FROM public.analysis_results ar
          JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
          JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
          JOIN public.source_messages sm ON sm.id = ej.source_message_id
         WHERE ar.id::text IN (SELECT jsonb_array_elements_text(ar_ids)) AND ar.pid_resolved = TRUE AND ar.condition_id IS NOT NULL),
      ranked AS (
        SELECT ar.id, ar.is_current AS old_cur, ar.updated_at AS old_upd,
               (row_number() OVER (PARTITION BY sm.supplier_channel_id, ar.condition_id ORDER BY sm.received_at DESC, ar.computed_at DESC) = 1) AS should
          FROM public.analysis_results ar
          JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
          JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
          JOIN public.source_messages sm ON sm.id = ej.source_message_id
         WHERE ar.product_id = s_id AND ar.pid_resolved = TRUE
           AND EXISTS (SELECT 1 FROM aff WHERE aff.ch IS NOT DISTINCT FROM sm.supplier_channel_id AND aff.condition_id = ar.condition_id))
      SELECT jsonb_agg(jsonb_build_object('id', id::text, 'from', old_cur, 'to', should, 'old_updated_at', old_upd) ORDER BY id::text)
        FROM ranked WHERE old_cur IS DISTINCT FROM should), '[]'::jsonb);
    SELECT count(*) INTO n_to_true FROM jsonb_array_elements(flips) f WHERE (f->>'to')::boolean;
    IF jsonb_array_length(flips) <> (spec->>'flips')::int OR n_to_true <> (spec->>'flips_to_true')::int THEN
      RAISE EXCEPTION 'GUARD is_current flips for survivor % = % (to true %) (expected % / %)', s_id, jsonb_array_length(flips), n_to_true, spec->>'flips', spec->>'flips_to_true';
    END IF;
    UPDATE public.analysis_results ar SET is_current = (f->>'to')::boolean, updated_at = NOW()
      FROM jsonb_array_elements(flips) f
     WHERE ar.id::text = f->>'id' AND ar.product_id = s_id;
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> jsonb_array_length(flips) THEN RAISE EXCEPTION 'is_current UPDATE affected % rows (expected %)', c, jsonb_array_length(flips); END IF;
    RAISE NOTICE 'pair % -> %: is_current flips=% (to true %)', r_id, s_id, c, n_to_true;

    -- 5. extraction_items.resolved_product_code (text of the id)
    UPDATE public.extraction_items SET resolved_product_code = s_id::text
     WHERE resolved_product_code = r_id::text AND id::text IN (SELECT jsonb_array_elements_text(ei_ids));
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> (spec->>'ei')::int THEN RAISE EXCEPTION 'extraction_items UPDATE for % affected % rows (expected %)', r_id, c, spec->>'ei'; END IF;
    RAISE NOTICE 'pair % -> %: extraction_items repointed rows=%', r_id, s_id, c;

    -- 6. buyback_shop_products.product_id
    UPDATE public.buyback_shop_products SET product_id = s_id
     WHERE product_id = r_id AND id::text IN (SELECT jsonb_array_elements_text(bb_ids));
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> (spec->>'bb')::int THEN RAISE EXCEPTION 'buyback_shop_products UPDATE for % affected % rows (expected %)', r_id, c, spec->>'bb'; END IF;
    RAISE NOTICE 'pair % -> %: buyback_shop_products repointed rows=%', r_id, s_id, c;

    -- 7. retire the product (keyword rows stay)
    UPDATE public.products SET is_active = FALSE WHERE id = r_id AND is_active = TRUE;
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> 1 THEN RAISE EXCEPTION 'products is_active UPDATE for % affected % rows (expected 1)', r_id, c; END IF;
    RAISE NOTICE 'pair % -> %: product % retired rows=%', r_id, s_id, r_id, c;

    -- final state of this pair
    IF EXISTS (SELECT 1 FROM public.analysis_results WHERE product_id = r_id)
       OR EXISTS (SELECT 1 FROM public.extraction_items WHERE resolved_product_code = r_id::text)
       OR EXISTS (SELECT 1 FROM public.buyback_shop_products WHERE product_id = r_id) THEN
      RAISE EXCEPTION 'FINAL STATE: references to retired % remain', r_id;
    END IF;
    SELECT count(*) INTO c FROM public.analysis_results WHERE product_id = s_id;
    IF c <> s_before + (spec->>'ar')::int THEN RAISE EXCEPTION 'FINAL STATE: survivor % has % analysis_results (expected %)', s_id, c, s_before + (spec->>'ar')::int; END IF;

    -- 8. audit row (new_values carries the exact repointed ids for rollback)
    after_snap := jsonb_build_object('retired', __SNAP_R__, 'survivor', __SNAP_S__);
    merge_info := jsonb_build_object(
      'merge_id', '__MERGE_ID__', 'retired', r_id, 'survivor', s_id,
      'counts', jsonb_build_object('analysis_results', jsonb_array_length(ar_ids), 'is_current_flips', jsonb_array_length(flips),
                                   'extraction_items', jsonb_array_length(ei_ids), 'buyback_shop_products', jsonb_array_length(bb_ids), 'products_deactivated', 1),
      'ids', jsonb_build_object('analysis_results', ar_ids, 'is_current_flips', flips, 'extraction_items', ei_ids, 'buyback_shop_products', bb_ids));
    INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
    VALUES ('products', gen_random_uuid(), 'UPDATE', '__ACTOR__', before_snap::text,
            (jsonb_build_object('retired_product_after', after_snap->'retired', 'survivor_after', after_snap->'survivor', 'merge', merge_info))::text);
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> 1 THEN RAISE EXCEPTION 'audit_log insert for % rows=% (expected 1)', r_id, c; END IF;
    touched := touched + 1;
  END LOOP;
  IF touched <> __N__ THEN RAISE EXCEPTION 'touched % pairs (expected __N__)', touched; END IF;
  RAISE NOTICE 'DONE: % pairs merged, % audit_log rows', touched, touched;
END
$do$;"""

# ---------------------------------------------------------------- rollback
ROLLBACK_DO = """DO $do$
DECLARE
  a record; nv jsonb; m jsonb; r_id int; s_id int; c int; seen int := 0; touched_flips int;
BEGIN
  FOR a IN SELECT id, new_values FROM public.audit_log
            WHERE table_name = 'products' AND changed_by = '__ACTOR_APPLY__' AND new_values LIKE '%__MERGE_ID__%'
              AND NOT EXISTS (SELECT 1 FROM public.audit_log rb
                               WHERE rb.table_name = 'products' AND rb.changed_by = '__ACTOR_ROLLBACK__'
                                 AND CASE WHEN rb.new_values LIKE '{%' THEN (rb.new_values::jsonb->>'rolled_back_audit_id')::bigint END = audit_log.id)
            ORDER BY id LOOP
    nv := a.new_values::jsonb; m := nv->'merge';
    IF m->>'merge_id' IS DISTINCT FROM '__MERGE_ID__' THEN CONTINUE; END IF;
    seen := seen + 1;
    r_id := (m->>'retired')::int; s_id := (m->>'survivor')::int;
    IF EXISTS (SELECT 1 FROM public.products WHERE id = r_id AND is_active) THEN RAISE EXCEPTION 'GUARD: retired % is already active', r_id; END IF;

    -- analysis_results.product_id back to the retired product (only the saved ids)
    UPDATE public.analysis_results SET product_id = r_id
     WHERE product_id = s_id AND id::text IN (SELECT jsonb_array_elements_text(m#>'{ids,analysis_results}'));
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> jsonb_array_length(m#>'{ids,analysis_results}') THEN RAISE EXCEPTION 'rollback analysis_results % -> %: % rows (expected %)', s_id, r_id, c, jsonb_array_length(m#>'{ids,analysis_results}'); END IF;
    RAISE NOTICE 'rollback % : analysis_results restored rows=%', r_id, c;

    -- is_current and updated_at back to their old values (only the saved flip rows; they are the rows flipped to FALSE or TRUE by apply)
    UPDATE public.analysis_results ar SET is_current = (f->>'from')::boolean, updated_at = (f->>'old_updated_at')::timestamptz
      FROM jsonb_array_elements(m#>'{ids,is_current_flips}') f
     WHERE ar.id::text = f->>'id' AND ar.is_current IS NOT DISTINCT FROM (f->>'to')::boolean;
    GET DIAGNOSTICS touched_flips = ROW_COUNT;
    IF touched_flips <> jsonb_array_length(m#>'{ids,is_current_flips}') THEN RAISE EXCEPTION 'rollback is_current %: % rows (expected %)', r_id, touched_flips, jsonb_array_length(m#>'{ids,is_current_flips}'); END IF;
    RAISE NOTICE 'rollback % : is_current restored rows=%', r_id, touched_flips;

    UPDATE public.extraction_items SET resolved_product_code = r_id::text
     WHERE resolved_product_code = s_id::text AND id::text IN (SELECT jsonb_array_elements_text(m#>'{ids,extraction_items}'));
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> jsonb_array_length(m#>'{ids,extraction_items}') THEN RAISE EXCEPTION 'rollback extraction_items %: % rows (expected %)', r_id, c, jsonb_array_length(m#>'{ids,extraction_items}'); END IF;
    RAISE NOTICE 'rollback % : extraction_items restored rows=%', r_id, c;

    UPDATE public.buyback_shop_products SET product_id = r_id
     WHERE product_id = s_id AND id::text IN (SELECT jsonb_array_elements_text(m#>'{ids,buyback_shop_products}'));
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> jsonb_array_length(m#>'{ids,buyback_shop_products}') THEN RAISE EXCEPTION 'rollback buyback_shop_products %: % rows (expected %)', r_id, c, jsonb_array_length(m#>'{ids,buyback_shop_products}'); END IF;
    RAISE NOTICE 'rollback % : buyback_shop_products restored rows=%', r_id, c;

    UPDATE public.products SET is_active = TRUE WHERE id = r_id AND is_active = FALSE;
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> 1 THEN RAISE EXCEPTION 'rollback products %: % rows (expected 1)', r_id, c; END IF;

    INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
    VALUES ('products', gen_random_uuid(), 'UPDATE', '__ACTOR_ROLLBACK__', a.new_values,
            jsonb_build_object('rolled_back_merge_id', '__MERGE_ID__', 'rolled_back_audit_id', a.id, 'retired', r_id, 'survivor', s_id)::text);
  END LOOP;
  IF seen <> __N__ THEN RAISE EXCEPTION 'rollback expected __N__ audit rows, found %', seen; END IF;
  RAISE NOTICE 'ROLLBACK DONE: % pairs restored', seen;
END
$do$;"""


def specs_json():
    return json.dumps(SPECS, ensure_ascii=False, indent=1)


def fill(t, **kw):
    t = t.replace("__SPECS__", specs_json()).replace("__N__", str(len(SPECS))).replace("__MERGE_ID__", MERGE_ID)
    t = t.replace("__ACTOR_APPLY__", ACTOR_APPLY).replace("__ACTOR_ROLLBACK__", ACTOR_ROLLBACK).replace("__ACTOR__", ACTOR_APPLY)
    t = t.replace("__SNAP_R__", SNAP.replace("__ID__", "r_id")).replace("__SNAP_S__", SNAP.replace("__ID__", "s_id"))
    return t


def head(title, note):
    return (f"-- {title}\n-- {note}\n-- Target: DB jarvis_db, schema public. Retire 440561/440572/440571 into 226/625/626. Generated by gen_sql.py; do not hand-edit.\n"
            "\\set ON_ERROR_STOP on\n")


def main():
    import sys
    global SPECS
    out = HERE
    if len(sys.argv) == 3:  # test mode: gen_sql.py <out_dir> <specs.json> (used only for the local throwaway-database test)
        out = Path(sys.argv[1]); SPECS = json.load(open(sys.argv[2], encoding="utf-8")); out.mkdir(parents=True, exist_ok=True)
    pre = "BEGIN;\nSET LOCAL app.is_operator = 'true';\nSET LOCAL lock_timeout = '10s';\nSET LOCAL statement_timeout = '120s';\n"
    files = {
        "precheck.sql": head("precheck.sql (READ-ONLY)", "RAISES unless the six products and every count (and the predicted is_current flips) equal the expected numbers.")
        + "BEGIN READ ONLY;\n" + SHOW + "\n" + fill(PRECHECK_DO) + "\nROLLBACK;\n",
        "dryrun.sql": head("dryrun.sql (same as apply.sql but ends with ROLLBACK)", "Nothing is kept. Shows the final state inside the transaction, then rolls back.")
        + pre + fill(APPLY_DO) + "\n" + SHOW + "\nROLLBACK;\n",
        "apply.sql": head("apply.sql (WRITES, one transaction, ends with COMMIT)", "Repoint analysis_results / extraction_items / buyback_shop_products, recompute is_current in the affected partitions, retire the 3 products, 3 audit rows.")
        + pre + fill(APPLY_DO) + "\n" + SHOW + "\nCOMMIT;\n",
        "rollback.sql": head("rollback.sql (WRITES; needs a NEW PO decision before running)", "Restores exactly the rows saved in the apply audit rows (merge_id " + MERGE_ID + "): product_id, is_current + updated_at, resolved_product_code, buyback product_id, is_active.")
        + pre + fill(ROLLBACK_DO) + "\n" + SHOW + "\nCOMMIT;\n",
        "postcheck.sql": head("postcheck.sql (READ-ONLY)", "RAISES unless the merge is in place (retired inactive, 0 references left, saved ids on the survivors, flips in place).")
        + "BEGIN READ ONLY;\n" + SHOW + "\n" + fill(POSTCHECK_DO)
        + f"\nSELECT id, changed_by, changed_at, length(old_values) AS old_len, length(new_values) AS new_len\n  FROM public.audit_log WHERE table_name = 'products' AND new_values LIKE '%{MERGE_ID}%' ORDER BY id;\nROLLBACK;\n",
    }
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
        print(name, len(text.splitlines()), "lines")


if __name__ == "__main__":
    main()
