-- LMI-SP0136-REQUEUE: SP0136 の有効メッセージ 2336edf3 の抽出ジョブを再実行可能な状態に戻す
--
-- 背景:
--   tenant_004 の supplier_channel SP0136 に有効な source_message が2件並存している。
--   掃除規則（received_at 最新の1件を残す・NULL は最古扱い）では 2336edf3 が残るが、
--   その抽出ジョブ a6c1d827 が 2026-09-04 の 429 で error のまま止まっている。
--   残す1件が未抽出のため掃除が実行できない。
--   設計: docs/handoff/tcg-line-message-integrity/design.md
--
-- 本 migration の範囲:
--   ジョブ a6c1d827 の1行のみ。id・status・created_at の3条件で特定する。
--   他の55件の error ジョブには一切触れない。
--   件数確認は本ファイルが対象とする1件の範囲のみを数える（テーブル全体は数えない）。
--
-- 冪等: 1回目で status が pending になり、2回目以降は status='error' の条件に合致せず更新は起きない。
--       抽出成功後は status が done になるため、以降のデプロイでも再度ヒットしない。
--       件数は RAISE NOTICE で記録するのみとし、RAISE EXCEPTION による固定検査は行わない
--       （固定検査を入れると2回目の実行で必ず失敗し、CI の冪等性テストを通らないため）。
--
-- 対象ADR: ADR-154
-- 対象テナント: tenant_004（本番）。CI の空DBではスキーマ不在のためスキップする。

DO $body$
DECLARE
    _schema TEXT := 'tenant_004';
    _job_id UUID := 'a6c1d827-7fd5-4cfc-a2e0-b0fa63388b43';
    _status TEXT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE 'LMI-SP0136-REQUEUE: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format($q$
        UPDATE %I.extraction_jobs
        SET status = 'pending',
            error_message = NULL
        WHERE id = $1
          AND status = 'error'
          AND created_at = '2026-09-04 07:54:11.187158+00'
    $q$, _schema) USING _job_id;

    EXECUTE format(
        'SELECT status FROM %I.extraction_jobs WHERE id = $1',
        _schema
    ) INTO _status USING _job_id;

    RAISE NOTICE 'LMI-SP0136-REQUEUE: job % の status = %', _job_id, _status;
END $body$;
