-- LMI-SP0136-CLEANUP: SP0136 の並存する有効メッセージのうち古い1件を無効化する
--
-- 背景:
--   tenant_004 の supplier_channel SP0136 に有効な source_message が2件並存している。
--   掃除規則（PO 合意 2026-09-06）: channel ごとに received_at 最新の1件を残す。
--   NULL は最古扱い。残す1件の抽出が成功していない channel は対象外。
--   設計: docs/handoff/tcg-line-message-integrity/design.md
--
-- 対象の2件（2026-09-08 実測）:
--   c5ad04aa  received_at NULL（最古扱い）  created_at 2026-08-30  items 31 / results 31  -> 無効化する
--   2336edf3  received_at 2026-09-03        created_at 2026-09-04  items 28 / results 28  -> 残す
--   2336edf3 の抽出は 2026-09-08 11:57 に成功済み（status=done）。対象外条件に該当しない。
--
-- superseded_by を同時に設定する理由:
--   取込コード backend/app/services/tcg_line_import_svc.py:407 は
--   SET superseded_by = :new_id, is_active = FALSE を必ず同時に行う。
--   実測でも is_active=FALSE の 771 行すべてが superseded_by を持ち、例外は 0 件である。
--   本 migration は取込ではなく人手の是正だが、同じ形に揃えて不変条件を保つ。
--
-- 本 migration の範囲:
--   source_messages の c5ad04aa 1行のみ。id と is_active の2条件で特定する。
--   他の channel には一切触れない。行は削除せず is_active を FALSE にするのみ。
--   ぶら下がる extraction_items 31件と analysis_results 31件は残る（監査のため）。
--
-- 冪等: 1回目で is_active が FALSE になり、2回目以降は is_active=TRUE の条件に合致せず更新は起きない。
--       状態は RAISE NOTICE で記録するのみとし、RAISE EXCEPTION による固定検査は行わない
--       （固定検査を入れると2回目の実行で必ず失敗し、CI の冪等性テストを通らないため）。
--
-- 対象ADR: ADR-154
-- 対象テナント: tenant_004（本番）。CI の空DBではスキーマ不在のためスキップする。

DO $body$
DECLARE
    _schema TEXT := 'tenant_004';
    _old_id UUID := 'c5ad04aa-213f-41e5-bfbe-35f5b8925b2a';
    _new_id UUID := '2336edf3-e5cf-46f5-b114-6ae827deaa44';
    _active BOOLEAN;
    _sb     UUID;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE 'LMI-SP0136-CLEANUP: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format($q$
        UPDATE %I.source_messages
        SET superseded_by = $2,
            is_active = FALSE
        WHERE id = $1
          AND is_active = TRUE
    $q$, _schema) USING _old_id, _new_id;

    EXECUTE format(
        'SELECT is_active, superseded_by FROM %I.source_messages WHERE id = $1',
        _schema
    ) INTO _active, _sb USING _old_id;

    RAISE NOTICE 'LMI-SP0136-CLEANUP: old % is_active=% superseded_by=%', _old_id, _active, _sb;
END $body$;
