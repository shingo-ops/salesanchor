-- D3 の戻し（ADR-1008）。D3 実行後にだけ使う。新たな PO 合意なしに実行しない。
-- 対象は D3 実行直前に値 1 だった行だけ。run_d3 が実行前に読み取った id 一覧
-- （~/CC報告ファイル-keep/user-ssot/d3/targets.log）を、下の <...> に埋めて流す。
-- 値 3・10 の行をまとめて 1 に戻してはいけない（P2 反映後の正しい書き込みも 3・10 のため）。
BEGIN;
DO $$
DECLARE n integer;
BEGIN
  UPDATE tenant_004.meta_messages SET seen_by_staff_id = 1 WHERE seen_by_staff_id = 3 AND id IN (<t4 seen_by の id 一覧>);
  GET DIAGNOSTICS n = ROW_COUNT; RAISE NOTICE 't4 seen_by 3->1: %', n;
  UPDATE tenant_004.meta_messages SET sent_by_staff_id = 1 WHERE sent_by_staff_id = 3 AND id IN (<t4 sent_by の id 一覧。無ければこの文を消す>);
  GET DIAGNOSTICS n = ROW_COUNT; RAISE NOTICE 't4 sent_by 3->1: %', n;
  UPDATE tenant_004.tenant_meta_config SET connected_by_staff_id = 1 WHERE connected_by_staff_id = 3 AND id IN (<t4 tenant_meta_config の id 一覧>);
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 11 THEN RAISE EXCEPTION 't4 connected_by expected 11 got %', n; END IF;
  UPDATE tenant_006.tenant_meta_config SET connected_by_staff_id = 1 WHERE connected_by_staff_id = 10 AND id IN (<t6 tenant_meta_config の id>);
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 't6 connected_by expected 1 got %', n; END IF;
  RAISE NOTICE 'D3 rollback ok';
END $$;
COMMIT;
-- 注: 外部キーは P2 で public.users(id) を向いている。値 1（users 1）は存在するので制約には反しないが、
--     旧コード（staff の番号として読む）に戻すには P2 の revert も合わせて必要。
