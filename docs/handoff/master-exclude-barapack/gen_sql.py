#!/usr/bin/env python3
"""master-exclude-barapack: 商品 440406 の除外語「バラパック」を1行外す。precheck/dryrun/apply/postcheck/rollback の .sql を1つの表から作る。DB には触れない。
方式は docs/handoff/master-keyword-fix/gen_sql.py と同じ（dryrun と apply は本体が同じで最後だけ ROLLBACK / COMMIT）。
Usage: python3 -B gen_sql.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACTOR_APPLY = "claude-sonnet (PO承認 2026-10-21 master-exclude-barapack)"
ACTOR_ROLLBACK = "claude-sonnet (PO承認 2026-10-21 master-exclude-barapack rollback)"
PID = 440406
CODE = "PM0263"
WORD = "バラパック"
WORD_ID = 2000          # 2026-10-21 reader 鍵で確認した、この行の id（rollback で同じ id・同じ updated_at に戻す）
WORD_UPDATED_AT = "2026-10-17 06:50:02.770819+00"
# 440406 の除外語 52 語（position 1..52 の順）。2026-10-21 reader 鍵で確認
OLD = ["FUTURISTIC", "プレミアム", "種セット", "ニャオハ", "サルノリ", "モクロー", "ハリマロン", "ツタージャ", "ナエトル", "キモリ", "チコリータ", "カードセット", "AR", "PSA", "PSA10", "PSA9", "SAR", "SR", "パラレル", "マスターボールミラー", "エーフィ", "ブラッキー", "デッキセット", "フューチャリスティック", "フシギダネ", "ヒトカゲ", "ゼニガメ", "ヒバニー", "メッソン", "ホゲータ", "クワッス", "アチャモ", "ミズゴロウ", "ニャビー", "アシマリ", "フォッコ", "ケロマツ", "ポカブ", "ミジュマル", "ヒコザル", "ポッチャマ", "ヒノアラシ", "ワニノコ", "ピカチュウ", "コンプ", "バラパック", "シングルカード", "9種", "種まとめ", "プロモパック", "カード9種", "遊戯王"]
POS = OLD.index(WORD) + 1   # 46
assert OLD.count(WORD) == 1 and len(OLD) == 52 and POS == 46
NEW = [w for w in OLD if w != WORD]
SPEC = {"id": PID, "code": CODE, "word": WORD, "word_id": WORD_ID, "word_pos": POS,
        "word_updated_at": WORD_UPDATED_AT, "old_exclude": OLD, "new_exclude": NEW}


def show():
    return f"""SELECT p.id, p.product_code, p.mark, p.name, p.is_active, p.updated_at,
       (SELECT count(*) FROM public.product_exclude_keywords k WHERE k.product_id = p.id) AS exclude_count,
       (SELECT string_agg(k.position || ':' || k.keyword, ' | ' ORDER BY k.position, k.id)
          FROM public.product_exclude_keywords k WHERE k.product_id = p.id) AS exclude_keywords
  FROM public.products p WHERE p.id = {PID};"""


# 値の照合。SIDE = before（外す前）/ after（外した後）。違えば RAISE EXCEPTION で止まる
CHECK = """DO $do$
DECLARE
  spec jsonb := $j$__SPEC__$j$::jsonb;
  pid int := (spec->>'id')::int;
  r record; cur_k text[]; cur_p int[]; want_k text[]; n int;
BEGIN
  SELECT * INTO r FROM public.products WHERE id = pid;
  IF NOT FOUND THEN RAISE EXCEPTION 'product % not found', pid; END IF;
  cur_k := ARRAY(SELECT keyword FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id);
  cur_p := ARRAY(SELECT position FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id);
  IF '__SIDE__' = 'before' THEN want_k := ARRAY(SELECT jsonb_array_elements_text(spec->'old_exclude'));
  ELSE want_k := ARRAY(SELECT jsonb_array_elements_text(spec->'new_exclude')); END IF;
  IF r.product_code IS DISTINCT FROM spec->>'code' OR r.is_active IS NOT TRUE
     OR cur_k IS DISTINCT FROM want_k
     OR cur_p IS DISTINCT FROM ARRAY(SELECT generate_series(1, array_length(want_k, 1))) THEN
    RAISE EXCEPTION 'MISMATCH (__SIDE__) id=%: code=% active=% count=% exclude=% positions=%', pid, r.product_code, r.is_active, array_length(cur_k, 1), cur_k, cur_p;
  END IF;
  SELECT count(*) INTO n FROM public.product_exclude_keywords WHERE product_id = pid AND keyword = spec->>'word';
  IF n <> (CASE '__SIDE__' WHEN 'before' THEN 1 ELSE 0 END) THEN
    RAISE EXCEPTION 'MISMATCH (__SIDE__) id=% word rows=%', pid, n;
  END IF;
  IF '__SIDE__' = 'before' THEN
    SELECT count(*) INTO n FROM public.product_exclude_keywords
     WHERE product_id = pid AND keyword = spec->>'word' AND id = (spec->>'word_id')::int AND position = (spec->>'word_pos')::int;
    IF n <> 1 THEN RAISE EXCEPTION 'MISMATCH (before) id=% word id/position differ', pid; END IF;
  END IF;
  RAISE NOTICE 'OK (__SIDE__) id=% code=% exclude_count=%', pid, r.product_code, array_length(cur_k, 1);
END
$do$;"""

# 本体。「バラパック」の行を keyword と product_id で特定して1行だけ消し、後ろの position を1つ詰める
CHANGE = """DO $do$
DECLARE
  spec jsonb := $j$__SPEC__$j$::jsonb;
  pid int := (spec->>'id')::int;
  r record; c int; cur_k text[]; old_k text[]; new_k text[]; before_snap jsonb; after_snap jsonb;
BEGIN
  SELECT * INTO r FROM public.products WHERE id = pid FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'product % not found', pid; END IF;
  old_k := ARRAY(SELECT jsonb_array_elements_text(spec->'old_exclude'));
  new_k := ARRAY(SELECT jsonb_array_elements_text(spec->'new_exclude'));
  cur_k := ARRAY(SELECT keyword FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id);
  IF r.product_code IS DISTINCT FROM spec->>'code' OR r.is_active IS NOT TRUE OR cur_k IS DISTINCT FROM old_k THEN
    RAISE EXCEPTION 'GUARD id=%: unexpected current state code=% exclude=%', pid, r.product_code, cur_k;
  END IF;
  before_snap := jsonb_build_object('product_id', pid, 'exclude_keywords', to_jsonb(cur_k));

  -- 1行だけ消す（keyword と product_id で特定。件数が 1 でなければ止まる）
  DELETE FROM public.product_exclude_keywords WHERE product_id = pid AND keyword = spec->>'word';
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> 1 THEN RAISE EXCEPTION 'removed rows=% (expected 1)', c; END IF;
  -- アプリの保存は position を 1..n の連番で書くため、後ろを1つ詰める（件数 = 52 - 46 = 6）
  UPDATE public.product_exclude_keywords SET position = position - 1
   WHERE product_id = pid AND position > (spec->>'word_pos')::int;
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> array_length(old_k, 1) - (spec->>'word_pos')::int THEN RAISE EXCEPTION 'shifted rows=% (expected %)', c, array_length(old_k, 1) - (spec->>'word_pos')::int; END IF;
  -- update_product_detail の UPDATE と同じ効果（更新時刻を進める）
  UPDATE public.products SET updated_at = now() WHERE id = pid;
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> 1 THEN RAISE EXCEPTION 'UPDATE products id=% rows=% (expected 1)', pid, c; END IF;

  cur_k := ARRAY(SELECT keyword FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id);
  IF cur_k IS DISTINCT FROM new_k
     OR ARRAY(SELECT position FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id)
        IS DISTINCT FROM ARRAY(SELECT generate_series(1, array_length(new_k, 1))) THEN
    RAISE EXCEPTION 'FINAL STATE id=% differs from target: exclude=%', pid, cur_k;
  END IF;
  after_snap := jsonb_build_object('product_id', pid, 'exclude_keywords', to_jsonb(cur_k));
  INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
  VALUES ('products', gen_random_uuid(), 'UPDATE', '__ACTOR__', before_snap::text, after_snap::text);
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> 1 THEN RAISE EXCEPTION 'audit_log insert rows=% (expected 1)', c; END IF;
  RAISE NOTICE 'DONE: exclude word removed (1 row), 6 rows shifted, 1 audit_log row, id=% now %', pid, array_length(cur_k, 1);
END
$do$;"""

# 戻し。外した行を元の id・position・updated_at で入れ直し、ずらした position を戻す。消す文は含まない
ROLLBACK = """DO $do$
DECLARE
  spec jsonb := $j$__SPEC__$j$::jsonb;
  pid int := (spec->>'id')::int;
  r record; c int; cur_k text[]; old_k text[]; new_k text[]; before_snap jsonb; after_snap jsonb;
BEGIN
  SELECT * INTO r FROM public.products WHERE id = pid FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'product % not found', pid; END IF;
  old_k := ARRAY(SELECT jsonb_array_elements_text(spec->'old_exclude'));
  new_k := ARRAY(SELECT jsonb_array_elements_text(spec->'new_exclude'));
  cur_k := ARRAY(SELECT keyword FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id);
  -- 今が「外した後」の状態であること。違えば何もせず止まる（外す前のままなら戻す必要なし）
  IF r.product_code IS DISTINCT FROM spec->>'code' OR r.is_active IS NOT TRUE OR cur_k IS DISTINCT FROM new_k
     OR ARRAY(SELECT position FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id)
        IS DISTINCT FROM ARRAY(SELECT generate_series(1, array_length(new_k, 1)))
     OR EXISTS (SELECT 1 FROM public.product_exclude_keywords WHERE id = (spec->>'word_id')::int) THEN
    RAISE EXCEPTION 'GUARD id=%: not in the after-state (or word id taken) exclude=%', pid, cur_k;
  END IF;
  before_snap := jsonb_build_object('product_id', pid, 'exclude_keywords', to_jsonb(cur_k));

  UPDATE public.product_exclude_keywords SET position = position + 1
   WHERE product_id = pid AND position >= (spec->>'word_pos')::int;
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> array_length(new_k, 1) - (spec->>'word_pos')::int + 1 THEN RAISE EXCEPTION 'shifted rows=% (expected %)', c, array_length(new_k, 1) - (spec->>'word_pos')::int + 1; END IF;
  INSERT INTO public.product_exclude_keywords (id, product_id, keyword, position, updated_at) OVERRIDING SYSTEM VALUE
  VALUES ((spec->>'word_id')::int, pid, spec->>'word', (spec->>'word_pos')::int, (spec->>'word_updated_at')::timestamptz);
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> 1 THEN RAISE EXCEPTION 'insert rows=% (expected 1)', c; END IF;
  UPDATE public.products SET updated_at = now() WHERE id = pid;
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> 1 THEN RAISE EXCEPTION 'UPDATE products id=% rows=% (expected 1)', pid, c; END IF;

  cur_k := ARRAY(SELECT keyword FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id);
  IF cur_k IS DISTINCT FROM old_k
     OR ARRAY(SELECT position FROM public.product_exclude_keywords WHERE product_id = pid ORDER BY position, id)
        IS DISTINCT FROM ARRAY(SELECT generate_series(1, array_length(old_k, 1))) THEN
    RAISE EXCEPTION 'FINAL STATE id=% differs from the original: exclude=%', pid, cur_k;
  END IF;
  after_snap := jsonb_build_object('product_id', pid, 'exclude_keywords', to_jsonb(cur_k));
  INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
  VALUES ('products', gen_random_uuid(), 'UPDATE', '__ACTOR__', before_snap::text, after_snap::text);
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c <> 1 THEN RAISE EXCEPTION 'audit_log insert rows=% (expected 1)', c; END IF;
  RAISE NOTICE 'ROLLBACK DONE: exclude word restored (1 row), 6 rows shifted back, 1 audit_log row, id=% now %', pid, array_length(cur_k, 1);
END
$do$;"""

AUDIT_CHECK = """DO $do$
DECLARE c int;
BEGIN
  SELECT count(*) INTO c FROM public.audit_log WHERE changed_by = '__ACTOR__';
  IF c <> 1 THEN RAISE EXCEPTION 'audit_log rows by actor=% (expected 1)', c; END IF;
  RAISE NOTICE 'OK (after) audit_log rows=%', c;
END
$do$;"""


def sub(t, **kw):
    t = t.replace("__SPEC__", json.dumps(SPEC, ensure_ascii=False, indent=1))
    for k, v in kw.items():
        t = t.replace(f"__{k}__", v)
    return t


def head(title, note):
    return (f"-- {title}\n-- {note}\n-- Target: DB jarvis_db, schema public. Product {PID} ({CODE}) 除外語「{WORD}」. Generated by gen_sql.py; do not hand-edit.\n"
            "\\set ON_ERROR_STOP on\n")


def main():
    pre = "BEGIN;\nSET LOCAL app.is_operator = 'true';\nSET LOCAL lock_timeout = '10s';\nSET LOCAL statement_timeout = '60s';\n"
    # 全部入り: 同じトランザクション内で precheck → 変更 → postcheck → (COMMIT | ROLLBACK)。どれか1つでも失敗したら全部戻る
    body = pre + sub(CHECK, SIDE="before") + "\n" + sub(CHANGE, ACTOR=ACTOR_APPLY) + "\n" + sub(CHECK, SIDE="after") + "\n" + show() + "\n"
    rb = pre + sub(ROLLBACK, ACTOR=ACTOR_ROLLBACK) + "\n" + sub(CHECK, SIDE="before") + "\n" + show() + "\n"
    files = {
        "precheck.sql": head("precheck.sql (READ-ONLY)", "今の本番の値が想定どおりか照合。違えば止まる。") + "BEGIN READ ONLY;\n" + show() + "\n" + sub(CHECK, SIDE="before") + "\nROLLBACK;\n",
        "apply.sql": head("apply.sql (WRITES, one transaction, ends with COMMIT)", "precheck → 変更 → postcheck を同じトランザクションで。除外語1行を外し、後ろの position を詰める。audit_log に1行。") + body + "COMMIT;\n",
        "dryrun.sql": head("dryrun.sql (same as apply.sql but ends with ROLLBACK)", "precheck → 変更 → postcheck を流して、最後に ROLLBACK。何も残さない。") + body + "ROLLBACK;\n",
        "postcheck.sql": head("postcheck.sql (READ-ONLY)", "適用後の値が目標どおりか照合。") + "BEGIN READ ONLY;\n" + show() + "\n" + sub(CHECK, SIDE="after") + "\n" + sub(AUDIT_CHECK, ACTOR=ACTOR_APPLY) + "\nROLLBACK;\n",
        # rollback は「外した後」の状態でだけ動く。本体の末尾で「外す前」の照合を通して元に戻ったことを確かめる
        "rollback.sql": head("rollback.sql (WRITES, one transaction, ends with COMMIT)", "「外した後」の状態のときだけ、外した行を元の id・position・updated_at で入れ直し、ずらした position を戻す。audit_log に1行。") + rb + "COMMIT;\n",
        "rollback_dryrun.sql": head("rollback_dryrun.sql (same as rollback.sql but ends with ROLLBACK)", "戻しの試し流し。何も残さない。") + rb + "ROLLBACK;\n",
    }
    for name, text in files.items():
        (HERE / name).write_text(text, encoding="utf-8")
        print(name, len(text.splitlines()), "lines")


if __name__ == "__main__":
    main()
