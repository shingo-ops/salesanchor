-- 復活止めの試験。使い方: createdb で空のDBを作り、psql -v mode=old|guard -f sandbox/scenarios.sql  （old = 現行SQL、guard = 案）
-- 商品: 10=A 20=B  状態: 1=Single 2=Error 3=Box 4=Case 5=Sealed 6=Damaged
-- 再解析で item を作り直すこと (line_analysis_v102_svc.py:519) は、古い item を gone=true にして新しい id で入れ直すことで再現する (行は消さない)。
\set ON_ERROR_STOP on
\i sandbox/setup.sql
\i sandbox/merge_old.sql
\i sandbox/merge_guard.sql
SET rg.mode = :'mode';
CREATE FUNCTION run_merge(j uuid, ep int[] DEFAULT '{}', ec int[] DEFAULT '{}', pp int[] DEFAULT NULL, pc int[] DEFAULT NULL, g boolean DEFAULT true) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 IF current_setting('rg.mode') = 'old' THEN PERFORM merge_old(j, chan_of(j), ep, ec);
 ELSE PERFORM merge_guard(j, chan_of(j), ep, ec, pp, pc, g); END IF;
END $$;
-- 再解析のまね (line_analysis_v102_svc.py:1461 前の組を控え → 作り直し → 1476 付け直し)。
-- 控え pp/pc = 前から現行だった組 (空でも配列で渡す)。extra = 前の全組。古い item は gone=true、新しい行は既定 TRUE で入る。
CREATE FUNCTION reanalyze2(j uuid, np int[], nc int[], ntag text[]) RETURNS void LANGUAGE plpgsql AS $$
DECLARE pp int[]; pc int[]; ap int[]; ac int[]; i int;
BEGIN
 SELECT coalesce(array_agg(ar.product_id),'{}'), coalesce(array_agg(ar.condition_id),'{}') INTO pp, pc FROM t.analysis_results ar JOIN t.extraction_items ei ON ei.id=ar.extraction_item_id AND NOT ei.gone WHERE ei.extraction_job_id=j AND ar.is_current AND ar.pid_resolved;
 SELECT coalesce(array_agg(p),'{}'), coalesce(array_agg(c),'{}') INTO ap, ac FROM (SELECT DISTINCT ar.product_id p, ar.condition_id c FROM t.analysis_results ar JOIN t.extraction_items ei ON ei.id=ar.extraction_item_id AND NOT ei.gone WHERE ei.extraction_job_id=j AND ar.pid_resolved) x;
 UPDATE t.extraction_items SET gone = true WHERE extraction_job_id = j AND NOT gone;
 FOR i IN 1..coalesce(array_length(np,1),0) LOOP PERFORM add_row(j, np[i], nc[i], ntag[i]); END LOOP;
 PERFORM run_merge(j, ap, ac, pp, pc);
END $$;
CREATE VIEW live AS SELECT ar.tag, ar.is_current FROM t.analysis_results ar JOIN t.extraction_items ei ON ei.id=ar.extraction_item_id AND NOT ei.gone;

-- ===== 初回の解析 (S1,S2,S3,S5,S6,S7,S8,S9: old と guard で同じ結果になるはず) =====
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; BEGIN -- S1 新A=Single 旧A=Error
 o := add_post(ch,5); PERFORM add_row(o,10,2,'S1 old A/Error'); n := add_post(ch,1); PERFORM add_row(n,10,1,'S1 new A/Single'); PERFORM run_merge(n); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; BEGIN -- S2 新に A 無し
 o := add_post(ch,5); PERFORM add_row(o,10,1,'S2 old A'); PERFORM add_row(o,20,1,'S2 old B'); n := add_post(ch,1); PERFORM add_row(n,20,1,'S2 new B'); PERFORM run_merge(n); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; BEGIN -- S3 〆だけの投稿
 o := add_post(ch,5); PERFORM add_row(o,10,1,'S3 old A'); n := add_post(ch,1); PERFORM run_merge(n); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); n uuid; BEGIN -- S6 同じ投稿に同じ商品が複数行
 n := add_post(ch,1); PERFORM add_row(n,10,3,'S6 same-post A/Box #1'); PERFORM add_row(n,10,3,'S6 same-post A/Box #2'); PERFORM add_row(n,10,4,'S6 same-post A/Case'); PERFORM run_merge(n); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; BEGIN -- S8 旧 A/Box+A/Case、新 A/Box だけ
 o := add_post(ch,5); PERFORM add_row(o,10,3,'S8 old A/Box'); PERFORM add_row(o,10,4,'S8 old A/Case'); n := add_post(ch,1); PERFORM add_row(n,10,3,'S8 new A/Box'); PERFORM run_merge(n); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; r uuid; BEGIN -- S5 仮の行
 o := add_post(ch,5); PERFORM add_row(o,10,3,'S5 old A/Box'); PERFORM add_row(o,10,4,'S5 old A/Case'); n := add_post(ch,1); r := add_row(n,20,3,'S5 new shime B');
 INSERT INTO t.analysis_soldout_extra_targets(analysis_result_id, product_id, condition_id) VALUES (r,10,3); PERFORM run_merge(n); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); a uuid; b uuid; BEGIN -- S7 同順位
 a := add_post(ch,2); b := add_post(ch,2); UPDATE t.source_messages SET received_at='2026-10-10 01:00+00' WHERE supplier_channel_id=ch;
 PERFORM add_row(a,10,3,'S7 tie job a'); PERFORM add_row(b,10,4,'S7 tie job b'); PERFORM run_merge(a); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; BEGIN -- S9 古い投稿を後から初回解析 (順番が前後して届いた場合)。控え無し → 今と同じ
 n := add_post(ch,1); PERFORM add_row(n,10,1,'S9 new A/Single'); PERFORM run_merge(n);
 o := add_post(ch,5); PERFORM add_row(o,10,2,'S9 late-first-analysis old A/Error'); PERFORM run_merge(o); END $$;

-- ===== 再解析 =====
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; BEGIN -- R1 (S4n) 最新の投稿の再解析で A/Error → A/Single。旧 A/Error は復活しない
 o := add_post(ch,5); PERFORM add_row(o,10,2,'R1 old A/Error'); n := add_post(ch,1); PERFORM add_row(n,10,2,'R1 new A/Error(再解析前)'); PERFORM run_merge(n);
 PERFORM reanalyze2(n, '{10}', '{1}', '{"R1 new A/Single(再解析後)"}'); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; BEGIN -- R2 最新の投稿の再解析で A → B。旧 A は戻る
 o := add_post(ch,5); PERFORM add_row(o,10,1,'R2 old A/Single'); n := add_post(ch,1); PERFORM add_row(n,10,1,'R2 new A/Single(再解析前)'); PERFORM run_merge(n);
 PERFORM reanalyze2(n, '{20}', '{1}', '{"R2 new B/Single(再解析後)"}'); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); x uuid; y uuid; BEGIN -- R3a 古い投稿 X の再解析 (A,Error)→(A,Single)。Y(より新しい)に A がある。(A,Damaged) は変えない
 x := add_post(ch,5); PERFORM add_row(x,10,2,'R3a X A/Error(再解析前)'); PERFORM add_row(x,10,6,'R3a X A/Damaged(再解析前)'); y := add_post(ch,1); PERFORM add_row(y,10,3,'R3a Y A/Box');
 PERFORM run_merge(x); PERFORM run_merge(y);
 PERFORM reanalyze2(x, '{10,10}', '{1,6}', '{"R3a X A/Single(再解析後)","R3a X A/Damaged(再解析後)"}'); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); x uuid; y uuid; BEGIN -- R3b 同じ。ただし Y に A が無い (B だけ)
 x := add_post(ch,5); PERFORM add_row(x,10,2,'R3b X A/Error(再解析前)'); PERFORM add_row(x,10,6,'R3b X A/Damaged(再解析前)'); y := add_post(ch,1); PERFORM add_row(y,20,3,'R3b Y B/Box');
 PERFORM run_merge(x); PERFORM run_merge(y);
 PERFORM reanalyze2(x, '{10,10}', '{1,6}', '{"R3b X A/Single(再解析後)","R3b X A/Damaged(再解析後)"}'); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); z uuid; x uuid; BEGIN -- R3c 最古の Z の行が X の (A,Error) に隠れている。X を (A,Error)→(A,Single) に再解析しても Z は復活しない
 z := add_post(ch,9); PERFORM add_row(z,10,2,'R3c Z A/Error'); x := add_post(ch,5); PERFORM add_row(x,10,2,'R3c X A/Error(再解析前)');
 PERFORM run_merge(z); PERFORM run_merge(x);
 PERFORM reanalyze2(x, '{10}', '{1}', '{"R3c X A/Single(再解析後)"}'); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; BEGIN -- R5 (9/25の設計) 旧 A/Sealed・A/Damaged、新 A/Sealed。再解析で A/Sealed → A/Single
 o := add_post(ch,5); PERFORM add_row(o,10,5,'R5 old A/Sealed'); PERFORM add_row(o,10,6,'R5 old A/Damaged'); n := add_post(ch,1); PERFORM add_row(n,10,5,'R5 new A/Sealed(再解析前)');
 PERFORM run_merge(o); PERFORM run_merge(n);
 PERFORM reanalyze2(n, '{10}', '{1}', '{"R5 new A/Single(再解析後)"}'); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); o uuid; n uuid; BEGIN -- R6 (9/25の設計) 新の再解析で内容が変わらない。旧 A/Damaged は TRUE のまま
 o := add_post(ch,5); PERFORM add_row(o,10,5,'R6 old A/Sealed'); PERFORM add_row(o,10,6,'R6 old A/Damaged'); n := add_post(ch,1); PERFORM add_row(n,10,5,'R6 new A/Sealed(再解析前)');
 PERFORM run_merge(o); PERFORM run_merge(n);
 PERFORM reanalyze2(n, '{10}', '{5}', '{"R6 new A/Sealed(再解析後・同じ)"}'); END $$;

-- ===== 件の削除 (v102_transcription_svc.py:370-382 の removed_pairs。控え無し) =====
DO $$ DECLARE ch uuid := gen_random_uuid(); x uuid; y uuid; r uuid; BEGIN -- D1 新しい投稿 Y の A/Single の件を消す。Y には A/Box が残る。旧 X の A/Single は?
 x := add_post(ch,5); PERFORM add_row(x,10,1,'D1 old A/Single'); y := add_post(ch,1); r := add_row(y,10,1,'D1 new A/Single(削除する)'); PERFORM add_row(y,10,3,'D1 new A/Box(残る)');
 PERFORM run_merge(x); PERFORM run_merge(y);
 UPDATE t.extraction_items SET gone = true WHERE id = (SELECT extraction_item_id FROM t.analysis_results WHERE id = r);
 PERFORM run_merge(y, '{10}', '{1}'); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); x uuid; y uuid; r uuid; BEGIN -- D1b 同じ。ただし削除の呼び出しだけ復活止めを切る (g=false)
 x := add_post(ch,5); PERFORM add_row(x,10,1,'D1b old A/Single'); y := add_post(ch,1); r := add_row(y,10,1,'D1b new A/Single(削除する)'); PERFORM add_row(y,10,3,'D1b new A/Box(残る)');
 PERFORM run_merge(x); PERFORM run_merge(y);
 UPDATE t.extraction_items SET gone = true WHERE id = (SELECT extraction_item_id FROM t.analysis_results WHERE id = r);
 PERFORM run_merge(y, '{10}', '{1}', NULL, NULL, false); END $$;
DO $$ DECLARE ch uuid := gen_random_uuid(); x uuid; y uuid; r uuid; BEGIN -- D2 Y の A の件を全部消す (Y に A が無くなる)。旧 X の A/Single は戻る (規則 (i))
 x := add_post(ch,5); PERFORM add_row(x,10,1,'D2 old A/Single'); y := add_post(ch,1); r := add_row(y,10,1,'D2 new A/Single(削除する)');
 PERFORM run_merge(x); PERFORM run_merge(y);
 UPDATE t.extraction_items SET gone = true WHERE id = (SELECT extraction_item_id FROM t.analysis_results WHERE id = r);
 PERFORM run_merge(y, '{10}', '{1}'); END $$;

\echo === RESULT mode=:mode
SELECT tag, is_current FROM live ORDER BY tag;
-- 冪等: 控え無しで全投稿をもう1度流しても変化 0
CREATE TEMP TABLE snap AS SELECT tag, is_current FROM live;
SELECT run_merge(ej.id) FROM t.extraction_jobs ej JOIN t.source_messages sm ON sm.id=ej.source_message_id ORDER BY sm.received_at;
\echo === IDEMPOTENT rows_changed_by_second_run
SELECT count(*) AS rows_changed_by_second_run FROM live l JOIN snap s ON s.tag=l.tag WHERE l.is_current IS DISTINCT FROM s.is_current;
