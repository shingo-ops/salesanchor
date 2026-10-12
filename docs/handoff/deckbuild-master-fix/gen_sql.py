#!/usr/bin/env python3
"""Generate precheck/apply/dryrun/rollback/postcheck .sql from one spec table (same method as the 2026-10-01
supplier-rules change). Output goes next to this file. Nothing here touches a database.

Usage: python3 gen_sql.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACTOR_APPLY = "claude-opus (PO承認 2026-10-04)"
ACTOR_ROLLBACK = "claude-opus (rollback; PO decision required)"
IDS = "58, 60, 74, 75, 103, 105"

# today's production values (masters/current_values.csv, read 2026-10-04 21:19) -> target
SPECS = [
    {"id": 58, "code": "SV9",
     "old": {"mark": "SV9", "name": "バトルパートナーズ", "search": ["バトルパートナーズ"], "exclude": ["デッキビルド", "デッキビルドBOX バトルパートナーズ"]},
     "new": {"mark": "SV9", "name": "バトルパートナーズ", "search": ["バトルパートナーズ"], "exclude": ["デッキビルド"]}},
    {"id": 60, "code": "SVN",
     "old": {"mark": "SV9", "name": "バトルパートナーズ", "search": ["バトルパートナーズ デッキビルド"], "exclude": []},
     "new": {"mark": "SVN", "name": "バトルパートナーズ デッキビルドBOX", "search": ["バトルパートナーズ デッキビルド", "SV9 デッキビルド"], "exclude": []}},
    {"id": 74, "code": "SV7",
     "old": {"mark": "SV7", "name": "ステラミラクル", "search": ["ステラミラクル"], "exclude": ["デッキビルド", "デッキビルドBOX ステラミラクル"]},
     "new": {"mark": "SV7", "name": "ステラミラクル", "search": ["ステラミラクル"], "exclude": ["デッキビルド"]}},
    {"id": 75, "code": "SVK",
     "old": {"mark": "SV7", "name": "ステラミラクル", "search": ["デッキビルド ステラミラクル"], "exclude": []},
     "new": {"mark": "SVK", "name": "ステラミラクル デッキビルドBOX", "search": ["ステラミラクル デッキビルド", "SV7 デッキビルド"], "exclude": []}},
    {"id": 103, "code": "SV3",
     "old": {"mark": "SV3", "name": "黒炎の支配者", "search": ["黒炎", "黒炎の支配者"], "exclude": ["デッキビルド", "デッキビルドBOX"]},
     "new": {"mark": "SV3", "name": "黒炎の支配者", "search": ["黒炎", "黒炎の支配者"], "exclude": ["デッキビルド"]}},
    {"id": 105, "code": "SVF",
     "old": {"mark": "SV3", "name": "黒炎の支配者", "search": ["黒炎の支配者 デッキビルド"], "exclude": []},
     "new": {"mark": "SVF", "name": "黒炎の支配者 デッキビルドBOX", "search": ["黒炎の支配者 デッキビルド", "黒炎 デッキビルド", "SV3 デッキビルド"], "exclude": []}},
]

SHOW = f"""SELECT p.id, p.product_code, p.mark, p.name, p.is_active,
       (SELECT string_agg(k.position || ':' || k.keyword, ' | ' ORDER BY k.position, k.id)
          FROM public.product_search_keywords k WHERE k.product_id = p.id) AS search_keywords,
       (SELECT string_agg(k.position || ':' || k.keyword, ' | ' ORDER BY k.position, k.id)
          FROM public.product_exclude_keywords k WHERE k.product_id = p.id) AS exclude_keywords
  FROM public.products p WHERE p.id IN ({IDS}) ORDER BY p.id;"""

# DO block: checks only (read-only). {side} = 'old' (precheck) or 'new' (postcheck)
CHECK_DO = """DO $do$
DECLARE
  spec jsonb;
  specs jsonb := $j$__SPECS__$j$::jsonb;
  pid int; r record; cur_s text[]; cur_e text[]; want_s text[]; want_e text[];
BEGIN
  FOR spec IN SELECT * FROM jsonb_array_elements(specs) LOOP
    pid := (spec->>'id')::int;
    SELECT * INTO r FROM public.products WHERE id = pid;
    IF NOT FOUND THEN RAISE EXCEPTION 'product % not found', pid; END IF;
    cur_s := ARRAY(SELECT keyword FROM public.product_search_keywords WHERE product_id = pid ORDER BY position, id);
    cur_e := ARRAY(SELECT keyword FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id);
    want_s := ARRAY(SELECT jsonb_array_elements_text(spec->'__SIDE__'->'search'));
    want_e := ARRAY(SELECT jsonb_array_elements_text(spec->'__SIDE__'->'exclude'));
    IF r.product_code IS DISTINCT FROM spec->>'code' OR r.mark IS DISTINCT FROM spec->'__SIDE__'->>'mark'
       OR r.name IS DISTINCT FROM spec->'__SIDE__'->>'name' OR r.is_active IS NOT TRUE
       OR cur_s IS DISTINCT FROM want_s OR cur_e IS DISTINCT FROM want_e THEN
      RAISE EXCEPTION 'MISMATCH (__SIDE__) id=%: code=% mark=% name=% active=% search=% exclude=%',
        pid, r.product_code, r.mark, r.name, r.is_active, cur_s, cur_e;
    END IF;
    RAISE NOTICE 'OK (__SIDE__) id=% code=% mark=% name=%', pid, r.product_code, r.mark, r.name;
  END LOOP;
END
$do$;"""

# DO block: the change. {from_}/{to_} are 'old'/'new' (apply) or 'new'/'old' (rollback)
CHANGE_DO = """DO $do$
DECLARE
  spec jsonb;
  specs jsonb := $j$__SPECS__$j$::jsonb;
  pid int; c int; r record;
  cur_s text[]; cur_e text[]; from_s text[]; from_e text[]; to_s text[]; to_e text[];
  before_snap jsonb; after_snap jsonb; touched int := 0;
BEGIN
  FOR spec IN SELECT * FROM jsonb_array_elements(specs) LOOP
    pid := (spec->>'id')::int;
    -- lock + guard on the values we expect to replace (mirrors FOR UPDATE + revision check in update_product_detail)
    SELECT * INTO r FROM public.products WHERE id = pid FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'product % not found', pid; END IF;
    cur_s := ARRAY(SELECT keyword FROM public.product_search_keywords WHERE product_id = pid ORDER BY position, id);
    cur_e := ARRAY(SELECT keyword FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id);
    from_s := ARRAY(SELECT jsonb_array_elements_text(spec->'__FROM__'->'search'));
    from_e := ARRAY(SELECT jsonb_array_elements_text(spec->'__FROM__'->'exclude'));
    to_s := ARRAY(SELECT jsonb_array_elements_text(spec->'__TO__'->'search'));
    to_e := ARRAY(SELECT jsonb_array_elements_text(spec->'__TO__'->'exclude'));
    IF r.product_code IS DISTINCT FROM spec->>'code' OR r.mark IS DISTINCT FROM spec->'__FROM__'->>'mark'
       OR r.name IS DISTINCT FROM spec->'__FROM__'->>'name' OR r.is_active IS NOT TRUE
       OR cur_s IS DISTINCT FROM from_s OR cur_e IS DISTINCT FROM from_e THEN
      RAISE EXCEPTION 'GUARD id=%: unexpected current state code=% mark=% name=% search=% exclude=%',
        pid, r.product_code, r.mark, r.name, cur_s, cur_e;
    END IF;

    before_snap := jsonb_build_object(
      'product', (SELECT to_jsonb(p) FROM public.products p WHERE p.id = pid),
      'search_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_search_keywords k WHERE k.product_id = pid), '[]'::jsonb),
      'exclude_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_exclude_keywords k WHERE k.product_id = pid), '[]'::jsonb));

    UPDATE public.products SET name = spec->'__TO__'->>'name', mark = spec->'__TO__'->>'mark'
     WHERE id = pid AND name = spec->'__FROM__'->>'name' AND mark = spec->'__FROM__'->>'mark';
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> 1 THEN RAISE EXCEPTION 'UPDATE products id=% affected % rows (expected 1)', pid, c; END IF;
    RAISE NOTICE 'id=% products UPDATE rows=%: mark % -> %, name % -> %', pid, c, spec->'__FROM__'->>'mark', spec->'__TO__'->>'mark', spec->'__FROM__'->>'name', spec->'__TO__'->>'name';

    -- keyword lists: only the lists that change; delete all rows of the product, re-insert with position 1..n (as the app does)
    IF to_s IS DISTINCT FROM from_s THEN
      DELETE FROM public.product_search_keywords WHERE product_id = pid;
      GET DIAGNOSTICS c = ROW_COUNT;
      IF c <> COALESCE(array_length(from_s, 1), 0) THEN RAISE EXCEPTION 'search delete id=% rows=% (expected %)', pid, c, COALESCE(array_length(from_s, 1), 0); END IF;
      RAISE NOTICE 'id=% search_keywords deleted rows=%', pid, c;
      INSERT INTO public.product_search_keywords (product_id, keyword, position)
        SELECT pid, t.w, t.o FROM unnest(to_s) WITH ORDINALITY AS t(w, o);
      GET DIAGNOSTICS c = ROW_COUNT;
      IF c <> COALESCE(array_length(to_s, 1), 0) THEN RAISE EXCEPTION 'search insert id=% rows=% (expected %)', pid, c, COALESCE(array_length(to_s, 1), 0); END IF;
      RAISE NOTICE 'id=% search_keywords inserted rows=%', pid, c;
    END IF;
    IF to_e IS DISTINCT FROM from_e THEN
      DELETE FROM public.product_exclude_keywords WHERE product_id = pid;
      GET DIAGNOSTICS c = ROW_COUNT;
      IF c <> COALESCE(array_length(from_e, 1), 0) THEN RAISE EXCEPTION 'exclude delete id=% rows=% (expected %)', pid, c, COALESCE(array_length(from_e, 1), 0); END IF;
      RAISE NOTICE 'id=% exclude_keywords deleted rows=%', pid, c;
      INSERT INTO public.product_exclude_keywords (product_id, keyword, position)
        SELECT pid, t.w, t.o FROM unnest(to_e) WITH ORDINALITY AS t(w, o);
      GET DIAGNOSTICS c = ROW_COUNT;
      IF c <> COALESCE(array_length(to_e, 1), 0) THEN RAISE EXCEPTION 'exclude insert id=% rows=% (expected %)', pid, c, COALESCE(array_length(to_e, 1), 0); END IF;
      RAISE NOTICE 'id=% exclude_keywords inserted rows=%', pid, c;
    END IF;

    -- final state of this product must equal the target
    SELECT * INTO r FROM public.products WHERE id = pid;
    cur_s := ARRAY(SELECT keyword FROM public.product_search_keywords WHERE product_id = pid ORDER BY position, id);
    cur_e := ARRAY(SELECT keyword FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id);
    IF r.mark IS DISTINCT FROM spec->'__TO__'->>'mark' OR r.name IS DISTINCT FROM spec->'__TO__'->>'name'
       OR cur_s IS DISTINCT FROM to_s OR cur_e IS DISTINCT FROM to_e THEN
      RAISE EXCEPTION 'FINAL STATE id=% differs from target: mark=% name=% search=% exclude=%', pid, r.mark, r.name, cur_s, cur_e;
    END IF;

    after_snap := jsonb_build_object(
      'product', (SELECT to_jsonb(p) FROM public.products p WHERE p.id = pid),
      'search_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_search_keywords k WHERE k.product_id = pid), '[]'::jsonb),
      'exclude_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_exclude_keywords k WHERE k.product_id = pid), '[]'::jsonb));

    -- same shape as update_product_detail's audit row (record_id is a fresh uuid there too; old/new are TEXT)
    INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
    VALUES ('products', gen_random_uuid(), 'UPDATE', '__ACTOR__', before_snap::text, after_snap::text);
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> 1 THEN RAISE EXCEPTION 'audit_log insert id=% rows=% (expected 1)', pid, c; END IF;
    touched := touched + 1;
  END LOOP;
  IF touched <> __N__ THEN RAISE EXCEPTION 'touched % products (expected __N__)', touched; END IF;
  RAISE NOTICE 'DONE: % products changed, % audit_log rows', touched, touched;
END
$do$;"""


def specs_json(swap=False):
    return json.dumps(SPECS, ensure_ascii=False, indent=1)


def head(title, note):
    return (f"-- {title}\n-- {note}\n-- Target: DB jarvis_db, schema public. Products {IDS}. Generated by gen_sql.py; do not hand-edit.\n"
            "\\set ON_ERROR_STOP on\n")


def build_check(side):
    return CHECK_DO.replace("__SPECS__", specs_json()).replace("__SIDE__", side)


def build_change(frm, to, actor):
    return (CHANGE_DO.replace("__SPECS__", specs_json()).replace("__FROM__", frm).replace("__TO__", to)
            .replace("__ACTOR__", actor).replace("__N__", str(len(SPECS))))


def main():
    files = {}
    files["precheck.sql"] = (head("precheck.sql (READ-ONLY)", "RAISES if any of the 6 products differs from the 2026-10-04 production values (masters/current_values.csv).")
        + "BEGIN READ ONLY;\n" + SHOW + "\n" + build_check("old") + "\nROLLBACK;\n")
    body_apply = "BEGIN;\nSET LOCAL app.is_operator = 'true';\nSET LOCAL lock_timeout = '10s';\nSET LOCAL statement_timeout = '60s';\n"
    files["apply.sql"] = (head("apply.sql (WRITES, one transaction, ends with COMMIT)", "Mirrors update_product_detail (backend/app/services/tcg_product_detail_svc.py): SET LOCAL app.is_operator, UPDATE name/mark, keyword delete+reinsert (positions 1..n), audit_log row.")
        + body_apply + build_change("old", "new", ACTOR_APPLY) + "\n" + SHOW + "\nCOMMIT;\n")
    files["dryrun.sql"] = (head("dryrun.sql (same as apply.sql but ends with ROLLBACK)", "Nothing is kept. Shows the final state inside the transaction, then rolls back.")
        + body_apply + build_change("old", "new", ACTOR_APPLY) + "\n" + SHOW + "\nROLLBACK;\n")
    files["rollback.sql"] = (head("rollback.sql (WRITES; needs a NEW PO decision before running)", "Restores the 2026-10-04 production values (the state before apply.sql). Guards on the target values.")
        + body_apply + build_change("new", "old", ACTOR_ROLLBACK) + "\n" + SHOW + "\nCOMMIT;\n")
    files["postcheck.sql"] = (head("postcheck.sql (READ-ONLY)", "RAISES unless all 6 products equal the target; also lists the audit rows written by apply.sql.")
        + "BEGIN READ ONLY;\n" + SHOW + "\n" + build_check("new")
        + f"\nSELECT id, table_name, action, changed_by, changed_at, length(old_values) AS old_len, length(new_values) AS new_len\n  FROM public.audit_log WHERE table_name = 'products' AND changed_by = '{ACTOR_APPLY}' ORDER BY id DESC LIMIT 12;\nROLLBACK;\n")
    for name, text in files.items():
        (HERE / name).write_text(text, encoding="utf-8")
        print(name, len(text.splitlines()), "lines")


if __name__ == "__main__":
    main()
