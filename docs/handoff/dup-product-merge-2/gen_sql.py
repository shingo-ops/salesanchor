#!/usr/bin/env python3
"""Generate precheck/dryrun/apply/rollback/postcheck .sql for the duplicate merge 2 (10 confirmed duplicate pairs).
   Survivors / retired:
     398 (UA-PC02BT)  <- 440573 (PM0225)
     440434 (PM0232) <- 1386 (LOR-the-first-chapter)   440435 (PM0233) <- 1385   440578 (PM0234) <- 1384
     440579 (PM0235) <- 1383   440580 (PM0236) <- 1382   440581 (PM0237) <- 1381   440582 (PM0238) <- 1380
     440583 (PM0239) <- 1379   440587 (PM0243) <- 1376
Same style as docs/handoff/dup-product-merge (dup-merge-20261005): one spec table (specs.json) -> five files.
Additions in this merge: extraction_shadow_results.product_id is repointed; the retired row's search/exclude keywords that the
survivor does not have yet are inserted into the survivor (next positions); a deterministic tie-break is added to the is_current
rule (is_current DESC, id) because one partition of the pair 440435 <- 1385 has two rows with identical timestamps.
Nothing here touches a database.
Usage: python3 gen_sql.py   (writes next to this file; specs.json holds the expected counts captured by a fresh read-only read)

Rollback design: apply.sql stores, in the audit_log.new_values JSON of each retired product (key "merge"), the exact ids of every
repointed row, every is_current flip (with the old value and old updated_at) and every inserted keyword row. rollback.sql reads
those audit rows (marked by merge_id) and restores exactly those rows.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MERGE_ID = "dup-merge-2-20261005"
ACTOR_APPLY = "claude-opus (PO承認 2026-10-05 dup-merge-2)"
ACTOR_ROLLBACK = "claude-opus (rollback dup-merge-2; PO decision required)"

SPECS = json.load(open(HERE / "specs.json", encoding="utf-8"))
ID_LIST = ", ".join(str(i) for s in SPECS for i in (s["retired"], s["survivor"]))

SNAP = """jsonb_build_object(
        'product', (SELECT to_jsonb(p) FROM public.products p WHERE p.id = __ID__),
        'search_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_search_keywords k WHERE k.product_id = __ID__), '[]'::jsonb),
        'exclude_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_exclude_keywords k WHERE k.product_id = __ID__), '[]'::jsonb))"""

SHOW = """SELECT p.id, p.product_code, p.mark, p.name, p.is_active,
       (SELECT count(*) FROM public.analysis_results ar WHERE ar.product_id = p.id) AS analysis_results,
       (SELECT count(*) FROM public.extraction_items ei WHERE ei.resolved_product_code = p.id::text) AS extraction_items,
       (SELECT count(*) FROM public.buyback_shop_products b WHERE b.product_id = p.id) AS buyback_shop_products,
       (SELECT count(*) FROM public.extraction_shadow_results sh WHERE sh.product_id = p.id) AS shadow_results,
       (SELECT count(*) FROM public.product_search_keywords k WHERE k.product_id = p.id) AS search_kw_rows,
       (SELECT count(*) FROM public.product_exclude_keywords k WHERE k.product_id = p.id) AS exclude_kw_rows
  FROM public.products p WHERE p.id IN (__ID_LIST__) ORDER BY p.id;"""

# ---------------------------------------------------------------- precheck / postcheck
PRECHECK_DO = """DO $do$
DECLARE
  specs jsonb := $j$__SPECS__$j$::jsonb;
  spec jsonb; r record; s record; n int; f_false int; f_true int; kw jsonb;
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
    SELECT count(*) INTO n FROM public.analysis_results WHERE product_id = s.id;
    IF n <> (spec->>'s_ar')::int THEN RAISE EXCEPTION 'analysis_results for survivor % = % (expected %)', s.id, n, spec->>'s_ar'; END IF;
    SELECT count(*) INTO n FROM public.extraction_items WHERE resolved_product_code = r.id::text;
    IF n <> (spec->>'ei')::int THEN RAISE EXCEPTION 'extraction_items for % = % (expected %)', r.id, n, spec->>'ei'; END IF;
    SELECT count(*) INTO n FROM public.buyback_shop_products WHERE product_id = r.id;
    IF n <> (spec->>'bb')::int THEN RAISE EXCEPTION 'buyback_shop_products for % = % (expected %)', r.id, n, spec->>'bb'; END IF;
    SELECT count(*) INTO n FROM public.extraction_shadow_results WHERE product_id = r.id;
    IF n <> (spec->>'sh')::int THEN RAISE EXCEPTION 'extraction_shadow_results for % = % (expected %)', r.id, n, spec->>'sh'; END IF;
    SELECT count(*) INTO n FROM public.product_search_keywords WHERE product_id = r.id;
    IF n <> (spec->>'r_skw')::int THEN RAISE EXCEPTION 'search keywords of retired % = % (expected %)', r.id, n, spec->>'r_skw'; END IF;
    SELECT count(*) INTO n FROM public.product_exclude_keywords WHERE product_id = r.id;
    IF n <> (spec->>'r_ekw')::int THEN RAISE EXCEPTION 'exclude keywords of retired % = % (expected %)', r.id, n, spec->>'r_ekw'; END IF;
    SELECT count(*) INTO n FROM public.product_search_keywords WHERE product_id = s.id;
    IF n <> (spec->>'s_skw')::int THEN RAISE EXCEPTION 'search keywords of survivor % = % (expected %)', s.id, n, spec->>'s_skw'; END IF;
    SELECT count(*) INTO n FROM public.product_exclude_keywords WHERE product_id = s.id;
    IF n <> (spec->>'s_ekw')::int THEN RAISE EXCEPTION 'exclude keywords of survivor % = % (expected %)', s.id, n, spec->>'s_ekw'; END IF;
    FOR kw IN SELECT * FROM jsonb_array_elements(spec->'kw') LOOP
      IF kw->>'kind' = 'search' THEN
        IF NOT EXISTS (SELECT 1 FROM public.product_search_keywords WHERE product_id = r.id AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'retired % lacks search keyword %', r.id, kw->>'keyword'; END IF;
        IF EXISTS (SELECT 1 FROM public.product_search_keywords WHERE product_id = s.id AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'survivor % already has search keyword %', s.id, kw->>'keyword'; END IF;
      ELSE
        IF NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = r.id AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'retired % lacks exclude keyword %', r.id, kw->>'keyword'; END IF;
        IF EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = s.id AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'survivor % already has exclude keyword %', s.id, kw->>'keyword'; END IF;
      END IF;
    END LOOP;
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
             (row_number() OVER (PARTITION BY x.ch, x.condition_id ORDER BY x.received_at DESC, x.computed_at DESC, x.is_current DESC, x.id) = 1) AS should
        FROM x WHERE EXISTS (SELECT 1 FROM aff WHERE aff.ch IS NOT DISTINCT FROM x.ch AND aff.condition_id = x.condition_id))
    SELECT count(*) FILTER (WHERE is_current AND NOT should), count(*) FILTER (WHERE NOT is_current AND should)
      INTO f_false, f_true FROM ranked;
    IF f_false <> (spec->>'flips')::int OR f_true <> (spec->>'flips_to_true')::int THEN
      RAISE EXCEPTION 'predicted flips for survivor % = to_false % / to_true % (expected % / %)', s.id, f_false, f_true, spec->>'flips', spec->>'flips_to_true';
    END IF;
    RAISE NOTICE 'OK pair % -> %: ar % / flips % / ei % / bb % / sh % / keywords to carry %', r.product_code, s.product_code, spec->>'ar', spec->>'flips', spec->>'ei', spec->>'bb', spec->>'sh', jsonb_array_length(spec->'kw');
  END LOOP;
END
$do$;"""

POSTCHECK_DO = """DO $do$
DECLARE
  a record; nv jsonb; n int; bad int; seen int := 0; kw jsonb;
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
    SELECT count(*) INTO n FROM public.extraction_shadow_results WHERE product_id = (nv#>>'{merge,retired}')::int;
    IF n <> 0 THEN RAISE EXCEPTION 'extraction_shadow_results still point at retired %: %', nv#>>'{merge,retired}', n; END IF;
    SELECT count(*) INTO n FROM public.analysis_results WHERE product_id = (nv#>>'{merge,survivor}')::int AND id::text IN (SELECT jsonb_array_elements_text(nv#>'{merge,ids,analysis_results}'));
    IF n <> jsonb_array_length(nv#>'{merge,ids,analysis_results}') THEN RAISE EXCEPTION 'repointed analysis_results not all on survivor %: % of %', nv#>>'{merge,survivor}', n, jsonb_array_length(nv#>'{merge,ids,analysis_results}'); END IF;
    SELECT count(*) INTO n FROM public.extraction_shadow_results WHERE product_id = (nv#>>'{merge,survivor}')::int AND id::text IN (SELECT jsonb_array_elements_text(nv#>'{merge,ids,extraction_shadow_results}'));
    IF n <> jsonb_array_length(nv#>'{merge,ids,extraction_shadow_results}') THEN RAISE EXCEPTION 'repointed shadow rows not all on survivor %', nv#>>'{merge,survivor}'; END IF;
    SELECT count(*) INTO bad FROM jsonb_array_elements(nv#>'{merge,ids,is_current_flips}') f
      JOIN public.analysis_results ar ON ar.id::text = f->>'id' WHERE ar.is_current IS DISTINCT FROM (f->>'to')::boolean;
    IF bad <> 0 THEN RAISE EXCEPTION 'is_current flips not in place for survivor %: % rows differ', nv#>>'{merge,survivor}', bad; END IF;
    FOR kw IN SELECT * FROM jsonb_array_elements(nv#>'{merge,ids,keywords_inserted}') LOOP
      IF kw->>'kind' = 'search' THEN
        IF NOT EXISTS (SELECT 1 FROM public.product_search_keywords WHERE id = (kw->>'id')::int AND product_id = (nv#>>'{merge,survivor}')::int AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'search keyword row % missing on survivor %', kw->>'id', nv#>>'{merge,survivor}'; END IF;
      ELSE
        IF NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE id = (kw->>'id')::int AND product_id = (nv#>>'{merge,survivor}')::int AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'exclude keyword row % missing on survivor %', kw->>'id', nv#>>'{merge,survivor}'; END IF;
      END IF;
    END LOOP;
    RAISE NOTICE 'OK % -> %: retired inactive, 0 references left, % repointed rows on the survivor, % flips in place, % keyword rows carried', nv#>>'{merge,retired}', nv#>>'{merge,survivor}', n, jsonb_array_length(nv#>'{merge,ids,is_current_flips}'), jsonb_array_length(nv#>'{merge,ids,keywords_inserted}');
  END LOOP;
  IF seen <> __N__ THEN RAISE EXCEPTION 'expected __N__ audit rows, found %', seen; END IF;
END
$do$;"""

# ---------------------------------------------------------------- apply (also used for dryrun)
APPLY_DO = """DO $do$
DECLARE
  specs jsonb := $j$__SPECS__$j$::jsonb;
  spec jsonb; r_id int; s_id int; r record; s record; kw jsonb;
  ar_ids jsonb; ei_ids jsonb; bb_ids jsonb; sh_ids jsonb; flips jsonb; kw_ids jsonb; new_kw_id int; next_pos int;
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
    sh_ids := COALESCE((SELECT jsonb_agg(id::text ORDER BY id::text) FROM public.extraction_shadow_results WHERE product_id = r_id), '[]'::jsonb);
    IF jsonb_array_length(ar_ids) <> (spec->>'ar')::int THEN RAISE EXCEPTION 'GUARD analysis_results for % = % (expected %)', r_id, jsonb_array_length(ar_ids), spec->>'ar'; END IF;
    IF jsonb_array_length(ei_ids) <> (spec->>'ei')::int THEN RAISE EXCEPTION 'GUARD extraction_items for % = % (expected %)', r_id, jsonb_array_length(ei_ids), spec->>'ei'; END IF;
    IF jsonb_array_length(bb_ids) <> (spec->>'bb')::int THEN RAISE EXCEPTION 'GUARD buyback_shop_products for % = % (expected %)', r_id, jsonb_array_length(bb_ids), spec->>'bb'; END IF;
    IF jsonb_array_length(sh_ids) <> (spec->>'sh')::int THEN RAISE EXCEPTION 'GUARD extraction_shadow_results for % = % (expected %)', r_id, jsonb_array_length(sh_ids), spec->>'sh'; END IF;
    SELECT count(*) INTO s_before FROM public.analysis_results WHERE product_id = s_id;
    IF s_before <> (spec->>'s_ar')::int THEN RAISE EXCEPTION 'GUARD survivor % analysis_results = % (expected %)', s_id, s_before, spec->>'s_ar'; END IF;
    SELECT count(*) INTO c FROM public.product_search_keywords WHERE product_id = s_id;
    IF c <> (spec->>'s_skw')::int THEN RAISE EXCEPTION 'GUARD survivor % search keywords = % (expected %)', s_id, c, spec->>'s_skw'; END IF;
    SELECT count(*) INTO c FROM public.product_exclude_keywords WHERE product_id = s_id;
    IF c <> (spec->>'s_ekw')::int THEN RAISE EXCEPTION 'GUARD survivor % exclude keywords = % (expected %)', s_id, c, spec->>'s_ekw'; END IF;
    SELECT count(*) INTO c FROM public.product_search_keywords WHERE product_id = r_id;
    IF c <> (spec->>'r_skw')::int THEN RAISE EXCEPTION 'GUARD retired % search keywords = % (expected %)', r_id, c, spec->>'r_skw'; END IF;
    SELECT count(*) INTO c FROM public.product_exclude_keywords WHERE product_id = r_id;
    IF c <> (spec->>'r_ekw')::int THEN RAISE EXCEPTION 'GUARD retired % exclude keywords = % (expected %)', r_id, c, spec->>'r_ekw'; END IF;

    -- 3. analysis_results.product_id retired -> survivor
    UPDATE public.analysis_results SET product_id = s_id
     WHERE product_id = r_id AND id::text IN (SELECT jsonb_array_elements_text(ar_ids));
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> (spec->>'ar')::int THEN RAISE EXCEPTION 'analysis_results UPDATE for % affected % rows (expected %)', r_id, c, spec->>'ar'; END IF;
    RAISE NOTICE 'pair % -> %: analysis_results repointed rows=%', r_id, s_id, c;

    -- 4. is_current recompute inside the affected partitions only, with the app's rule (backend/app/services/tcg_analyzer_svc.py:1759-1791):
    --    partition = (supplier channel, product, condition); newest source_messages.received_at wins, then analysis_results.computed_at DESC
    --    (+ is_current DESC, id as a deterministic tie-break that keeps the row that is current today);
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
               (row_number() OVER (PARTITION BY sm.supplier_channel_id, ar.condition_id ORDER BY sm.received_at DESC, ar.computed_at DESC, ar.is_current DESC, ar.id) = 1) AS should
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

    -- 7. extraction_shadow_results.product_id
    UPDATE public.extraction_shadow_results SET product_id = s_id
     WHERE product_id = r_id AND id::text IN (SELECT jsonb_array_elements_text(sh_ids));
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> (spec->>'sh')::int THEN RAISE EXCEPTION 'extraction_shadow_results UPDATE for % affected % rows (expected %)', r_id, c, spec->>'sh'; END IF;
    RAISE NOTICE 'pair % -> %: extraction_shadow_results repointed rows=%', r_id, s_id, c;

    -- 8. carry the retired row's keywords that the survivor does not have (list fixed in specs.json; compared with normalize_for_match when it was built)
    kw_ids := '[]'::jsonb;
    FOR kw IN SELECT * FROM jsonb_array_elements(spec->'kw') LOOP
      IF kw->>'kind' = 'search' THEN
        IF NOT EXISTS (SELECT 1 FROM public.product_search_keywords WHERE product_id = r_id AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'GUARD retired % lacks search keyword %', r_id, kw->>'keyword'; END IF;
        IF EXISTS (SELECT 1 FROM public.product_search_keywords WHERE product_id = s_id AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'GUARD survivor % already has search keyword %', s_id, kw->>'keyword'; END IF;
        SELECT COALESCE(max("position"), -1) + 1 INTO next_pos FROM public.product_search_keywords WHERE product_id = s_id;
        INSERT INTO public.product_search_keywords (keyword, "position", product_id, updated_at) VALUES (kw->>'keyword', next_pos, s_id, NOW()) RETURNING id INTO new_kw_id;
      ELSE
        IF NOT EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = r_id AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'GUARD retired % lacks exclude keyword %', r_id, kw->>'keyword'; END IF;
        IF EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE product_id = s_id AND keyword = kw->>'keyword') THEN RAISE EXCEPTION 'GUARD survivor % already has exclude keyword %', s_id, kw->>'keyword'; END IF;
        SELECT COALESCE(max("position"), -1) + 1 INTO next_pos FROM public.product_exclude_keywords WHERE product_id = s_id;
        INSERT INTO public.product_exclude_keywords (keyword, "position", product_id, updated_at) VALUES (kw->>'keyword', next_pos, s_id, NOW()) RETURNING id INTO new_kw_id;
      END IF;
      kw_ids := kw_ids || jsonb_build_array(jsonb_build_object('kind', kw->>'kind', 'id', new_kw_id, 'keyword', kw->>'keyword', 'position', next_pos));
    END LOOP;
    IF jsonb_array_length(kw_ids) <> jsonb_array_length(spec->'kw') THEN RAISE EXCEPTION 'keyword rows inserted for % = % (expected %)', s_id, jsonb_array_length(kw_ids), jsonb_array_length(spec->'kw'); END IF;
    RAISE NOTICE 'pair % -> %: keyword rows carried=%', r_id, s_id, jsonb_array_length(kw_ids);

    -- 9. retire the product (its own keyword rows stay)
    UPDATE public.products SET is_active = FALSE WHERE id = r_id AND is_active = TRUE;
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> 1 THEN RAISE EXCEPTION 'products is_active UPDATE for % affected % rows (expected 1)', r_id, c; END IF;
    RAISE NOTICE 'pair % -> %: product % retired rows=%', r_id, s_id, r_id, c;

    -- final state of this pair
    IF EXISTS (SELECT 1 FROM public.analysis_results WHERE product_id = r_id)
       OR EXISTS (SELECT 1 FROM public.extraction_items WHERE resolved_product_code = r_id::text)
       OR EXISTS (SELECT 1 FROM public.buyback_shop_products WHERE product_id = r_id)
       OR EXISTS (SELECT 1 FROM public.extraction_shadow_results WHERE product_id = r_id) THEN
      RAISE EXCEPTION 'FINAL STATE: references to retired % remain', r_id;
    END IF;
    SELECT count(*) INTO c FROM public.analysis_results WHERE product_id = s_id;
    IF c <> s_before + (spec->>'ar')::int THEN RAISE EXCEPTION 'FINAL STATE: survivor % has % analysis_results (expected %)', s_id, c, s_before + (spec->>'ar')::int; END IF;
    SELECT count(*) INTO c FROM public.product_search_keywords WHERE product_id = s_id;
    IF c <> (spec->>'s_skw')::int + (SELECT count(*) FROM jsonb_array_elements(spec->'kw') k WHERE k->>'kind' = 'search') THEN RAISE EXCEPTION 'FINAL STATE: survivor % has % search keyword rows', s_id, c; END IF;
    SELECT count(*) INTO c FROM public.product_exclude_keywords WHERE product_id = s_id;
    IF c <> (spec->>'s_ekw')::int + (SELECT count(*) FROM jsonb_array_elements(spec->'kw') k WHERE k->>'kind' = 'exclude') THEN RAISE EXCEPTION 'FINAL STATE: survivor % has % exclude keyword rows', s_id, c; END IF;

    -- 10. audit row (new_values carries the exact repointed ids for rollback)
    after_snap := jsonb_build_object('retired', __SNAP_R__, 'survivor', __SNAP_S__);
    merge_info := jsonb_build_object(
      'merge_id', '__MERGE_ID__', 'retired', r_id, 'survivor', s_id,
      'counts', jsonb_build_object('analysis_results', jsonb_array_length(ar_ids), 'is_current_flips', jsonb_array_length(flips),
                                   'extraction_items', jsonb_array_length(ei_ids), 'buyback_shop_products', jsonb_array_length(bb_ids),
                                   'extraction_shadow_results', jsonb_array_length(sh_ids), 'keywords_inserted', jsonb_array_length(kw_ids), 'products_deactivated', 1),
      'ids', jsonb_build_object('analysis_results', ar_ids, 'is_current_flips', flips, 'extraction_items', ei_ids, 'buyback_shop_products', bb_ids,
                                'extraction_shadow_results', sh_ids, 'keywords_inserted', kw_ids));
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
  a record; nv jsonb; m jsonb; r_id int; s_id int; c int; seen int := 0; touched_flips int; kw jsonb;
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

    UPDATE public.extraction_shadow_results SET product_id = r_id
     WHERE product_id = s_id AND id::text IN (SELECT jsonb_array_elements_text(m#>'{ids,extraction_shadow_results}'));
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> jsonb_array_length(m#>'{ids,extraction_shadow_results}') THEN RAISE EXCEPTION 'rollback extraction_shadow_results %: % rows (expected %)', r_id, c, jsonb_array_length(m#>'{ids,extraction_shadow_results}'); END IF;
    RAISE NOTICE 'rollback % : extraction_shadow_results restored rows=%', r_id, c;

    -- delete exactly the keyword rows that apply inserted (guard: id, survivor and text still match)
    FOR kw IN SELECT * FROM jsonb_array_elements(m#>'{ids,keywords_inserted}') LOOP
      IF kw->>'kind' = 'search' THEN
        DELETE FROM public.product_search_keywords WHERE id = (kw->>'id')::int AND product_id = s_id AND keyword = kw->>'keyword';
      ELSE
        DELETE FROM public.product_exclude_keywords WHERE id = (kw->>'id')::int AND product_id = s_id AND keyword = kw->>'keyword';
      END IF;
      GET DIAGNOSTICS c = ROW_COUNT;
      IF c <> 1 THEN RAISE EXCEPTION 'rollback keyword row % (%) on % affected % rows (expected 1)', kw->>'id', kw->>'kind', s_id, c; END IF;
    END LOOP;
    RAISE NOTICE 'rollback % : keyword rows deleted=%', r_id, jsonb_array_length(m#>'{ids,keywords_inserted}');

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


def fill(t):
    t = t.replace("__SPECS__", specs_json()).replace("__N__", str(len(SPECS))).replace("__MERGE_ID__", MERGE_ID)
    t = t.replace("__ACTOR_APPLY__", ACTOR_APPLY).replace("__ACTOR_ROLLBACK__", ACTOR_ROLLBACK).replace("__ACTOR__", ACTOR_APPLY)
    t = t.replace("__SNAP_R__", SNAP.replace("__ID__", "r_id")).replace("__SNAP_S__", SNAP.replace("__ID__", "s_id"))
    return t.replace("__ID_LIST__", ID_LIST)


def head(title, note):
    return (f"-- {title}\n-- {note}\n-- Target: DB jarvis_db, schema public. Merge 2 (merge_id {MERGE_ID}): 10 duplicate pairs, see specs.json. Generated by gen_sql.py; do not hand-edit.\n"
            "\\set ON_ERROR_STOP on\n")


def main():
    import sys
    global SPECS, ID_LIST
    out = HERE
    if len(sys.argv) == 3:  # test mode: gen_sql.py <out_dir> <specs.json> (used only for the local throwaway-database test)
        out = Path(sys.argv[1]); SPECS = json.load(open(sys.argv[2], encoding="utf-8")); out.mkdir(parents=True, exist_ok=True)
        ID_LIST = ", ".join(str(i) for s in SPECS for i in (s["retired"], s["survivor"]))
    pre = "BEGIN;\nSET LOCAL app.is_operator = 'true';\nSET LOCAL lock_timeout = '10s';\nSET LOCAL statement_timeout = '120s';\n"
    files = {
        "precheck.sql": head("precheck.sql (READ-ONLY)", "RAISES unless the products and every count (and the predicted is_current flips and keyword carry) equal the expected numbers.")
        + "BEGIN READ ONLY;\n" + fill(SHOW) + "\n" + fill(PRECHECK_DO) + "\nROLLBACK;\n",
        "dryrun.sql": head("dryrun.sql (same as apply.sql but ends with ROLLBACK)", "Nothing is kept. Shows the final state inside the transaction, then rolls back.")
        + pre + fill(APPLY_DO) + "\n" + fill(SHOW) + "\nROLLBACK;\n",
        "apply.sql": head("apply.sql (WRITES, one transaction, ends with COMMIT)", "Repoint analysis_results / extraction_items / buyback_shop_products / extraction_shadow_results, recompute is_current in the affected partitions, carry keywords, retire the 10 products, 10 audit rows.")
        + pre + fill(APPLY_DO) + "\n" + fill(SHOW) + "\nCOMMIT;\n",
        "rollback.sql": head("rollback.sql (WRITES; needs a NEW PO decision before running)", "Restores exactly the rows saved in the apply audit rows (merge_id " + MERGE_ID + "): product_id, is_current + updated_at, resolved_product_code, buyback and shadow product_id, inserted keyword rows deleted, is_active.")
        + pre + fill(ROLLBACK_DO) + "\n" + fill(SHOW) + "\nCOMMIT;\n",
        "postcheck.sql": head("postcheck.sql (READ-ONLY)", "RAISES unless the merge is in place (retired inactive, 0 references left, saved ids on the survivors, flips in place, keyword rows present).")
        + "BEGIN READ ONLY;\n" + fill(SHOW) + "\n" + fill(POSTCHECK_DO)
        + f"\nSELECT id, changed_by, changed_at, length(old_values) AS old_len, length(new_values) AS new_len\n  FROM public.audit_log WHERE table_name = 'products' AND new_values LIKE '%{MERGE_ID}%' ORDER BY id;\nROLLBACK;\n",
    }
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
        print(name, len(text.splitlines()), "lines")


if __name__ == "__main__":
    main()
