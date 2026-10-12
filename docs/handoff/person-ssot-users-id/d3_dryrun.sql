-- D3: P2 で参照先を public.users(id) に移した列の値を、名簿の番号から users の番号へ付け替える（ADR-1008 段階 D3）
-- 前提: D1 実行済み（t4 staff 1 = users 3、t6 staff 1 = users 10、t1 staff 1 = users 1）。P2 本番反映済み。
-- 対応: t4 の値 1（staff 1）→ 3、t6 の値 1（staff 1）→ 10。t1 は staff 1 = users 1 で値が同じため付け替え不要。
-- 安全: t4・t6 で値 1 を書けるのは旧コードだけ（users 1 は tenant 1 の所属で t4・t6 にログインできない）。
--       P2 反映後の新しい書き込みは 3・10 など users の番号になるため、値 1 の行だけを付け替えれば取り違えない。
-- 1トランザクション・件数ガード付き。DRY-RUN は末尾 COMMIT を ROLLBACK に置き換えて流す。
BEGIN;
DO $$
DECLARE n integer;
BEGIN
  -- 事前確認: 付け替え対象外の列は全テナントで値なし（2026-10-13 読み取り: 0 件）
  SELECT (SELECT count(*) FROM tenant_001.bots) + (SELECT count(*) FROM tenant_003.bots) + (SELECT count(*) FROM tenant_004.bots)
       + (SELECT count(*) FROM tenant_005.bots) + (SELECT count(*) FROM tenant_006.bots) INTO n;
  IF n <> 0 THEN RAISE EXCEPTION 'pre bots expected 0 got %', n; END IF;
  SELECT (SELECT count(*) FROM tenant_001.order_commissions WHERE staff_id IS NOT NULL) + (SELECT count(*) FROM tenant_003.order_commissions WHERE staff_id IS NOT NULL)
       + (SELECT count(*) FROM tenant_004.order_commissions WHERE staff_id IS NOT NULL) + (SELECT count(*) FROM tenant_005.order_commissions WHERE staff_id IS NOT NULL)
       + (SELECT count(*) FROM tenant_006.order_commissions WHERE staff_id IS NOT NULL) INTO n;
  IF n <> 0 THEN RAISE EXCEPTION 'pre order_commissions expected 0 got %', n; END IF;
  SELECT (SELECT count(*) FROM tenant_001.calendar_owner_settings) + (SELECT count(*) FROM tenant_003.calendar_owner_settings) + (SELECT count(*) FROM tenant_004.calendar_owner_settings)
       + (SELECT count(*) FROM tenant_005.calendar_owner_settings) + (SELECT count(*) FROM tenant_006.calendar_owner_settings) INTO n;
  IF n <> 0 THEN RAISE EXCEPTION 'pre calendar_owner_settings expected 0 got %', n; END IF;
  SELECT (SELECT count(*) FROM tenant_003.meta_messages WHERE sent_by_staff_id IS NOT NULL OR seen_by_staff_id IS NOT NULL)
       + (SELECT count(*) FROM tenant_005.meta_messages WHERE sent_by_staff_id IS NOT NULL OR seen_by_staff_id IS NOT NULL)
       + (SELECT count(*) FROM tenant_003.tenant_meta_config WHERE connected_by_staff_id IS NOT NULL)
       + (SELECT count(*) FROM tenant_005.tenant_meta_config WHERE connected_by_staff_id IS NOT NULL) INTO n;
  IF n <> 0 THEN RAISE EXCEPTION 'pre t3/t5 meta expected 0 got %', n; END IF;
  -- t4・t6 の値は「旧（1）」か「新（3・4・5・6／10）」だけであること
  SELECT count(*) INTO n FROM tenant_004.meta_messages WHERE (seen_by_staff_id IS NOT NULL AND seen_by_staff_id NOT IN (1, 3, 4, 5, 6)) OR (sent_by_staff_id IS NOT NULL AND sent_by_staff_id NOT IN (1, 3, 4, 5, 6));
  IF n <> 0 THEN RAISE EXCEPTION 'pre t4 meta_messages unexpected values %', n; END IF;
  SELECT count(*) INTO n FROM tenant_004.tenant_meta_config WHERE connected_by_staff_id IS NOT NULL AND connected_by_staff_id NOT IN (1, 3, 4, 5, 6);
  IF n <> 0 THEN RAISE EXCEPTION 'pre t4 meta_config unexpected values %', n; END IF;
  SELECT count(*) INTO n FROM tenant_006.tenant_meta_config WHERE connected_by_staff_id IS NOT NULL AND connected_by_staff_id NOT IN (1, 10, 80, 81, 82);
  IF n <> 0 THEN RAISE EXCEPTION 'pre t6 meta_config unexpected values %', n; END IF;

  -- 付け替え（meta_messages の件数は 2026-10-13 読み取り時点が下限＝旧コードの書き込みで増えうる。
  --          tenant_meta_config の件数は上限＝P2 反映後の再接続で新しい番号に上書きされて減りうる。
  --          どちらも最後の「値 1 が残っていない」確認で取りこぼしを検出する）
  UPDATE tenant_004.meta_messages SET seen_by_staff_id = 3 WHERE seen_by_staff_id = 1;
  GET DIAGNOSTICS n = ROW_COUNT; IF n < 25 THEN RAISE EXCEPTION 't4 seen_by expected >= 25 got %', n; END IF;
  RAISE NOTICE 't4 meta_messages.seen_by 1->3: %', n;
  UPDATE tenant_004.meta_messages SET sent_by_staff_id = 3 WHERE sent_by_staff_id = 1;
  GET DIAGNOSTICS n = ROW_COUNT; RAISE NOTICE 't4 meta_messages.sent_by 1->3: %', n;
  UPDATE tenant_004.tenant_meta_config SET connected_by_staff_id = 3 WHERE connected_by_staff_id = 1;
  GET DIAGNOSTICS n = ROW_COUNT; IF n > 11 THEN RAISE EXCEPTION 't4 connected_by expected <= 11 got %', n; END IF;
  RAISE NOTICE 't4 tenant_meta_config.connected_by 1->3: %', n;
  UPDATE tenant_006.tenant_meta_config SET connected_by_staff_id = 10 WHERE connected_by_staff_id = 1;
  GET DIAGNOSTICS n = ROW_COUNT; IF n > 1 THEN RAISE EXCEPTION 't6 connected_by expected <= 1 got %', n; END IF;
  RAISE NOTICE 't6 tenant_meta_config.connected_by 1->10: %', n;

  -- 事後確認: t4・t6 に値 1 が残っていない
  SELECT (SELECT count(*) FROM tenant_004.meta_messages WHERE seen_by_staff_id = 1 OR sent_by_staff_id = 1)
       + (SELECT count(*) FROM tenant_004.tenant_meta_config WHERE connected_by_staff_id = 1)
       + (SELECT count(*) FROM tenant_006.tenant_meta_config WHERE connected_by_staff_id = 1) INTO n;
  IF n <> 0 THEN RAISE EXCEPTION 'post remaining value 1: %', n; END IF;
  RAISE NOTICE 'D3 ok';
END $$;
ROLLBACK;
