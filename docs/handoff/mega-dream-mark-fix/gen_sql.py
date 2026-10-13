#!/usr/bin/env python3
"""Generate precheck/dryrun/apply/rollback/postcheck .sql for the MEGAドリームex mark fix (PM0198, id 440559, mark M3 -> M2a).
Same structure as the deckbuild change (docs/handoff/deckbuild-master-fix/gen_sql.py). Nothing here touches a database.
Usage: python3 gen_sql.py   (writes next to this file)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACTOR_APPLY = "claude-opus (PO承認 2026-10-05)"
ACTOR_ROLLBACK = "claude-opus (rollback; PO decision required)"
IDS = "440559"

KEYWORDS_SEARCH = ["MEGAドリームex", "MEGA Dream", "メガドリーム"]
KEYWORDS_EXCLUDE = ["AR", "PSA", "PSA10", "PSA9", "SAR", "SR", "パラレル", "マスターボールミラー"]
# production values read 2026-10-05 (item1/rows.csv); keywords are NOT changed by this fix
SPECS = [{
    "id": 440559, "code": "PM0198",
    "old": {"mark": "M3", "name": "MEGAドリームex", "search": KEYWORDS_SEARCH, "exclude": KEYWORDS_EXCLUDE},
    "new": {"mark": "M2a", "name": "MEGAドリームex", "search": KEYWORDS_SEARCH, "exclude": KEYWORDS_EXCLUDE},
}]

SHOW = f"""SELECT p.id, p.product_code, p.mark, p.name, p.is_active,
       (SELECT string_agg(k.position || ':' || k.keyword, ' | ' ORDER BY k.position, k.id)
          FROM public.product_search_keywords k WHERE k.product_id = p.id) AS search_keywords,
       (SELECT string_agg(k.position || ':' || k.keyword, ' | ' ORDER BY k.position, k.id)
          FROM public.product_exclude_keywords k WHERE k.product_id = p.id) AS exclude_keywords,
       p.updated_at
  FROM public.products p WHERE p.id IN ({IDS}) ORDER BY p.id;"""

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
    -- this fix changes the mark only: the keyword lists must be identical before and after
    IF to_s IS DISTINCT FROM from_s OR to_e IS DISTINCT FROM from_e OR spec->'__TO__'->>'name' IS DISTINCT FROM spec->'__FROM__'->>'name' THEN
      RAISE EXCEPTION 'SPEC id=%: this script must change the mark only', pid;
    END IF;

    before_snap := jsonb_build_object(
      'product', (SELECT to_jsonb(p) FROM public.products p WHERE p.id = pid),
      'search_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_search_keywords k WHERE k.product_id = pid), '[]'::jsonb),
      'exclude_keywords', COALESCE((SELECT jsonb_agg(to_jsonb(k) ORDER BY k.position, k.id) FROM public.product_exclude_keywords k WHERE k.product_id = pid), '[]'::jsonb));

    UPDATE public.products SET mark = spec->'__TO__'->>'mark'
     WHERE id = pid AND name = spec->'__FROM__'->>'name' AND mark = spec->'__FROM__'->>'mark';
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> 1 THEN RAISE EXCEPTION 'UPDATE products id=% affected % rows (expected 1)', pid, c; END IF;
    RAISE NOTICE 'id=% products UPDATE rows=%: mark % -> %', pid, c, spec->'__FROM__'->>'mark', spec->'__TO__'->>'mark';

    -- final state of this product must equal the target (keyword rows untouched)
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


def specs_json():
    return json.dumps(SPECS, ensure_ascii=False, indent=1)


def head(title, note):
    return (f"-- {title}\n-- {note}\n-- Target: DB jarvis_db, schema public. Product {IDS} (PM0198 MEGAドリームex). Generated by gen_sql.py; do not hand-edit.\n"
            "\\set ON_ERROR_STOP on\n")


def build_check(side):
    return CHECK_DO.replace("__SPECS__", specs_json()).replace("__SIDE__", side)


def build_change(frm, to, actor):
    return (CHANGE_DO.replace("__SPECS__", specs_json()).replace("__FROM__", frm).replace("__TO__", to)
            .replace("__ACTOR__", actor).replace("__N__", str(len(SPECS))))


def main():
    pre = "BEGIN;\nSET LOCAL app.is_operator = 'true';\nSET LOCAL lock_timeout = '10s';\nSET LOCAL statement_timeout = '60s';\n"
    files = {
        "precheck.sql": head("precheck.sql (READ-ONLY)", "RAISES unless product 440559 equals today's production values (mark M3).")
        + "BEGIN READ ONLY;\n" + SHOW + "\n" + build_check("old") + "\nROLLBACK;\n",
        "dryrun.sql": head("dryrun.sql (same as apply.sql but ends with ROLLBACK)", "Nothing is kept. Shows the final state inside the transaction, then rolls back.")
        + pre + build_change("old", "new", ACTOR_APPLY) + "\n" + SHOW + "\nROLLBACK;\n",
        "apply.sql": head("apply.sql (WRITES, one transaction, ends with COMMIT)", "UPDATE products SET mark = 'M2a' for id 440559 only; keywords unchanged; one audit_log row.")
        + pre + build_change("old", "new", ACTOR_APPLY) + "\n" + SHOW + "\nCOMMIT;\n",
        "rollback.sql": head("rollback.sql (WRITES; needs a NEW PO decision before running)", "Restores mark M3 for id 440559. Guards on the target values.")
        + pre + build_change("new", "old", ACTOR_ROLLBACK) + "\n" + SHOW + "\nCOMMIT;\n",
        "postcheck.sql": head("postcheck.sql (READ-ONLY)", "RAISES unless product 440559 has mark M2a and unchanged keywords; lists the audit row.")
        + "BEGIN READ ONLY;\n" + SHOW + "\n" + build_check("new")
        + f"\nSELECT id, table_name, action, changed_by, changed_at, length(old_values) AS old_len, length(new_values) AS new_len\n  FROM public.audit_log WHERE table_name = 'products' AND changed_by = '{ACTOR_APPLY}' ORDER BY id DESC LIMIT 5;\nROLLBACK;\n",
    }
    for name, text in files.items():
        (HERE / name).write_text(text, encoding="utf-8")
        print(name, len(text.splitlines()), "lines")


if __name__ == "__main__":
    main()
